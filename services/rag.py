from sqlalchemy.ext.asyncio import AsyncSession

from services.llm_client import generate
from services.vector_store import search

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions using ONLY the "
    "provided context below. If the context does not contain the answer, "
    "say you don't know — do not use outside knowledge. For every claim "
    "in your answer, cite the source chunk number it came from, like [1]."
)


async def answer_question(session: AsyncSession, query: str, k: int = 3) -> dict:
    chunks = await search(session, query, k=k)

    if not chunks:
        return {"answer": "I don't know — no relevant documents found.", "sources": []}

    context = "\n\n".join(f"[{i + 1}] {chunk.content}" for i, chunk in enumerate(chunks))
    prompt = f"Context:\n{context}\n\nQuestion: {query}"

    answer = generate(prompt, system=SYSTEM_PROMPT)

    sources = [
        {"id": i + 1, "source": chunk.source, "content": chunk.content}
        for i, chunk in enumerate(chunks)
    ]

    return {"answer": answer, "sources": sources}
