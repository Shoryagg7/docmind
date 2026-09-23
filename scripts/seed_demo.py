"""Ingest every demo document in one command: `python -m scripts.seed_demo`.

Re-running is safe: each document's existing chunks are deleted before it is
re-ingested, so the database never holds duplicates.
"""

import asyncio
from pathlib import Path

from sqlalchemy import delete

from core.db import async_session
from core.models import Chunk
from services.ingest import ingest_pdf
from services.vector_store import store_chunks

ROOT = Path(__file__).resolve().parent.parent

DEMO_DOCS = [
    ROOT / "tests" / "fixtures" / "sample.pdf",
    ROOT / "tests" / "fixtures" / "sample2.pdf",
    ROOT / "eval" / "data" / "synthetic_pii.pdf",
]


async def seed() -> None:
    async with async_session() as session:
        for path in DEMO_DOCS:
            chunks = ingest_pdf(path)
            await session.execute(delete(Chunk).where(Chunk.source == path.name))
            await store_chunks(session, chunks, source=path.name)
            print(f"{path.name}: {len(chunks)} chunks")


if __name__ == "__main__":
    asyncio.run(seed())
