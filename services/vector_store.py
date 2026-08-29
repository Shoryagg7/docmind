from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Chunk
from services.embedder import embed_text


async def store_chunks(session: AsyncSession, texts: list[str], source: str) -> None:
    for text in texts:
        embedding = embed_text(text)
        session.add(Chunk(content=text, source=source, embedding=embedding))
    await session.commit()


async def search(session: AsyncSession, query: str, k: int = 3) -> list[Chunk]:
    query_embedding = embed_text(query)
    stmt = (
        select(Chunk)
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(k)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
