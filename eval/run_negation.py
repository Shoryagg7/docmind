import asyncio

from core.db import async_session
from eval.negation_set import CONTROL_PAIRS, NEGATION_PAIRS
from services.embedder import embed_text
from services.vector_store import search


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def similarity(text_a: str, text_b: str) -> float:
    return cosine(embed_text(text_a), embed_text(text_b))


def report_embedding_level() -> None:
    print("=" * 78)
    print("A statement vs. its own NEGATION (opposite meaning — should score LOW)")
    print("=" * 78)
    negation_scores = []
    for pair in NEGATION_PAIRS:
        score = similarity(pair["statement"], pair["negation"])
        negation_scores.append(score)
        print(f"  {score:.4f}  {pair['label']}")

    print()
    print("=" * 78)
    print("Control: genuinely DIFFERENT statements (should score lower than above)")
    print("=" * 78)
    control_scores = []
    for pair in CONTROL_PAIRS:
        score = similarity(pair["statement"], pair["other"])
        control_scores.append(score)
        print(f"  {score:.4f}  {pair['label']}")

    neg_avg = sum(negation_scores) / len(negation_scores)
    ctl_avg = sum(control_scores) / len(control_scores)
    print()
    print(f"  average, statement vs its negation : {neg_avg:.4f}")
    print(f"  average, genuinely different pairs : {ctl_avg:.4f}")
    print(f"  gap                                : {neg_avg - ctl_avg:+.4f}")


async def report_retrieval_level() -> None:
    print()
    print("=" * 78)
    print("Retrieval level: does a negated query retrieve different chunks?")
    print("=" * 78)

    positive = "Are Enterprise customers eligible for the 14-day refund window?"
    negative = "Are Enterprise customers not eligible for the 14-day refund window?"

    async with async_session() as session:
        pos_chunks = await search(session, positive, k=2, source="sample2.pdf")
        neg_chunks = await search(session, negative, k=2, source="sample2.pdf")

    pos_ids = [c.id for c in pos_chunks]
    neg_ids = [c.id for c in neg_chunks]

    print(f"  query A (positive): {positive}")
    print(f"    -> chunk ids {pos_ids}")
    print(f"  query B (negated) : {negative}")
    print(f"    -> chunk ids {neg_ids}")
    print()
    print(f"  same chunks retrieved: {pos_ids == neg_ids}")
    print(f"  query A vs query B similarity: {similarity(positive, negative):.4f}")


async def main() -> None:
    report_embedding_level()
    await report_retrieval_level()


if __name__ == "__main__":
    asyncio.run(main())
