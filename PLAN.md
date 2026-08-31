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
| 6 | Self-correction, bounded loops | Relevance grader + query rewrite | Done |
| 7 | Eval methodology, LLM-as-judge | 25-question golden set | Done |
| 8 | Cache semantics, TTL, thresholds | Redis semantic cache | Done |
| 9 | Embedding failure modes | Negation set + threshold tuning | Done |
| 10 | Streaming, token/cost accounting | SSE, UI, logging | Done |
| 11 | Portfolio polish | README, demo, cleanup | Done |

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

## Phase 6 — Self-correction, bounded loops

### Unit 14 — Relevance grader (standalone)

- **What:** `services/grader.py` with `grade_relevance(query, chunk_content) -> bool` — one LLM call, forced to a strict yes/no reply via a dedicated system prompt.
- **Why:** the conditional edge Phase 6 needs can't be built without a signal to condition on first; isolating the grader means it can be verified correct before any control flow depends on it.
- **Files changed:** `services/grader.py`.
- **Command used:** `.venv/bin/python -m services.grader`
- **Observed result:** correctly graded a genuinely relevant chunk as relevant and a genuinely irrelevant chunk as irrelevant, on real content from `sample.pdf`/`sample2.pdf`.
- **Design decision:** rejected using `search()`'s own cosine-distance score as the relevance signal — a chunk can be embedding-close without answering the question (negation is the sharpest case, already documented in `Interview_prep.md` §1); LLM-as-judge catches that, a distance cutoff can't.
- **Remaining work:** not yet wired into the graph — next unit.

### Unit 15 — Graph rewired: grade + rewrite nodes, conditional edge, bounded retry

- **What:** `services/graph.py` extended with `grade_node`, `rewrite_node`, a `should_retry` conditional-edge function, `MAX_RETRIES = 2`, and `retry_count: Annotated[int, operator.add]` added to `RAGState`. Edges: `retrieve → grade → (rewrite | generate)`, `rewrite → retrieve`.
- **Why:** the actual self-correction mechanics — grading retrieved chunks and retrying with a rewritten query when they're weak, bounded so it can't loop forever.
- **Files changed:** `services/graph.py`.
- **Command used:** normal-path re-run of the graph against `sample.pdf`; a forced-failure trace via `graph.astream()` asking a question the scoped document can't answer.
- **Observed result:** normal path unchanged. Forced failure: graded 0 relevant chunks → rewrote the query → graded 0 again → rewrote a second time → graded 0 a third time → routed to `generate`, returning `"I don't know"` instead of looping again. `retry_count` accumulated 0 → 1 → 2 correctly via the reducer.
- **Design decision:** `retry_count` uses `Annotated[int, operator.add]` so `rewrite_node` returns a delta (`{"retry_count": 1}`) instead of computing the running total itself — the concrete case the reducer concept was flagged for back in Unit 13.
- **Remaining work:** still not wired into `/query` — next unit.

### Unit 16 — Wired the graph into `/query`

- **What:** `routers/query.py` now calls `services.graph.answer_question_graph` instead of `services.rag.answer_question`.
- **Why:** last step to make the self-correcting graph the actual code path serving real queries, not just something exercised in test scripts.
- **Files changed:** `routers/query.py`.
- **Command used:** `.venv/bin/uvicorn main:app --port 8001`; `curl -X POST http://localhost:8001/query` with a real question against `sample.pdf`.
- **Observed result:** `{"answer": "Maya Chen works in Toronto. [1]", "sources": [...]}` — correct grounded answer with citation, now actually served by the graph.
- **Design decision:** `services/rag.py::answer_question()` kept in the codebase, unused by any route — the "before" reference implementation, referenced by `Interview_prep.md` §6/§7 and the retrieval-pipeline diagram.
- **Remaining work:** none for Phase 6 itself.

## Remaining work (current phase)

**Phase 6 complete.** Code track (relevance grader, query rewrite, conditional edge, bounded retry) built, wired into `/query`, and observed on both the happy path and a forced failure exercising the full retry-then-give-up behavior. Concept track (self-correction, bounded loops) written in `Interview_prep.md` §8; §7 updated to reflect the graph's final 4-node shape.

**Earned claim:** "Built an agentic RAG pipeline in LangGraph with self-correcting retrieval — a relevance-grading node and bounded query-rewrite retries — serving live queries end-to-end."

## Phase 7 — Eval methodology, LLM-as-judge

### Unit 17 — Eval harness on a 3-question golden set

- **What:** `eval/golden_set.py` (question/source/reference_answer triples), `eval/judge.py` (`llm_as_judge()`, a separate LLM call forced to strict correct/incorrect), `eval/run_eval.py` (runs each question through `answer_question_graph`, judges it, prints a pass/fail summary).
- **Why:** the judging mechanism is what's actually worth proving before writing 25 questions' worth of data on top of it.
- **Command used:** `docker compose up -d postgres` (had stopped between sessions); `.venv/bin/python -m eval.run_eval`.
- **Observed result:** first run 2/3 — genuine unplanned failure, traced to a wrong reference answer in the golden set itself (asked about a "free tier" that doesn't exist in `sample2.pdf`); the system's "I don't know" was actually correct. Fixed the golden set to match real document content; re-run 3/3.
- **Design decision:** LLM-as-judge over string-similarity scoring, since correct answers vary in phrasing.
- **Remaining work:** scale from 3 to 25 questions across both fixture documents, covering both answerable and deliberately unanswerable cases.

### Unit 18 — Scaled golden set to 25 questions

- **What:** `eval/golden_set.py` grown to 25 entries — 12 against `sample.pdf`, 10 against `sample2.pdf`, 3 deliberately unanswerable (out-of-scope topic, wrong-document scoping, topic in neither document).
- **Why:** the actual "25-question golden set" deliverable; every reference answer verified against real chunk content in Postgres first, directly because Unit 17 caught a fabricated one.
- **Command used:** `docker compose up -d postgres`; `.venv/bin/python -m eval.run_eval`.
- **Observed result:** 25/25 passed — all answerable questions correct and cited, all 3 unanswerable questions correctly refused rather than guessed.
- **Design decision:** the 3 unanswerable cases were chosen to cover 3 distinct reasons an answer can legitimately not exist, not just one repeated pattern.
- **Failure mode discovered:** Unit 11's citation-format gotcha (full-width `【1】` brackets) recurred live in this run; absorbed by the existing fallback, didn't affect scoring, logged as evidence the underlying non-determinism is still real.
- **Remaining work:** none for Phase 7 itself.

## Remaining work (current phase)

**Phase 7 complete.** Code track (25-question golden set, LLM-as-judge harness) built and observed at 25/25 against the live graph-based `/query` implementation. Concept track (eval methodology, LLM-as-judge) written in `Interview_prep.md` §9.

**Earned claim:** "Built a 25-question golden evaluation set with an LLM-as-judge scoring harness, covering both correctly-answerable and deliberately-unanswerable queries, and used it to verify grounding held across the full agentic RAG pipeline."

## Phase 8 — Redis semantic cache

### Unit 19 — Redis Stack service + connectivity

- **What:** `redis` service added to `docker-compose.yml` (`redis/redis-stack-server`), `redis_url` added to settings, `core/redis_client.py` with `get_redis_client()` and a runnable smoke test. No caching logic.
- **Why:** the cache can't be built before Redis is reachable from the app; smallest observable slice, matching the "plumbing before logic" pattern used in Units 7 and 13.
- **Files changed:** `docker-compose.yml`, `core/config.py`, `core/redis_client.py`, `requirements.txt`.
- **Command used:** `docker compose up -d redis`; `.venv/bin/python -m core.redis_client`.
- **Observed result:** `Redis says: alive` — real SET/GET round trip through the app's async client; `redis-cli ping` → `PONG`.
- **Design decision:** Redis **Stack** (not plain Redis) because RediSearch provides the vector index the semantic cache needs; plain Redis only does exact-key lookup, which is the approach being rejected. No volume mounted — a cache isn't a source of truth, so losing it on restart is correct.
- **Failure mode discovered:** with Redis stopped, the client raises `ConnectionError: Error 111`. Directly constrains the next unit: the cache must treat Redis being down as a cache miss and fall through to the graph, never propagate the exception — a cache that can take down `/query` is worse than no cache.
- **Remaining work:** the actual semantic cache — embed the incoming question, vector-search prior cached questions in Redis, return the cached answer above a similarity threshold, otherwise run the graph and store the result with a TTL.

### Unit 20 — Exact-match cache (deliberately the naive version)

- **What:** `services/cache.py` — `get_cached_answer()` / `set_cached_answer()`, keyed on `f"docmind:cache:{source}:{question}"` with a 1-hour TTL, and `RedisError` swallowed on both read and write.
- **Why:** build the naive key-on-raw-string version first and watch it miss a paraphrase — the same "see the limitation before buying the fix" pattern as exact search before HNSW. Costs zero Groq tokens to demonstrate, which matters while the daily quota is exhausted.
- **Files changed:** `services/cache.py`.
- **Command used:** throwaway script caching one question, then looking up the identical string, a paraphrase, and a different document scope; re-run with `docker compose stop redis`.
- **Observed result:** identical string → HIT; paraphrase *"Which city is Maya Chen based in?"* → **MISS**; other document scope → MISS (correct). Redis stopped → all MISS, no exception.
- **Design decision:** cache key includes `source` so one document's cached answer can never serve another's query. Fresh client per call rather than a cached singleton, deliberately avoiding the cross-event-loop reuse bug hit in Unit 8.
- **Remaining work:** replace the exact key with an embedding + similarity threshold so the paraphrase hits.

### Unit 21 — Semantic cache (RediSearch vector index + threshold)

- **What:** `services/semantic_cache.py` — cached entries stored as Redis hashes (question, source TAG, answer JSON, 384-dim FLOAT32 embedding) behind a RediSearch `FLAT` cosine index; lookup embeds the incoming question, runs a KNN-1 search filtered by `source`, and returns the cached answer only if similarity ≥ `SIMILARITY_THRESHOLD`.
- **Why:** the direct fix for Unit 20's paraphrase miss.
- **Files changed:** `services/semantic_cache.py`.
- **Command used:** throwaway script caching one question then looking up 5 variants + a wrong-document scope; then a threshold sweep at 0.92 vs 0.85.
- **Observed result:** all six correct — identical → HIT, **paraphrase → HIT**, born-in → MISS, different question → MISS, unrelated → MISS, other document → MISS.
- **Design decision:** threshold `0.92` chosen from measured similarities, not intuition — paraphrase 0.9399, dangerous near-miss ("born in" vs "work in", different answers) 0.8718, same-person-different-question 0.8011. Only a 0.068 window; biased strict because a false hit is far more costly than a miss. `FLAT` not HNSW (a few hundred entries don't need ANN, and exact search removes approximation as a variable while tuning the threshold).
- **Failure mode discovered:** at threshold 0.85, *"What city was Maya Chen **born** in?"* is served the cached *"Maya Chen works in Toronto"* — wrong answer, instant, with a citation, and **zero LLM calls in the path to catch it**. A cache hit bypasses both Phase 4 grounding and Phase 6 relevance grading, making the cache the only component with no safety net behind it.
- **Remaining work:** wire into `/query` via a cache-aside wrapper, and measure the actual token/latency saving on a hit.

### Unit 22 — Cache-aside wiring into `/query`

- **What:** `answer_question_cached()` in `services/graph.py` (check cache → on miss run the graph → store → return), `routers/query.py` switched to it, `QueryResponse.cached: bool` added so hits are visible to the client.
- **Why:** makes the cache real rather than a library sitting unused, and lets the saving be measured.
- **Files changed:** `services/graph.py`, `routers/query.py`, `schemas/query.py`.
- **Command used:** `redis-cli FLUSHALL`; server on 8001; four timed `curl` calls.
- **Observed result:** cold **9.62s** (`cached:false`) → identical question **0.01s** (`cached:true`) → **paraphrase never asked before 0.01s** (`cached:true`, correct answer) → near-miss "born in" **3.95s** (`cached:false`, correctly answered **Vancouver**).
- **Design decision:** wrapper sits outside the graph (a hit must skip graph construction and all its LLM calls, so an `if` beats a node + conditional edge). **`eval/run_eval.py` intentionally still calls the uncached `answer_question_graph()`** — routing eval through the cache would make every run after the first replay cached answers, reporting a perfect score while testing nothing.
- **Failure mode noted:** a hit is ~960× faster precisely because it skips retrieval, grading, and generation — the benefit and the risk are the same fact. Also, the full-width `【1】` citation quirk persists on `gpt-oss-120b`, so it's general model behaviour rather than model-specific.

## Remaining work (current phase)

**Phase 8 complete.** Code track (Redis Stack, exact-match strawman, semantic cache with measured threshold, cache-aside wiring) built and observed end-to-end over HTTP. Concept track written in `Interview_prep.md` §10.

**Earned claim:** "Implemented a Redis semantic query cache using RediSearch vector similarity with a measured similarity threshold, wired into the query endpoint as a cache-aside layer — cutting repeat and paraphrased queries from ~9.6s to ~0.01s with zero LLM calls, while preserving correctness on near-miss questions."

## Phase 9 — Embedding failure modes

### Unit 23 — Negation test set

- **What:** `eval/negation_set.py` (6 statement/negation pairs + 3 control pairs), `eval/run_negation.py` (measures embedding-level similarity and retrieval-level impact). Zero Groq calls.
- **Why:** Phase 9's core concept, and the Unit 6 negation observation (0.888 on one example) deserved to become a measured set rather than an anecdote.
- **Files changed:** `eval/negation_set.py`, `eval/run_negation.py`.
- **Command used:** `.venv/bin/python -m eval.run_negation`, plus two targeted cache probes.
- **Observed result:**
  - Embedding: negation pairs avg **0.8728** vs control (genuinely different) avg **0.4692**. Worst case 0.9586 (SOC 2 certified vs not certified).
  - Retrieval: positive and negated queries retrieved **identical chunks** — survivable, since the chunk contains the negated fact and grounded generation still answers correctly.
  - Cache: *"Which tiers **are** eligible for a refund?"* vs *"Which tiers are **not** eligible?"* = **0.9879** → **CACHE HIT, wrong answer served** with a citation and no LLM in the path.
- **Design decision:** measured against a control set, not in isolation — a 0.87 is meaningless without knowing that genuinely-different text scores 0.47.
- **Failure mode discovered:** **no threshold can fix this.** The negation scores **0.9879** while the paraphrase the cache exists to catch scores **0.9399** — the thing to reject scores higher than the thing to accept. Phase 8's 0.92 threshold protects against near-miss questions and is provably useless against negation.
- **Remaining work:** a mitigation. The cache needs a negation guard that doesn't rely on similarity at all.

### Unit 24 — Lexical negation guard on cache lookups

- **What:** `has_negation()` in `services/semantic_cache.py`, plus a polarity check that rejects a cache hit when the incoming and cached questions disagree on negation markers. Runs after the threshold check, costs one regex.
- **Why:** Unit 23 proved similarity cannot separate a question from its negation, so the guard has to use a signal from outside the embedding.
- **Files changed:** `services/semantic_cache.py`.
- **Command used:** `redis-cli FLUSHALL`; Unit 21 suite as regression check; negation suite; failure-probe suite.
- **Observed result:** negated forms (0.9879 and 0.9896) now **MISS** instead of serving wrong answers. No regression — all six Unit 21 cases still correct, and a genuine paraphrase at 0.9539 still HITs.
- **Design decision:** guard placed after the similarity check (only runs on candidates that already passed) and based on lexical markers rather than any learned signal, so it adds no latency and no LLM call to the path the cache exists to make fast.
- **Failure mode discovered:** measured in both directions. **False negative (dangerous):** *"Which tiers are **barred from** the refund?"* scores 0.9273 with no lexical marker → still HITs → still wrong. Vocabulary-level negation defeats the guard. **False positive (safe):** *"...with **no** restrictions"* trips the marker in a non-negating role and loses a legitimate hit. This is a mitigation, not a fix — a real fix needs a cross-encoder or an LLM verification step on hits, which costs the latency the cache exists to save.

## Remaining work (current phase)

**Phase 9 complete.** Code track (negation set, threshold analysis, negation guard) built and measured; concept track written in `Interview_prep.md` §11.

**Earned claim:** "Built a negation test set demonstrating that embedding similarity cannot distinguish a statement from its opposite (0.87 avg vs 0.47 for genuinely different text), showed this defeats similarity-threshold semantic caching by construction, and mitigated it with a lexical negation guard — with the guard's own residual failure mode measured rather than assumed."

## Phase 10 — Streaming, UI, token/cost accounting

### Unit 25 — Token accounting

- **What:** `core/usage.py` (per-call logging + `ContextVar`-based per-request totals), usage recorded inside `llm_client.generate()`, every call site labelled (`grade` / `rewrite` / `generate` / `judge`), `tokens` and `llm_calls` returned on `QueryResponse`.
- **Why:** the quota wall hit during Phase 7/9 was invisible — this is the instrument that makes spend observable before it becomes a 429.
- **Files changed:** `core/usage.py`, `services/llm_client.py`, `services/grader.py`, `services/graph.py`, `eval/judge.py`, `schemas/query.py`, `main.py`.
- **Command used:** server on 8001, `redis-cli FLUSHALL`, one cold query then a repeat.
- **Observed result:** cold → `tokens: 1221, llm_calls: 4`; repeat (cache hit) → `tokens: 0, llm_calls: 0`. Log attributes each call: 3 × `grade` (276/289/292) + 1 × `generate` (364), then a per-request total with `0.61% of daily free-tier quota`.
- **Design decision:** instrument the single client choke point rather than each call site (captures 100% of spend with one edit); `ContextVar` rather than a module global, since FastAPI serves concurrent requests on one event loop and a global would blend users' usage together.
- **Failure mode / finding:** **grading is 70% of token cost** (857 of 1221) versus 30% for the actual answer, because it fires once per retrieved chunk. Derived: ~163 queries/day on the free tier; a 25-question eval run ≈ 39,000 tokens; ~5 eval runs exhausts the quota — matching exactly what happened during the chunk-size experiment. Also retroactively justifies Phase 8, since a cache hit costs 0 tokens.
- **Remaining work:** SSE streaming endpoint, then the static HTML page.

### Unit 26 — SSE streaming + static UI

- **What:** `generate_stream()` in `llm_client.py`; `defer_generation` flag on `RAGState` so the graph runs retrieve/grade/rewrite but stops before generating; `POST /query/stream` emitting SSE stage + token + done events; `static/index.html` served at `/`.
- **Why:** makes the whole agentic pipeline visible in one place — the payoff demo for the project.
- **Files changed:** `services/llm_client.py`, `services/graph.py`, `routers/stream.py`, `static/index.html`, `main.py`.
- **Command used:** `redis-cli FLUSHALL`; `curl -sN` against `/query/stream` cold then cached; `curl /`.
- **Observed result:** cold → stage events (cache miss → retrieved 3 chunks → graded 1 relevant → generating) then **12 separate token events**, then `done calls=4 tokens=1246`. Cached → one `cache hit` stage, `calls=0 tokens=0`. Page serves 200.
- **Design decision:** reuse the graph rather than reimplement it — `defer_generation` lets the route stream the final call while retrieval, grading and bounded retry still run through the real graph. Stage events come from `graph.astream()`, so they are actual node transitions, not a scripted animation.
- **Failure modes discovered:** (1) `astream()` yields `None` (not `{}`) for a node that changes no state → crash on `**update`. (2) Installed Groq SDK rejects `stream_options` — probing showed usage is attached to the final chunk automatically. (3) `pkill -f "uvicorn main:app"` kills its own shell when the same command also contains the launch line; use `fuser -k 8001/tcp`.

### Unit 27 — Query normalization before embedding

- **What:** `normalize_question()` in `services/semantic_cache.py` (casefold, collapse whitespace, strip trailing punctuation), applied at the embedding and key-digest steps; the original question text is still stored for display and the negation guard.
- **Why:** found by real UI use — typing *"Which city is Maya Chen based in"* without a question mark missed a paraphrase that had previously measured as a hit.
- **Files changed:** `services/semantic_cache.py`.
- **Command used:** before/after similarity comparison across 6 variants; end-to-end cache probes; Unit 21 suite as regression check.
- **Observed result:** the trailing `?` alone was worth **0.065** (0.9399 → 0.8754) — nearly the whole 0.068 safe window, and within 0.0036 of the dangerous "born in" score of 0.8718. After normalization all three paraphrase variants collapse to an identical **0.9654**; all Unit 21 cases still pass.
- **Unexpected benefit:** the safe window **widened ~41%** (0.068 → 0.096), because removing variance irrelevant to meaning made the meaningful signal easier to separate.

### Unit 28 — Full UI: upload, chat history, query controls

- **What:** `GET /documents` endpoint; UI rebuilt with PDF upload, persistent chat turns, a document list driven by real DB state, a top-k control, and a `bypass_cache` flag.
- **Why:** the pipeline was built but not operable — no upload path in the UI, and after one query the cache made streaming undemonstrable.
- **Files changed:** `routers/documents.py`, `routers/stream.py`, `schemas/document.py`, `schemas/query.py`, `static/index.html`.
- **Command used:** `GET /documents`; upload via `-F "file=@..."`; `/query/stream` with `bypass_cache:true`; `pytest`.
- **Observed result:** documents list correct; upload → `{"source":"uitest.pdf","chunks_stored":4}` and immediately selectable; bypass flag produces a full pipeline run; 20/20 tests pass.
- **Failure mode discovered:** `pytest` left a `test-fixture` document visible in the UI's document list — the Unit 11 shared test/dev database issue now leaking into the product surface, not just manual testing.

### Unit 29 — Portfolio polish

- **What:** `README.md`; `REDIS_URL` added to `.env.example` (missing since Unit 19); test-pollution cleanup; cache flushed to a clean demo state.
- **Why:** Phase 11 — make the project legible to someone arriving cold.
- **Files changed:** `README.md`, `.env.example`.
- **Command used:** `pytest -q`; fixture re-ingest; `DELETE FROM chunks WHERE source='test-fixture'`; `redis-cli FLUSHALL`.
- **Observed result:** 20/20 tests pass; DB holds exactly the two demo documents (9 chunks); cache empty.
- **Design decision:** README leads with measured findings rather than a feature list, and states six known limitations explicitly — a portfolio project claiming no weaknesses reads as unexamined.

## Remaining work

**All 11 phases complete.** Code track and concept track both finished; `Interview_prep.md` has 12 sections covering every major concept, each with a decision, trade-off, gotcha, and self-test.

Optional future work (all deliberately out of the locked scope): separate test database, cache-error observability, citation verification, reranking or hybrid BM25/vector search, multi-user auth, deployment.

**Earned claims:** token accounting through a single choke point (grading = 70% of per-query tokens; ~163 queries/day on free tier); SSE streaming with live agent-stage events and per-request cost surfaced in the UI.

Phase 11 next: portfolio polish — README, demo, cleanup — pending its own proposal/approval.
