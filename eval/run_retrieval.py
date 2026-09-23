"""Retrieval metrics with no LLM calls: recall@k and MRR over the golden set.

`python -m eval.run_retrieval` (needs the demo docs: `python -m scripts.seed_demo`)

An item counts as retrieved at rank r when the r-th chunk returned by vector search
contains the item's `evidence` string. This measures the first retrieval only, before
any grading or query rewrite. Unanswerable items (no evidence) are skipped.
"""

import asyncio

from sqlalchemy import select

from core.db import async_session
from core.models import Chunk
from eval.golden_set import GOLDEN_SET
from services.vector_store import search

KS = (1, 3, 5)  # the app retrieves k=3


async def verify_evidence(session) -> None:
    """Fail loudly if any evidence string is not in the ingested chunks of its document."""
    missing = []
    for case in GOLDEN_SET:
        if case["evidence"] is None:
            continue
        stmt = select(Chunk.content).where(Chunk.source == case["source"])
        contents = (await session.execute(stmt)).scalars().all()
        if not any(case["evidence"] in content for content in contents):
            missing.append(f"{case['source']}: {case['evidence']!r}")
    if missing:
        raise SystemExit("Evidence not found in ingested chunks:\n  " + "\n  ".join(missing))


async def main() -> None:
    answerable = [c for c in GOLDEN_SET if c["evidence"] is not None]
    hits = {k: 0 for k in KS}
    reciprocal_ranks = []

    async with async_session() as session:
        await verify_evidence(session)
        for case in answerable:
            chunks = await search(session, case["question"], k=max(KS), source=case["source"])
            rank = next(
                (i + 1 for i, c in enumerate(chunks) if case["evidence"] in c.content), None
            )
            for k in KS:
                hits[k] += rank is not None and rank <= k
            reciprocal_ranks.append(1 / rank if rank else 0.0)
            print(f"rank={rank or '-':>2}  {case['question']}")

    n = len(answerable)
    print()
    print(f"answerable items: {n} (every evidence string verified present in the DB)")
    for k in KS:
        print(f"recall@{k}: {hits[k]}/{n} = {hits[k] / n:.3f}")
    print(f"MRR@{max(KS)}: {sum(reciprocal_ranks) / n:.3f}")


if __name__ == "__main__":
    asyncio.run(main())
