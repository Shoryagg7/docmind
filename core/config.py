from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "development"
    groq_api_key: str
    database_url: str = "postgresql+asyncpg://docmind:docmind@localhost:5432/docmind"


@lru_cache
def get_settings() -> Settings:
    return Settings()
