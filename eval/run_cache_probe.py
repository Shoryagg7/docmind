"""Semantic-cache threshold probe. Local embeddings only: no Redis, no LLM.

`python -m eval.run_cache_probe`

For each (cached question, incoming question) pair it prints the cosine similarity
the cache would compute, raw and after normalize_question(), and whether the
cache's rule would serve the cached answer: similarity >= SIMILARITY_THRESHOLD
and both questions agree on negation (the same checks as get_cached_answer).
"""

from services.embedder import embed_text
from services.semantic_cache import SIMILARITY_THRESHOLD, has_negation, normalize_question

BASE = "What city does Maya Chen work in?"
TIERS = "Which tiers are eligible for the 14-day refund?"

PAIRS = [
    ("paraphrase (should hit)", BASE, "Which city is Maya Chen based in?"),
    ("paraphrase, no '?' (should hit)", BASE, "Which city is Maya Chen based in"),
    ("different answer: born vs work (must miss)", BASE, "What city was Maya Chen born in?"),
    ("negation (must miss)", TIERS, "Which tiers are not eligible for the 14-day refund?"),
    ("negation, no marker word (must miss)", TIERS, "Which tiers are barred from the 14-day refund?"),
]


def cosine(a: str, b: str) -> float:
    return sum(x * y for x, y in zip(embed_text(a), embed_text(b)))  # vectors are unit length


def main() -> None:
    print(f"threshold = {SIMILARITY_THRESHOLD}")
    for label, cached, incoming in PAIRS:
        raw = cosine(cached, incoming)
        normalized = cosine(normalize_question(cached), normalize_question(incoming))
        hit = normalized >= SIMILARITY_THRESHOLD and has_negation(cached) == has_negation(incoming)
        print(f"{label}")
        print(f"    {cached!r} vs {incoming!r}")
        print(f"    raw {raw:.4f}  normalized {normalized:.4f}  -> {'HIT' if hit else 'miss'}")


if __name__ == "__main__":
    main()
