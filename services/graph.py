import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Chunk
from services.grader import grade_relevance
from services.llm_client import generate
from services.rag import CITATION_PATTERN, SYSTEM_PROMPT
from services.semantic_cache import get_cached_answer, set_cached_answer
from services.vector_store import search

MAX_RETRIES = 2

REWRITE_SYSTEM_PROMPT = (
    "You rewrite search queries that failed to retrieve relevant results. "
    "Given the original question, produce one rephrased version more likely to "
    "match relevant document text. Reply with only the rewritten question, nothing else."
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


def build_graph(session: AsyncSession):
    async def retrieve_node(state: RAGState) -> dict:
        chunks = await search(session, state["query"], k=state["k"], source=state["source"])
        return {"chunks": chunks}

    async def grade_node(state: RAGState) -> dict:
        relevant = [c for c in state["chunks"] if grade_relevance(state["query"], c.content)]
        return {"relevant_chunks": relevant}

    async def rewrite_node(state: RAGState) -> dict:
        rewritten = generate(state["query"], system=REWRITE_SYSTEM_PROMPT)
        return {"query": rewritten.strip(), "retry_count": 1}

    def should_retry(state: RAGState) -> str:
        if not state["relevant_chunks"] and state["retry_count"] < MAX_RETRIES:
            return "rewrite"
        return "generate"

    async def generate_node(state: RAGState) -> dict:
        chunks = state["relevant_chunks"]
        if not chunks:
            return {"answer": "I don't know — no relevant documents found.", "sources": []}

        context = "\n\n".join(f"[{i + 1}] {c.content}" for i, c in enumerate(chunks))
        prompt = f"Context:\n{context}\n\nQuestion: {state['query']}"
        answer = generate(prompt, system=SYSTEM_PROMPT)

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
        }
    )
    return {"answer": result["answer"], "sources": result["sources"]}


async def answer_question_cached(
    session: AsyncSession, query: str, k: int = 3, source: str | None = None
) -> dict:
    cached = await get_cached_answer(query, source=source)
    if cached is not None:
        return {**cached, "cached": True}

    result = await answer_question_graph(session, query, k=k, source=source)
    await set_cached_answer(query, result, source=source)
    return {**result, "cached": False}
