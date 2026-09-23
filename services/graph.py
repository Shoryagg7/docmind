import operator
import re
from dataclasses import asdict
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import PrivacyAction
from core.errors import PrivacyBlockedError
from core.models import Chunk
from core.usage import logger as usage_logger
from core.usage import start_request
from services.grader import grade_relevance
from services import pii
from services.llm_client import generate
from services.pii import PLACEHOLDER_INSTRUCTION
from services.privacy_policy import BLOCK_MESSAGE, begin_request
from services.semantic_cache import get_cached_answer, set_cached_answer
from services.vector_store import search

MAX_RETRIES = 2

CITATION_PATTERN = re.compile(r"\[(\d+)\]")

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions using ONLY the "
    "provided context below. If the context does not contain the answer, "
    "say you don't know — do not use outside knowledge. For every claim "
    "in your answer, cite the source chunk number it came from using "
    "plain ASCII square brackets ONLY, exactly like [1] or [2] — never "
    "use any other bracket style (no full-width, no parentheses, no "
    "superscript). " + PLACEHOLDER_INSTRUCTION
)

REWRITE_SYSTEM_PROMPT = (
    "You rewrite search queries that failed to retrieve relevant results. "
    "Given the original question, produce one rephrased version more likely to "
    "match relevant document text. Reply with only the rewritten question, nothing else. "
    + PLACEHOLDER_INSTRUCTION
)


class RAGState(TypedDict):
    query: str
    k: int
    source: str | None
    chunks: list[Chunk]
    relevant_chunks: list[Chunk]
    answer: str
    sources: list[dict]
    retry_count: Annotated[int, operator.add]
    # When set, generate_node stops before calling the LLM and leaves the graded
    # chunks in state. The SSE route then streams generation itself, so streaming
    # reuses the real retrieve/grade/rewrite pipeline instead of duplicating it.
    defer_generation: bool


def build_graph(session: AsyncSession):
    async def retrieve_node(state: RAGState) -> dict:
        chunks = await search(session, state["query"], k=state["k"], source=state["source"])
        return {"chunks": chunks}

    async def grade_node(state: RAGState) -> dict:
        relevant = [c for c in state["chunks"] if grade_relevance(state["query"], c.content)]
        return {"relevant_chunks": relevant}

    async def rewrite_node(state: RAGState) -> dict:
        rewritten = generate(state["query"], system=REWRITE_SYSTEM_PROMPT, label="rewrite")
        return {"query": rewritten.strip(), "retry_count": 1}

    def should_retry(state: RAGState) -> str:
        if not state["relevant_chunks"] and state["retry_count"] < MAX_RETRIES:
            return "rewrite"
        return "generate"

    async def generate_node(state: RAGState) -> dict:
        chunks = state["relevant_chunks"]
        if not chunks:
            return {"answer": "I don't know — no relevant documents found.", "sources": []}

        if state.get("defer_generation"):
            return {}

        context = "\n\n".join(f"[{i + 1}] {c.content}" for i, c in enumerate(chunks))
        prompt = f"Context:\n{context}\n\nQuestion: {state['query']}"
        answer = generate(prompt, system=SYSTEM_PROMPT, label="generate")

        cited_ids = {int(n) for n in CITATION_PATTERN.findall(answer)}
        all_sources = [
            {"id": i + 1, "source": c.source, "content": c.content}
            for i, c in enumerate(chunks)
        ] 
        sources = [s for s in all_sources if s["id"] in cited_ids] or all_sources

        return {"answer": answer, "sources": sources}

    graph = StateGraph(RAGState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("grade", grade_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("generate", generate_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_conditional_edges(
        "grade", should_retry, {"rewrite": "rewrite", "generate": "generate"}
    )
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("generate", END)

    return graph.compile()


async def answer_question_graph(
    session: AsyncSession, query: str, k: int = 3, source: str | None = None
) -> dict:
    graph = build_graph(session)
    result = await graph.ainvoke(
        {
            "query": query,
            "k": k,
            "source": source,
            "chunks": [],
            "relevant_chunks": [],
            "answer": "",
            "sources": [],
            "retry_count": 0,
            "defer_generation": False,
        }
    )
    return {"answer": result["answer"], "sources": result["sources"]}


def initial_state(query: str, k: int, source: str | None, defer_generation: bool) -> dict:
    return {
        "query": query,
        "k": k,
        "source": source,
        "chunks": [],
        "relevant_chunks": [],
        "answer": "",
        "sources": [],
        "retry_count": 0,
        "defer_generation": defer_generation,
    }


def build_context(chunks: list[Chunk]) -> tuple[str, list[dict]]:
    context = "\n\n".join(f"[{i + 1}] {c.content}" for i, c in enumerate(chunks))
    all_sources = [
        {"id": i + 1, "source": c.source, "content": c.content}
        for i, c in enumerate(chunks)
    ]
    return context, all_sources


def filter_cited(answer: str, all_sources: list[dict]) -> list[dict]:
    cited_ids = {int(n) for n in CITATION_PATTERN.findall(answer)}
    return [s for s in all_sources if s["id"] in cited_ids] or all_sources


async def answer_query(
    session: AsyncSession,
    query: str,
    k: int = 3,
    source: str | None = None,
    allow_sensitive: bool = False,
    use_cache: bool = True,
) -> dict:
    """One request: privacy decision -> semantic cache -> graph. Used by /query and eval."""
    totals = start_request()
    decision = begin_request(query, allow_sensitive)
    egress = pii.current().record

    if decision.stops_request:
        return _response(decision.message(), [], totals, egress)

    # Consent answers never touch the cache. Otherwise a later paraphrase asked
    # WITHOUT consent could be served an answer that depended on it.
    use_cache = use_cache and not decision.consent_given

    if use_cache:
        cached = await get_cached_answer(query, source=source)
        if cached is not None:
            usage_logger.info("request cached=True llm_calls=0 tokens=0")
            return {**_response(cached["answer"], cached["sources"], totals, egress), "cached": True}

    try:
        result = await answer_question_graph(session, query, k=k, source=source)
    except PrivacyBlockedError:
        egress.action = PrivacyAction.BLOCK
        return _response(BLOCK_MESSAGE, [], totals, egress)

    if use_cache:
        # Stored after restore: the cache lives inside the privacy boundary.
        await set_cached_answer(query, result, source=source)

    usage_logger.info(
        "request cached=False llm_calls=%d tokens=%d (%.2f%% of daily free-tier quota)",
        totals.calls,
        totals.total_tokens,
        totals.percent_of_daily_quota,
    )
    return _response(result["answer"], result["sources"], totals, egress)


def _response(answer: str, sources: list[dict], totals, egress) -> dict:
    return {
        "answer": answer,
        "sources": sources,
        "cached": False,
        "tokens": totals.total_tokens,
        "llm_calls": totals.calls,
        "privacy": asdict(egress),
    }
