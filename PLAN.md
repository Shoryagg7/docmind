# DocMind — Plan

Agentic RAG document assistant. Built one small, observable unit at a time per `CLAUDE.md`.

## Phases

| # | Concept track | Code track | Status |
|---|---|---|---|
| 1 | Embeddings, cosine similarity | Skeleton, config, Groq client | Done |
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

### Unit 2 — Groq client wrapper + smoke test

- **What:** `services/llm_client.py` with a `generate(prompt)` function that calls Groq's chat completions API and returns the text response, runnable directly as `python -m services.llm_client`.
- **Why:** last unbuilt piece of Phase 1's code track; first proof the app can actually talk to an LLM.
- **Files changed:** `services/llm_client.py`, `requirements.txt` (added `groq`), `CLAUDE.md` (model pin updated).
- **Command used:** `.venv/bin/python -m services.llm_client`
- **Observed result:** real API round trip returned `"DocMind is alive"`.
- **Design deviation:** the stack's pinned model `llama-3.3-70b-versatile` no longer exists on Groq (404 `model_not_found`). Queried `client.models.list()` against the real key and switched to `openai/gpt-oss-20b` — smaller/faster, better free-tier rate-limit headroom for the multi-call LangGraph phases later. See BUILD_LOG Unit 2 for the full decision.
- **Remaining work:** none — Phase 1 code track is now fully built.

### Unit 3 — PDF text extraction

- **What:** `services/pdf_extractor.py` with `extract_text(pdf_path)`, using `pypdf` to pull raw text out of every page and join with newlines. No upload endpoint, no chunking yet.
- **Why:** first unit of Phase 2; need to see what raw extracted text actually looks like before any chunking strategy decision makes sense.
- **Files changed:** `services/pdf_extractor.py`, `tests/test_pdf_extractor.py`, `tests/fixtures/sample.pdf`, `requirements.txt` (added `pypdf`).
- **Command used:** `.venv/bin/python -m pytest -v`
- **Observed result:** 5/5 tests passed (3 existing + 2 new: successful extraction, missing-file error).
- **Design decision:** chose `pypdf` over `PyMuPDF` (AGPL license, awkward for a public portfolio repo) and `pdfplumber` (heavier, table-focused, unneeded here).
- **Remaining work:** upload endpoint (HTTP plumbing) and chunker (Phase 2's actual concept) are separate future units.

## Remaining work (current phase)

Phase 2 Unit 1 (PDF extraction) done. Next: chunker — the phase's actual concept (chunking strategy, overlap trade-offs) — pending approval.
