# DocMind — Plan

Agentic RAG document assistant. Built one small, observable unit at a time per `CLAUDE.md`.

## Phases

| # | Concept track | Code track | Status |
|---|---|---|---|
| 1 | Embeddings, cosine similarity | Skeleton, config, Groq client | In progress |
| 2 | Chunking strategy and trade-offs | PDF ingest, chunker | Not started |
| 3 | Vector indexes, HNSW vs exact | pgvector schema, top-k search | Not started |
| 4 | Prompting, grounding, citations | Naive RAG end-to-end | Not started |
| 5 | Chains vs graphs, state, reducers | LangGraph rewrite | Not started |
| 6 | Self-correction, bounded loops | Relevance grader + query rewrite | Not started |
| 7 | Eval methodology, LLM-as-judge | 25-question golden set | Not started |
| 8 | Cache semantics, TTL, thresholds | Redis semantic cache | Not started |
| 9 | Embedding failure modes | Negation set + threshold tuning | Not started |
| 10 | Streaming, token/cost accounting | SSE, UI, logging | Not started |
| 11 | Portfolio polish | README, demo, cleanup | Not started |

A phase is done only after its behavior has been observed and explained, not merely coded.

## Units

Units are logged here as they're completed. See `BUILD_LOG.md` for the detailed per-unit record.

### Unit 1 — Project skeleton + typed config

- **What:** `core/`, `routers/`, `services/`, `schemas/`, `tests/` directory layout; `core/config.py` with a pydantic-settings `Settings` class (`groq_api_key` required, `app_env` defaults to `development`); `.env.example`; `.gitignore`.
- **Why:** everything else in Phase 1 needs a home and a validated way to read secrets, and this is the smallest unit that's both real and observable.
- **Files changed:** `core/config.py`, `core/__init__.py`, `routers/__init__.py`, `services/__init__.py`, `schemas/__init__.py`, `tests/__init__.py`, `tests/test_config.py`, `.env.example`, `.gitignore`, `requirements.txt`.
- **Command used:** `.venv/bin/python -m pytest -v`
- **Observed result:** 3/3 tests passed; a bare `Settings()` call with no `.env`/env vars raises `pydantic_core.ValidationError: groq_api_key Field required`, confirming fail-fast behavior.
- **Remaining work:** developer to create a real local `.env` from `.env.example` and paste their own Groq key (not done through the assistant, to keep the secret out of chat/session logs).

## Remaining work (current phase)

Unit 1 done. Next up (pending approval): a minimal Groq client wrapper + a smoke-test script that makes one real call to `llama-3.3-70b-versatile` and prints the response, proving `GROQ_API_KEY` actually works end-to-end.
