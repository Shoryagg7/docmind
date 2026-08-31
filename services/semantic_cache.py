import hashlib
import json
import re

import numpy as np
from redis.commands.search.field import TagField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import RedisError, ResponseError

from core.redis_client import get_redis_client
from services.embedder import embed_text

INDEX_NAME = "docmind_semcache_idx"
KEY_PREFIX = "docmind:semcache:"
EMBEDDING_DIM = 384
CACHE_TTL_SECONDS = 3600

# Measured against the fixture questions: a true paraphrase scores ~0.94, while
# "what city does she WORK in" vs "what city was she BORN in" scores ~0.87 despite
# having different correct answers. 0.92 sits in that gap, biased toward the strict
# side because serving a wrong cached answer is far worse than missing the cache.
SIMILARITY_THRESHOLD = 0.92

NO_SOURCE = "__all__"

_TAG_SPECIAL = re.compile(r"([,.<>{}\[\]\"':;!@#$%^&*()\-+=~ /\\])")


def _escape_tag(value: str) -> str:
    return _TAG_SPECIAL.sub(r"\\\1", value)


def _entry_key(question: str, source: str | None) -> str:
    digest = hashlib.sha256(f"{source or NO_SOURCE}:{question}".encode()).hexdigest()
    return f"{KEY_PREFIX}{digest}"


def _to_bytes(embedding: list[float]) -> bytes:
    return np.array(embedding, dtype=np.float32).tobytes()


async def ensure_index(client) -> None:
    try:
        await client.ft(INDEX_NAME).info()
        return
    except ResponseError:
        pass

    schema = (
        TagField("source"),
        VectorField(
            "embedding",
            "FLAT",
            {"TYPE": "FLOAT32", "DIM": EMBEDDING_DIM, "DISTANCE_METRIC": "COSINE"},
        ),
    )
    definition = IndexDefinition(prefix=[KEY_PREFIX], index_type=IndexType.HASH)
    await client.ft(INDEX_NAME).create_index(schema, definition=definition)


async def get_cached_answer(question: str, source: str | None = None) -> dict | None:
    client = get_redis_client()
    try:
        await ensure_index(client)

        query = (
            Query(f"(@source:{{{_escape_tag(source or NO_SOURCE)}}})=>[KNN 1 @embedding $vec AS dist]")
            .return_fields("question", "answer", "dist")
            .sort_by("dist")
            .dialect(2)
        )
        result = await client.ft(INDEX_NAME).search(
            query, query_params={"vec": _to_bytes(embed_text(question))}
        )
    except RedisError:
        return None
    finally:
        await client.aclose()

    if not result.docs:
        return None

    best = result.docs[0]
    similarity = 1.0 - float(best.dist)
    if similarity < SIMILARITY_THRESHOLD:
        return None

    return json.loads(best.answer)


async def set_cached_answer(question: str, answer: dict, source: str | None = None) -> None:
    client = get_redis_client()
    try:
        await ensure_index(client)

        key = _entry_key(question, source)
        await client.hset(
            key,
            mapping={
                "question": question,
                "source": source or NO_SOURCE,
                "answer": json.dumps(answer),
                "embedding": _to_bytes(embed_text(question)),
            },
        )
        await client.expire(key, CACHE_TTL_SECONDS)
    except RedisError:
        pass
    finally:
        await client.aclose()
