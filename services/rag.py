import re

from sqlalchemy.ext.asyncio import AsyncSession

from services.llm_client import generate
from services.vector_store import search

CITATION_PATTERN = re.compile(r"\[(\d+)\]")

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions using ONLY the "
    "provided context below. If the context does not contain the answer, "
    "say you don't know — do not use outside knowledge. For every claim "
    "in your answer, cite the source chunk number it came from using "
    "plain ASCII square brackets ONLY, exactly like [1] or [2] — never "
    "use any other bracket style (no full-width, no parentheses, no "
    "superscript)."
)


async def answer_question(
    session: AsyncSession, query: str, k: int = 3, source: str | None = None
) -> dict:
    chunks = await search(session, query, k=k, source=source)

    if not chunks:
        return {"answer": "I don't know — no relevant documents found.", "sources": []}

    context = "\n\n".join(f"[{i + 1}] {chunk.content}" for i, chunk in enumerate(chunks))
    prompt = f"Context:\n{context}\n\nQuestion: {query}"

    answer = generate(prompt, system=SYSTEM_PROMPT)

    cited_ids = {int(n) for n in CITATION_PATTERN.findall(answer)}
    all_sources = [
        {"id": i + 1, "source": chunk.source, "content": chunk.content}
        for i, chunk in enumerate(chunks)
    ]
    # Citation parsing is best-effort (the LLM isn't guaranteed to use the
    # exact bracket format asked for) — fall back to all retrieved chunks
    # rather than silently returning zero evidence if parsing finds nothing.
    sources = [s for s in all_sources if s["id"] in cited_ids] or all_sources

    return {"answer": answer, "sources": sources}
