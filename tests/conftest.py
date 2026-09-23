"""Point the whole test session at the test database before any app code loads.

core/db.py builds its engine at import time from DATABASE_URL, so the override
has to happen here, before pytest imports any test module.
"""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config

# Tests never talk to Groq. A fake key means an accidental real call fails with
# 401 instead of silently spending the real quota.
os.environ["GROQ_API_KEY"] = "test-key-never-sent"

from core.config import Settings  # noqa: E402  (must follow the env override)

_settings = Settings()
if _settings.test_database_url == _settings.database_url:
    raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL")
os.environ["DATABASE_URL"] = _settings.test_database_url


def pytest_configure(config):
    # Build the schema with the real migrations, so tests also exercise them.
    command.upgrade(Config(str(Path(__file__).parent.parent / "alembic.ini")), "head")
