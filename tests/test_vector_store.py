import asyncio

from sqlalchemy import delete

from core.db import async_session
from core.models import Chunk
from services.vector_store import search, store_chunks

SEED_CHUNKS = [
    "The company's return policy allows refunds within 30 days of purchase.",
    "Our office is located in downtown Seattle near the waterfront.",
    "Employees must submit expense reports within two weeks of travel.",
]


async def _reset_and_seed():
    async with async_session() as session:
        await session.execute(delete(Chunk))
        await session.commit()
        await store_chunks(session, texts=SEED_CHUNKS, source="test-fixture")


async def _run_search(query: str, k: int):
    async with async_session() as session:
        return await search(session, query, k=k)


def test_search_returns_most_relevant_chunk_first():
    asyncio.run(_reset_and_seed())

    results = asyncio.run(_run_search("What is the refund policy?", k=2))

    assert len(results) == 2
    assert "refund" in results[0].content.lower()


def test_search_respects_k():
    asyncio.run(_reset_and_seed())

    results = asyncio.run(_run_search("office location", k=1))

    assert len(results) == 1
