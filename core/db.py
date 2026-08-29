from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import get_settings


class Base(DeclarativeBase):
    pass


def get_engine() -> AsyncEngine:
    # NullPool: nothing in this codebase yet holds one persistent event loop
    # (that only starts once a FastAPI app with a lifespan exists). Pooled
    # connections from asyncpg are tied to the event loop that created them,
    # so reusing a pooled connection across separate asyncio.run() calls
    # raises "another operation is in progress". Revisit once there's a
    # single long-lived loop to pool within.
    return create_async_engine(get_settings().database_url, poolclass=NullPool)


engine = get_engine()
async_session = async_sessionmaker(engine, expire_on_commit=False)
