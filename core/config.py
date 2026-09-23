from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from core.enums import PrivacyMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "development"
    groq_api_key: str
    database_url: str = "postgresql+asyncpg://docmind:docmind@localhost:5432/docmind"
    redis_url: str = "redis://localhost:6379"
    privacy_mode: PrivacyMode = PrivacyMode.MINIMIZE
    # EVAL_MODE=1 pins temperature=0 on every LLM call (generate, grade, rewrite, judge).
    eval_mode: bool = False
    # pytest runs against this database (the `postgres-test` compose service),
    # never against database_url. See tests/conftest.py.
    test_database_url: str = "postgresql+asyncpg://docmind:docmind@localhost:5433/docmind_test"


@lru_cache
def get_settings() -> Settings:
    return Settings()
