# DocMind — Plan

Agentic RAG document assistant. Built one small, observable unit at a time per `CLAUDE.md`.

## Phases

| # | Concept track | Code track | Status |
|---|---|---|---|
| 1 | Embeddings, cosine similarity | Skeleton, config, Groq client | Done |
| 2 | Chunking strategy and trade-offs | PDF ingest, chunker | Done |
| 3 | Vector indexes, HNSW vs exact | pgvector schema, top-k search | Done |
| 4 | Prompting, grounding, citations | Naive RAG end-to-end | Done |
| 5 | Chains vs graphs, state, reducers | LangGraph rewrite | Done |
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

### Unit 4 — Fixed-size chunker with overlap

- **What:** `services/chunker.py` with `chunk_text(text, chunk_size=500, overlap=50)` — character-based sliding window, raises `ValueError` if `overlap >= chunk_size`.
- **Why:** this phase's actual concept (chunking + overlap trade-offs); the direct next step after extraction, and everything downstream (embeddings, pgvector storage) needs chunks to operate on.
- **Files changed:** `services/chunker.py`, `tests/test_chunker.py`.
- **Command used:** `.venv/bin/python -m pytest -v`
- **Observed result:** 10/10 tests passed (5 existing + 5 new: overlap slicing correctness, shared overlap region between consecutive chunks, empty text, short text, invalid overlap).
- **Design decision:** character-based, not token-based, chunking — the simplest mechanism to observe directly; introducing the embedding model's tokenizer here would pull in a Phase 3 abstraction before chunking itself is understood.
- **Remaining work:** none for this unit. Interview_prep.md §3 written alongside (developer requested side-by-side, not at phase end, for this one).

### Unit 5 — Ingest pipeline (extraction + chunking composed)

- **What:** `services/ingest.py` with `ingest_pdf(pdf_path, chunk_size=500, overlap=50) -> list[str]`, composing `extract_text` + `chunk_text`.
- **Why:** last piece needed to observe Phase 2's "PDF ingest" code-track item end-to-end, not just as two separately-tested units.
- **Files changed:** `services/ingest.py`, `tests/test_ingest.py`.
- **Command used:** `.venv/bin/python -m pytest -v`
- **Observed result:** 12/12 tests passed. Manual run against the real fixture with `chunk_size=40, overlap=10` showed 3 chunks, with the phrase "line prov...proves" correctly surviving intact across the chunk 0/1 boundary.
- **Design decision:** plain function composition, no FastAPI route yet — no router/app layer exists in the repo; HTTP wiring deferred to Phase 4 when the API surface is actually needed.
- **Remaining work:** the `PdfStreamError` failure mode (confirmed to propagate unchanged through the composed pipeline) will need to be caught and mapped to a custom error class once an HTTP upload endpoint exists — not needed yet.

## Remaining work (current phase)

**Phase 2 complete.** Code track (PDF ingest, chunker) fully built and observed end-to-end via `ingest_pdf`; concept track (chunking strategy and trade-offs) written in `Interview_prep.md` §3.

### Unit 6 — Embedder (sentence-transformers, no database yet)

- **What:** `services/embedder.py` with `embed_text(text) -> list[float]`, wrapping `sentence-transformers`' `all-MiniLM-L6-v2`, embeddings L2-normalized at encode time. Validated with a hand-written cosine similarity function (no numpy, no database) against real sentence pairs.
- **Why:** Phase 3 needs embeddings before storage/search mean anything; isolating the embedding model from any database layer means a bug can only be in one place.
- **Files changed:** `services/embedder.py`, `tests/test_embedder.py`, `requirements.txt` (added `sentence-transformers`).
- **Command used:** `.venv/bin/python -m pytest -v`
- **Observed result:** 14/14 tests passed. Manual check showed real cosine scores: cat-sentence pair 0.612, unrelated pair 0.075, and — notably — a negated drug-approval pair scored 0.888, *higher* than the genuinely similar pair. Confirms the negation failure mode predicted in `Interview_prep.md` §1 with real numbers.
- **Remaining work:** none for this unit. Negation failure is expected and tracked for Phase 9, not something to fix now.

### Unit 7 — Postgres + pgvector schema (Docker Compose, Alembic)

- **What:** `docker-compose.yml` running `pgvector/pgvector:pg18`; `core/db.py` (async SQLAlchemy engine/session, `Base`); `core/models.py` (`Chunk` ORM model: `id`, `content: Text`, `source: Text`, `embedding: Vector(384)`); Alembic (async template) with a hand-written migration that runs `CREATE EXTENSION IF NOT EXISTS vector` then creates the `chunks` table. No data inserted, no search yet.
- **Why:** storage half of Phase 3's code track; must exist before any top-k search query.
- **Files changed:** `docker-compose.yml`, `core/db.py`, `core/models.py`, `core/config.py` (added `database_url`), `.env.example` / `.env` (added `DATABASE_URL`), `alembic.ini`, `alembic/env.py`, `alembic/versions/398fbec4f808_create_chunks_table.py`, `requirements.txt` (added `sqlalchemy`, `alembic`, `asyncpg`, `pgvector`).
- **Command used:** `docker compose up -d postgres`, `.venv/bin/alembic upgrade head`, `docker compose exec postgres psql -U docmind -d docmind -c "\d chunks"` and `-c "\dx"`.
- **Observed result:** `\d chunks` confirmed all 4 columns with correct types, `embedding` as `vector(384)`; `\dx` confirmed the `vector` extension (v0.8.6) is enabled. Full pytest suite still 14/14 after the config change.
- **Design decision:** `pgvector/pgvector:pg18` image (extension precompiled) over manual `CREATE EXTENSION` on a plain Postgres image. Async SQLAlchemy + `asyncpg` + Alembic's async template, matching the async-Python-first stack. No index on `embedding` yet — deliberately deferred; exact (brute-force) search comes first per `CLAUDE.md`'s explicit ordering rule.
- **Failure mode discovered:** Postgres 18's Docker image changed its expected volume mount — `docker-compose.yml` originally mounted the volume at `/var/lib/postgresql/data`, which made the container exit immediately (exit code 1) with a message that 18+ images want a single mount at `/var/lib/postgresql` instead (they manage the versioned subdirectory themselves). Fixed by changing the mount path; a real, undocumented-until-you-hit-it infra gotcha, not a code bug.
- **Remaining work:** inserting real embedded chunks and running an actual top-k cosine similarity query — separate next unit.

### Unit 8 — Exact top-k cosine similarity search

- **What:** `services/vector_store.py` with `store_chunks(session, texts, source)` and `search(session, query, k) -> list[Chunk]`, using pgvector's `Chunk.embedding.cosine_distance(query_embedding)` (compiles to SQL `<=>`) with `ORDER BY ... ASC LIMIT k`. No index on `embedding` — full-table exact scan.
- **Why:** the actual "top-k search" deliverable of Phase 3's code track, and the first point retrieval genuinely works end-to-end (embed → store → query → correct ranked results).
- **Files changed:** `services/vector_store.py`, `tests/test_vector_store.py`, `core/db.py` (switched engine to `poolclass=NullPool`).
- **Command used:** `.venv/bin/python -m pytest -v`
- **Observed result:** 16/16 tests passed. Manual query against 3 seeded chunks for "What is the refund policy?" returned the refund chunk first at cosine distance 0.3277, vs. 0.8200 and 0.9880 for the other two — correct ranking with real numbers.
- **Design decision:** used pgvector's SQLAlchemy `.cosine_distance()` comparator (compiles to `<=>`) rather than raw SQL, for type safety and IDE support; functionally identical to hand-written SQL. `store_chunks`/`search` take an `AsyncSession` as a parameter rather than managing their own — keeps the functions testable and avoids hidden global session state.
- **Failure mode discovered:** async engine/connection-pool mismatch across event loops — `core/db.py`'s engine used default pooling, but pytest calling `asyncio.run()` per test spins a fresh event loop each time, and a pooled `asyncpg` connection from a previous loop raised `InterfaceError: cannot perform operation: another operation is in progress` on reuse. Fixed by switching to `poolclass=NullPool` (the same fix Alembic's own async template already used in `env.py`) — every checkout is a fresh connection, no cross-loop reuse. Documented as a deliberate trade-off (no pooling) to revisit once a FastAPI app holds one persistent event loop for the app's lifetime.
- **Break-it experiment:** re-ran the same query with `ORDER BY ... DESC` instead of `ASC` — no error, just a silently and completely inverted ranking (most irrelevant chunk returned first). Confirms the predicted gotcha from the unit proposal.
- **Resume claim earned:** **"Built semantic search over documents using sentence-transformer embeddings and PostgreSQL/pgvector, with exact cosine-similarity top-k retrieval."** Earned now — embed, store, and query have all been observed working together on real data, not just individually.

### Unit 9 — HNSW index + exact-vs-approximate comparison

- **What:** Alembic migration adding `CREATE INDEX chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops)`. Compared query plans via `EXPLAIN ANALYZE` at 3 rows vs. 3003 rows (3000 synthetic random unit vectors inserted temporarily, then deleted).
- **Why:** closes out Phase 3's concept track, "Vector indexes, HNSW vs exact" — the exact half was already observed in Unit 8; this makes the HNSW half concrete with a real query plan instead of only discussed in theory.
- **Files changed:** `alembic/versions/4b925de70d4b_add_hnsw_index_on_chunks_embedding.py`.
- **Command used:** `.venv/bin/alembic upgrade head`; manual `EXPLAIN ANALYZE` runs via a Python script at both row counts; cleanup via `DELETE FROM chunks WHERE source = 'synthetic-bulk-demo'`.
- **Observed result:** at 3 rows, the planner ignored the HNSW index entirely and used `Seq Scan` (correct cost-based choice — index overhead isn't worth it at this size). At 3003 rows, the plan switched to `Index Scan using chunks_embedding_hnsw_idx`. Confirmed the approximate index still returned the correct, genuinely relevant chunk first even among 3000 unrelated random vectors.
- **Design decision:** synthetic bulk data generated with pure-Python `random.gauss` + manual L2 normalization (no numpy dependency added) purely to give the query planner enough rows to consider the index; deleted immediately after the comparison rather than left in the table.
- **Remaining work:** none — synthetic rows cleaned up, table back to 3 real rows, full suite re-confirmed at 16/16.

## Remaining work (current phase)

**Phase 3 complete.** Code track (pgvector schema, top-k search) and concept track (vector indexes, HNSW vs exact) both built and observed with real evidence, not just discussed. Concept notes for Phase 3 (embeddings-in-practice negation gotcha already covered in §1; cosine similarity in §2) plus the new exact-vs-HNSW material go into `Interview_prep.md` §4 next.

### Unit 10 — Naive RAG end-to-end (batched: synthesis + FastAPI app)

Built as one consolidated unit rather than several separate approvals, at the developer's explicit request to move faster on implementation granularity (concept explanations and testing rigor kept; per-file approval checkpoints dropped for this unit onward).

- **What:**
  - `services/rag.py` — `answer_question(session, query, k=3) -> {answer, sources}`: retrieves top-k chunks, builds a grounded prompt (explicit "answer only from context, cite [n]" instruction), calls Groq, returns answer + numbered sources.
  - `services/llm_client.py` — `generate()` extended with an optional `system` parameter (proper system/user role separation instead of concatenating everything into one user message).
  - `core/errors.py` (new) — `DocMindError` base, `InvalidPDFError`. `services/pdf_extractor.py` now catches `pypdf.errors.PdfReadError` and re-raises as `InvalidPDFError`, per the "no bare generic exceptions for expected application failures" convention.
  - `main.py` (new) — FastAPI app with `/health`, `POST /documents` (upload → ingest → embed → store), `POST /query` (ask → retrieve → generate → cite).
  - `schemas/query.py`, `schemas/document.py` (new) — request/response models.
  - `routers/documents.py`, `routers/query.py` (new) — thin route handlers; upload catches `InvalidPDFError` → clean `400`.
  - `core/db.py` — added `get_session()` FastAPI dependency (shared by both routers).
  - Regenerated `tests/fixtures/sample.pdf` with an actual bio (name, background) instead of placeholder text, so retrieval/generation could be tested meaningfully; updated `tests/test_pdf_extractor.py` and `tests/test_ingest.py` assertions to match; added a test for the new `InvalidPDFError` path.
  - `requirements.txt` — added `fastapi`, `uvicorn[standard]`, `python-multipart`, `httpx`.
- **Why:** the actual "naive RAG end-to-end" deliverable of Phase 4, and the first point the system is usable as a real HTTP service instead of only importable Python functions.
- **Command used:** `.venv/bin/python -m pytest -v`; then real HTTP testing — `.venv/bin/uvicorn main:app --port 8001` (8000 was occupied by an unrelated DeliverIQ container) plus `curl` against `/health`, `POST /documents`, and `POST /query`.
- **Observed result:** 17/17 tests passed. Real HTTP round trip: uploaded the bio PDF (`chunks_stored: 1`), asked *"What is the name of this person?"* → `"The person's name is Aria Kapoor. [1]"` with the correct source chunk attached. Asked an out-of-context question (*"What is the capital of France?"*) → `"I don't know."` — grounding held, no hallucination despite an LLM that certainly knows Paris. Uploaded a corrupted file → clean `400` with a readable message, no stack trace leaked.
- **Design decision:** citations are prompt-instructed only, not structurally verified — the LLM could still cite a chunk that doesn't say what it claims, and nothing here checks that. `search()` still has no relevance/similarity threshold, so an irrelevant top-1 chunk gets shown to the LLM as "context" regardless of how weak the match is (Phase 9's locked scope item); grounding currently relies entirely on the LLM honoring the instruction, not a hard cutoff.
- **Failure mode discovered:** port 8000 was already bound by an unrelated, already-running DeliverIQ Docker container on this machine — our first `uvicorn` attempt failed to bind (`[Errno 98] address already in use`) and exited silently in the background, while a `curl` against port 8000 kept "succeeding" because it was actually hitting DeliverIQ's health check the entire time, not ours. Caught by checking the actual server log rather than trusting a 200 response; fixed by moving to port 8001.
- **Resume claim earned:** **"Built a naive RAG system end-to-end over FastAPI: PDF upload, chunking, embedding, pgvector retrieval, and LLM-generated answers with source citations, with verified grounding behavior (refuses out-of-context questions instead of hallucinating)."** Earned now — this was tested as a real running HTTP service, not just unit-tested functions.

### Unit 11 — Citation filtering, document scoping, source B-tree index

Found via real usage (developer uploaded their own resume) rather than planned work — two real bugs surfaced live and got fixed:

- **What:**
  - `services/rag.py` — `sources` in the response now only includes chunks the LLM actually cited (parsed `[n]` refs from the answer), not every retrieved chunk regardless of use. Falls back to all retrieved chunks only if citation parsing finds nothing (best-effort, not guaranteed format).
  - `SYSTEM_PROMPT` tightened to require plain ASCII `[n]` brackets — the model was observed using full-width bracket characters (`〔2〕`) on one run, which silently broke citation parsing.
  - `services/vector_store.py` / `services/rag.py` / `schemas/query.py` / `routers/query.py` — threaded an optional `source` param through `search()` → `answer_question()` → `QueryRequest` → the route, so a query can be scoped to one uploaded document instead of searching the whole `chunks` table.
  - `alembic/versions/3002213eec16_...` — B-tree index on `chunks.source`, since it's now a filter column.
- **Why:** the developer uploaded their real resume and got an answer contaminated by leftover chunks from a previous test document — `search()` had no document scoping at all, competing every uploaded document's chunks for the same top-k slots regardless of which document the user meant to ask about.
- **Command used:** `.venv/bin/alembic upgrade head`; `.venv/bin/python -m pytest -v` (17/17); real HTTP tests with two distinct uploaded documents, scoped vs. unscoped.
- **Observed result:** scoped query to `sample.pdf` → correct answer from that document only; scoped to `second_doc.pdf` → correct answer from that one only; **unscoped query with both documents present → `"I don't know"`**, because the question was genuinely ambiguous across two different people's bios — grounding correctly recognized the ambiguity instead of guessing.
- **Failure mode discovered (unrelated to this unit's own change, found while verifying it):** `tests/test_vector_store.py` does `DELETE FROM chunks` and reseeds its own fixture data every run — and dev and test share the same database (no separate test DB). Running `pytest` silently destroyed manually-uploaded dev/demo data mid-session. Known, real class of bug (shared test/dev state); not fixed here — would need a separate test database or transactional test fixtures, a bigger change than this moment called for. Documented so it's not mistaken for a scoping bug again.
- **Resume claim earned:** extends Unit 10's claim — retrieval can now be scoped per document, and citations reflect only what the model actually used, not a raw dump of everything retrieved.

### Unit 12 — Auto-append `.pdf` to `source` in query requests

- **What:** `schemas/query.py` — `QueryRequest.source` gained a `field_validator` that appends `.pdf` if the given value doesn't already end with it (case-insensitive check). `"sample"` and `"sample.pdf"` now both resolve to `"sample.pdf"`.
- **Why:** developer hit the exact-match B-tree gotcha from Unit 11 firsthand (`source: "sample"` silently matched nothing) and asked for the friction removed.
- **Files changed:** `schemas/query.py`, `tests/test_query_schema.py` (new).
- **Command used:** `.venv/bin/python -m pytest tests/test_query_schema.py -v` (3/3) — deliberately not the full suite, to avoid the Unit 11 test/dev DB collision wiping demo data again; verified live via `curl` with `source: "sample"`.
- **Observed result:** query with `source: "sample"` correctly resolved to `sample.pdf` and returned the right answer.
- **Design decision:** normalization happens at the schema layer (Pydantic validator), before the request reaches any service code — keeps `search()`/`answer_question()` unaware of the convenience and only ever dealing with a fully-qualified source string. Still an exact match after normalization — a genuine typo (`"smple"`) is unaffected and still silently returns nothing; only the extension is forgiving.
- **Resume claim earned:** none new — this is a UX polish fix, not new capability.

## Remaining work (current phase)

**Phase 4 complete**, including three real fixes found and made via actual usage rather than planned testing. Known open item for later: test/dev database separation (surfaced in Unit 11, not yet fixed).

## Phase 5 — LangGraph rewrite

### Unit 13 — 2-node LangGraph graph (retrieve → generate), functionally identical to Phase 4

- **What:** `services/graph.py` — `RAGState` (TypedDict), a `retrieve` node and a `generate` node (logic ported from `services/rag.py`), wired `START → retrieve → generate → END` via `StateGraph`. `answer_question_graph(session, query, k, source)` builds and invokes the graph. Pinned `langgraph==1.2.11` exactly, per `CLAUDE.md`'s pinning rule.
- **Why:** first unit of Phase 5 — prove the graph mechanics (state, node returns, compilation, `ainvoke`) work correctly with zero new behavior, before Phase 6 adds the grade/rewrite loop on top of a graph already known to work.
- **Files changed:** `services/graph.py` (new), `requirements.txt` (added `langgraph==1.2.11`).
- **Command used:** manual comparison script — ran the same question through both `answer_question()` (Unit 10/11's straight-line function) and `answer_question_graph()` against the same live data, no DB mutation.
- **Observed result:** both produced the correct answer ("Maya Chen") with the correct citation; grounding held identically through the graph path (out-of-context question → "I don't know", sources fell back to all retrieved chunks per the Unit 11 fallback rule).
- **Design decision:** no custom reducers defined — `retrieve` and `generate` write disjoint state keys, so LangGraph's default overwrite-on-write behavior is sufficient. This will need to change in Phase 6, when a retry loop needs to *accumulate* state (e.g., a retry counter) across loop iterations rather than overwrite it. Deliberately **not** wired into the `/query` route yet — this graph will still change shape in Phase 6 before it's the real implementation.
- **Remaining work:** none for Phase 5 itself — its code track ("LangGraph rewrite") is exactly what Unit 13 delivers. The grade/rewrite nodes belong to Phase 6 ("Self-correction, bounded loops"), a separate phase.

**Phase 5 complete.** Code track (LangGraph rewrite) observed producing identical results to the pre-graph implementation; concept track (chains vs. graphs, state, reducers) written in `Interview_prep.md` §7.

## Remaining work (current phase)

Phase 6 next: relevance-grading node + query-rewrite node + a conditional edge looping back to `retrieve` on a poor grade, bounded to prevent infinite retries — pending its own proposal/approval. This is where `services/graph.py` actually changes shape and needs its first custom reducer.
