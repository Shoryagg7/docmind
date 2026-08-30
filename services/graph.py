from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Chunk
from services.llm_client import generate
from services.rag import CITATION_PATTERN, SYSTEM_PROMPT
from services.vector_store import search


class RAGState(TypedDict):
    query: str
    k: int
    source: str | None
    chunks: list[Chunk]
    answer: str
    sources: list[dict]


def build_graph(session: AsyncSession):
    async def retrieve_node(state: RAGState) -> dict:
        chunks = await search(session, state["query"], k=state["k"], source=state["source"])
        return {"chunks": chunks}

    async def generate_node(state: RAGState) -> dict:
        chunks = state["chunks"]
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
    graph.add_node("generate", generate_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


async def answer_question_graph(
    session: AsyncSession, query: str, k: int = 3, source: str | None = None
) -> dict:
    graph = build_graph(session)
    result = await graph.ainvoke(
        {"query": query, "k": k, "source": source, "chunks": [], "answer": "", "sources": []}
    )
    return {"answer": result["answer"], "sources": result["sources"]}
