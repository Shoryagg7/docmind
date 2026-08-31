import json

from redis.exceptions import RedisError

from core.redis_client import get_redis_client

CACHE_TTL_SECONDS = 3600


def _cache_key(question: str, source: str | None) -> str:
    return f"docmind:cache:{source or '*'}:{question}"


async def get_cached_answer(question: str, source: str | None = None) -> dict | None:
    client = get_redis_client()
    try:
        raw = await client.get(_cache_key(question, source))
    except RedisError:
        return None
    finally:
        await client.aclose()

    return json.loads(raw) if raw else None


async def set_cached_answer(question: str, answer: dict, source: str | None = None) -> None:
    client = get_redis_client()
    try:
        await client.set(
            _cache_key(question, source), json.dumps(answer), ex=CACHE_TTL_SECONDS
        )
    except RedisError:
        pass
    finally:
        await client.aclose()
