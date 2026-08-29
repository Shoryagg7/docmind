import pytest
from pydantic import ValidationError

from core.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-123")
    monkeypatch.setenv("APP_ENV", "test")

    settings = Settings(_env_file=None)

    assert settings.groq_api_key == "test-key-123"
    assert settings.app_env == "test"


def test_settings_defaults_app_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-123")
    monkeypatch.delenv("APP_ENV", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_env == "development"


def test_settings_fails_loudly_without_groq_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
