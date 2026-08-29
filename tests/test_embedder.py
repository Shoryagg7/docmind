import math

from services.embedder import embed_text


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)


def test_embed_text_returns_384_dim_vector():
    embedding = embed_text("The cat sat on the mat.")
    assert len(embedding) == 384


def test_similar_sentences_score_higher_than_unrelated_ones():
    cat_a = embed_text("The cat sat on the mat.")
    cat_b = embed_text("A kitten rested on the rug.")
    unrelated = embed_text("The stock market fell sharply today.")

    similar_score = cosine_similarity(cat_a, cat_b)
    unrelated_score = cosine_similarity(cat_a, unrelated)

    assert similar_score > unrelated_score
    assert similar_score > 0.5
    assert unrelated_score < similar_score - 0.2
