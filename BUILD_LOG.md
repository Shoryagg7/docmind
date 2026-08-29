# DocMind — Build Log

Appended after every successfully completed implementation unit. Each entry: unit name, concept touched, files changed, key design decision, test/command run, observed behavior, one failure mode discovered, whether a new resume claim is earned.

This file exists so a separate teaching assistant can reconstruct exactly what has actually been built, without re-reading the whole codebase.

---

## Unit 1 — Project skeleton + typed config

- **Concept touched:** system-design — centralized, typed configuration via `pydantic-settings` instead of scattered `os.environ` reads, so missing/malformed config fails at import/startup time instead of mid-request. No GenAI concept in this unit; that starts with the embeddings work in Phase 2.
- **Files changed:** `core/config.py`, package `__init__.py` files for `core/`, `routers/`, `services/`, `schemas/`, `tests/`, `tests/test_config.py`, `.env.example`, `.gitignore`, `requirements.txt`.
- **Design decision:** `groq_api_key` has no default (required field) so the app refuses to start without it; `app_env` defaults to `"development"` since it's not security-sensitive. Rejected raw `os.environ.get(...)` calls — no validation, no single source of truth, and explicitly banned by project conventions.
- **Test/command run:** `.venv/bin/python -m pytest -v`
- **Observed behavior:** 3/3 tests passed — settings load from env vars, `app_env` defaults correctly, and a missing `GROQ_API_KEY` raises `ValidationError` instead of silently proceeding.
- **Failure mode discovered:** calling `Settings()` with no `.env` file and no env vars set raises `pydantic_core.ValidationError: groq_api_key Field required` — confirmed live via a bare `python -c` call, not just the test suite.
- **Resume claim earned:** none yet. Config plumbing alone doesn't earn a resume claim — the first earned claim lands once the Groq client makes a real call and the naive RAG path is observable.
