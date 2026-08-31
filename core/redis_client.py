import redis.asyncio as redis

from core.config import get_settings


def get_redis_client() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


if __name__ == "__main__":
    import asyncio

    async def main():
        client = get_redis_client()
        await client.set("docmind:smoke_test", "alive")
        value = await client.get("docmind:smoke_test")
        print(f"Redis says: {value}")
        await client.aclose()

    asyncio.run(main())
