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

---

## Unit 2 — Groq client wrapper + smoke test

- **Concept touched:** prompt construction (trivial form — single user message, no system prompt or RAG context yet) and, incidentally, real-world API/model lifecycle risk: a pinned model can be deprecated out from under you.
- **Files changed:** `services/llm_client.py` (new), `requirements.txt` (added `groq>=0.11`), `CLAUDE.md` (Stack section model pin updated).
- **Design decision:** pinned model `llama-3.3-70b-versatile` from the original stack spec returned `404 model_not_found` — Groq has removed it from their catalog since the prompt was written. Called `client.models.list()` against the real key to see what's actually available: `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `groq/compound`(-mini), a couple Qwen models, and safety/audio models — no Llama chat model remained. Chose `openai/gpt-oss-20b` over `openai/gpt-oss-120b`: faster and more free-tier rate-limit headroom, which matters once Phase 5–6's LangGraph loop fires several LLM calls per query (retrieve → grade → rewrite → synthesize); `120b`'s reasoning ceiling isn't needed yet and the model constant is a one-line swap later if quality becomes the bottleneck.
- **Test/command run:** `.venv/bin/python -m services.llm_client`
- **Observed behavior:** real round trip to Groq returned `"DocMind is alive"`.
- **Failure modes discovered:** (1) wrong/deprecated model name → `groq.NotFoundError` (404, `model_not_found`); (2) invalid API key → `groq.AuthenticationError` (401, `invalid_api_key`). Distinct from Unit 1's `pydantic.ValidationError` for missing config entirely — three different failure layers (config missing / bad credential / bad model) now each have a known, distinguishable error signature.
- **Resume claim earned:** "Integrated Groq's hosted LLM API (`openai/gpt-oss-20b`) for text generation." Not yet "built a RAG system" or "agentic" anything — those require retrieval, grounding, and the LangGraph loop, none of which exist yet.

**Phase 1 complete.** Code track (skeleton, config, Groq client) fully built and observed; concept track (embeddings, cosine similarity) pre-written in `Interview_prep.md` §1–2 ahead of the code, per this phase's role as conceptual grounding before Phase 2/3 actually use embeddings.

---

## Unit 3 — PDF text extraction

- **Concept touched:** none GenAI-specific — this is data-prep groundwork. The real concept for this phase (chunking strategy and trade-offs) lands in the next unit, once there's real extracted text to chunk.
- **Files changed:** `services/pdf_extractor.py` (new), `tests/test_pdf_extractor.py` (new), `tests/fixtures/sample.pdf` (new, generated once via a temporary `reportlab` install, not a project dependency), `requirements.txt` (added `pypdf>=5.0`).
- **Design decision:** `pypdf` chosen over `PyMuPDF` (better text fidelity but AGPL-licensed — awkward for code in a public portfolio repo) and `pdfplumber` (heavier, table-structure-focused, not needed here). `extract_text` takes a path, not a stream — the upload endpoint that would need stream support doesn't exist yet, so no reason to widen the signature now.
- **Test/command run:** `.venv/bin/python -m pytest -v`
- **Observed behavior:** 5/5 tests passed; extraction returns the exact fixture text, missing file raises `FileNotFoundError`.
- **Failure mode discovered:** feeding a non-PDF file (plain text saved as `.pdf`) raises `pypdf.errors.PdfStreamError: Stream has ended unexpectedly` — a third distinct failure signature alongside Unit 1's `ValidationError` and Unit 2's `NotFoundError`/`AuthenticationError`. Relevant later: the upload endpoint will need to catch this and turn it into a clean validation error, not a bare 500 (per the project's "no bare generic exceptions for expected application failures" convention).
- **Resume claim earned:** none yet — extracting text from a fixture isn't "built a document ingestion pipeline." That's earned once upload + extraction + chunking + storage work together.

---

## Unit 4 — Fixed-size chunker with overlap

- **Concept touched:** chunking and overlap.
- **Files changed:** `services/chunker.py` (new), `tests/test_chunker.py` (new).
- **Design decision:** character-based sliding window (`chunk_size=500`, `overlap=50` defaults), not token- or sentence-aware. Rejected `nltk`/`spaCy` sentence-boundary chunking for this unit — it hides the naive fixed-size mechanism (and its failure modes) behind a "smarter" abstraction before those failure modes have actually been seen. `overlap >= chunk_size` raises `ValueError` rather than silently producing an infinite loop or empty chunks.
- **Test/command run:** `.venv/bin/python -m pytest -v`
- **Observed behavior:** 10/10 tests passed; a manual demo showed a planted phrase ("thirty days written notice") straddling a chunk boundary was split and unrecoverable in any single chunk with `overlap=1`, but intact in one chunk with `overlap=30` — same underlying text, only the overlap parameter changed.
- **Failure mode discovered:** none new beyond the already-guarded `overlap >= chunk_size` case; the more interesting "failure" was the intentional boundary-split demo above, which motivates overlap existing at all.
- **Resume claim earned:** none yet — chunking in isolation isn't a resume claim; it becomes one once chunks flow into embeddings + storage + retrieval.

---

## Unit 5 — Ingest pipeline (extraction + chunking composed)

- **Concept touched:** none new — pure composition of Units 3 and 4. Worth logging as its own unit because it's the first point Phase 2's actual code-track deliverable ("PDF ingest") is observed working, not just its parts in isolation.
- **Files changed:** `services/ingest.py` (new), `tests/test_ingest.py` (new).
- **Design decision:** kept as a plain function, deliberately not wired to a FastAPI upload endpoint — no router/app layer exists anywhere in the repo yet, and standing one up now would mean scaffolding an architectural layer (app entrypoint, routers/, multipart handling, error-class wrapping) ahead of when Phase 4 (naive RAG end-to-end) actually needs it.
- **Test/command run:** `.venv/bin/python -m pytest -v`
- **Observed behavior:** 12/12 tests passed; manual run on the real fixture (`chunk_size=40, overlap=10`) produced 3 chunks, with a phrase spanning the chunk 0/1 boundary surviving intact due to overlap.
- **Failure mode discovered:** confirmed (didn't discover new) — `pypdf.errors.PdfStreamError` from a corrupted/non-PDF file propagates unchanged through the composed pipeline. Flagged as future work: needs to become a custom error class once an HTTP boundary exists to catch it, per the project's "no bare generic exceptions for expected application failures" convention.
- **Resume claim earned:** **"Built a PDF ingestion pipeline that extracts and chunks document text with overlap-preserving boundaries."** Earned now because the full path (real PDF file → extracted text → overlapping chunks) has actually run and been observed, not just its individual pieces.

**Phase 2 complete.** Code track (PDF ingest, chunker) fully built and observed end-to-end; concept track (chunking strategy and trade-offs) written in `Interview_prep.md` §3.

---

## Unit 6 — Embedder (sentence-transformers, no database yet)

- **Concept touched:** embeddings and cosine similarity — first time these are computed in real, running code rather than discussed in `Interview_prep.md` §1–2.
- **Files changed:** `services/embedder.py` (new), `tests/test_embedder.py` (new), `requirements.txt` (added `sentence-transformers>=3.0`, which pulled in `torch`).
- **Design decision:** embeddings are L2-normalized at encode time (`normalize_embeddings=True`) so cosine similarity reduces to a plain dot product — matches how pgvector will be used in the next unit. Deliberately not wired to any database yet: verifying the model behaves correctly in isolation means a wrong-looking score can only be the model's fault, not the storage/query layer's, in the next unit.
- **Test/command run:** `.venv/bin/python -m pytest -v`
- **Observed behavior:** 14/14 tests passed. First run took ~75s (one-time model weight download); subsequent runs are fast. Real cosine scores: cat-sentence pair 0.612, unrelated pair 0.075.
- **Failure mode discovered:** the negation gotcha predicted in `Interview_prep.md` §1 confirmed with real numbers — "The drug is approved for adult use" vs. "The drug is NOT approved for adult use" scored **0.888**, higher than the genuinely similar cat-sentence pair. Embedding similarity alone cannot distinguish agreement from contradiction; this is exactly why Phase 9 exists.
- **Resume claim earned:** none new yet — embedding in isolation isn't "semantic search." That's earned once pgvector storage and top-k SQL retrieval exist and return correct real results.

---

## Unit 7 — Postgres + pgvector schema (Docker Compose, Alembic)

- **Concept touched:** vector databases / schema design for embeddings — first time a `vector(N)` column exists anywhere in the project. No search yet, so exact-vs-HNSW isn't touched by this unit.
- **Files changed:** `docker-compose.yml` (new), `core/db.py` (new), `core/models.py` (new), `core/config.py` (added `database_url`), `.env.example`/`.env` (added `DATABASE_URL`), `alembic.ini` + `alembic/env.py` + `alembic/versions/398fbec4f808_create_chunks_table.py` (new), `requirements.txt` (added `sqlalchemy`, `alembic`, `asyncpg`, `pgvector`).
- **Design decision:** `pgvector/pgvector:pg18` image (extension precompiled) over a plain `postgres` image plus manual `CREATE EXTENSION`. Async SQLAlchemy engine/session + Alembic's async template, matching the project's async-first stack. Migration hand-written rather than autogenerated — `CREATE EXTENSION` isn't something Alembic's autogenerate detects, and autogenerate would need a live DB connection for a migration this simple anyway. `chunks` schema kept minimal (`id`, `content`, `source`, `embedding`) — no document/upload table yet, since no upload endpoint exists.
- **Test/command run:** `docker compose up -d postgres`; `.venv/bin/alembic upgrade head`; verified with `docker compose exec postgres psql -U docmind -d docmind -c "\d chunks"` and `"\dx"`; full pytest suite re-run (14/14) to confirm the config change didn't regress anything.
- **Observed behavior:** `\d chunks` showed all 4 columns with correct types (`embedding` as `vector(384)`, not null); `\dx` showed the `vector` extension enabled at v0.8.6.
- **Failure modes discovered:** (1) Postgres 18's Docker image requires the data volume mounted at `/var/lib/postgresql`, not the previously-standard `/var/lib/postgresql/data` — container exited immediately with a clear message on the first attempt; fixed by changing the mount path. A genuine infra surprise, not a code bug. (2) Confirmed pgvector enforces column dimensionality at the DB level: inserting a 3-element vector into the `vector(384)` column raised `asyncpg.exceptions.DataError: expected 384 dimensions, not 3`, and the table was confirmed still empty afterward (transactional integrity held — no partial row).
- **Resume claim earned:** none yet — a schema with a vector column isn't "vector search." That's earned once real embedded chunks are stored and a top-k query returns correct results.

---

## Unit 8 — Exact top-k cosine similarity search

- **Concept touched:** exact nearest-neighbor search / top-k retrieval.
- **Files changed:** `services/vector_store.py` (new), `tests/test_vector_store.py` (new), `core/db.py` (engine switched to `poolclass=NullPool`).
- **Design decision:** pgvector's `.cosine_distance()` SQLAlchemy comparator instead of raw `<=>` SQL — same operator under the hood, but type-checked. No index on `embedding` — deliberate, matches `CLAUDE.md`'s explicit ordering (exact search understood and observed before HNSW).
- **Test/command run:** `.venv/bin/python -m pytest -v`
- **Observed behavior:** 16/16 tests passed. Manual query for "What is the refund policy?" against 3 seeded chunks returned the refund-policy chunk first at cosine distance 0.3277 (vs. 0.8200 and 0.9880 for the other two) — correct ranking, real numbers, not just a passing assertion.
- **Failure mode discovered:** async engine connection pooling doesn't survive across separate `asyncio.run()` calls — a pooled `asyncpg` connection created under one event loop raised `InterfaceError: cannot perform operation: another operation is in progress` when reused under a new loop spun up by a later `asyncio.run()`. Fixed with `poolclass=NullPool`, mirroring the fix Alembic's own async template already uses. Second, deliberate break-it experiment: re-running the query with `ORDER BY ... DESC` instead of `ASC` produced no error at all — just a silently, completely inverted ranking (least relevant chunk first). This is the single most dangerous failure mode in this unit: it fails quiet, not loud.
- **Resume claim earned:** **"Built semantic search over documents using sentence-transformer embeddings and PostgreSQL/pgvector, with exact cosine-similarity top-k retrieval."** First time the full path — embed, store, query, correct ranking — has been observed working together end-to-end on real data.

---

## Unit 9 — HNSW index + exact-vs-approximate comparison

- **Concept touched:** vector indexes — HNSW vs. exact search.
- **Files changed:** `alembic/versions/4b925de70d4b_add_hnsw_index_on_chunks_embedding.py` (new).
- **Design decision:** `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)` — `vector_cosine_ops` chosen to match the cosine-distance operator already used in `services/vector_store.py`; an index built with the wrong distance operator class silently can't be used by a query using a different one. Synthetic scale-up data (3000 random unit vectors) generated in pure Python and deleted immediately after the comparison — not committed as a fixture.
- **Test/command run:** `.venv/bin/alembic upgrade head`; `EXPLAIN ANALYZE` via a manual script at 3 rows and again at 3003 rows; `.venv/bin/python -m pytest -v` after cleanup.
- **Observed behavior:** at 3 rows: `Seq Scan on chunks`, 0.054ms — planner correctly judged the index not worth using at this size. At 3003 rows: `Index Scan using chunks_embedding_hnsw_idx` — the planner switched over on its own, no query changed. The real relevant chunk ("refund policy...") was still returned correctly ranked first even via the approximate index, among 3000 unrelated random vectors. Full suite 16/16 after cleanup.
- **Failure mode discovered:** none new — this unit's value was in observing correct, expected behavior (planner cost-based index selection) rather than uncovering a bug.
- **Resume claim earned:** extends the Unit 8 claim — can now say the semantic search understanding includes *when* an index gets used, not just that pgvector supports one: **"...and can explain the exact-vs-approximate-index trade-off with an observed query-plan comparison, not just in theory."**

**Phase 3 complete.** Code track (pgvector schema, top-k search) and concept track (vector indexes, HNSW vs exact) both built and observed with real evidence.

---

## Unit 10 — Naive RAG end-to-end (batched: synthesis + FastAPI app)

- **Concept touched:** prompt construction, grounding, citations. Batched implementation at developer's request — process granularity relaxed (fewer approval checkpoints), rigor kept (tests, concept explanation, real HTTP validation).
- **Files changed:** `services/rag.py` (new), `services/llm_client.py` (added `system` param), `core/errors.py` (new: `DocMindError`, `InvalidPDFError`), `services/pdf_extractor.py` (wraps `PdfReadError`), `main.py` (new FastAPI app), `schemas/query.py` + `schemas/document.py` (new), `routers/documents.py` + `routers/query.py` (new), `core/db.py` (added `get_session`), `tests/fixtures/sample.pdf` (regenerated with real bio content), `tests/test_pdf_extractor.py` + `tests/test_ingest.py` (updated assertions, added `InvalidPDFError` test), `requirements.txt` (added `fastapi`, `uvicorn[standard]`, `python-multipart`, `httpx`).
- **Design decision:** citations are prompt-instructed, not structurally verified — a known, stated limitation, not an oversight. `generate()` now takes messages as proper system/user roles instead of one concatenated string, matching how chat models are actually meant to be prompted.
- **Test/command run:** `.venv/bin/python -m pytest -v` (17/17); real server run via `uvicorn main:app --port 8001` with `curl` against all three endpoints.
- **Observed behavior:** end-to-end HTTP round trip worked — upload → `chunks_stored: 1`; query *"What is the name of this person?"* → `"The person's name is Aria Kapoor. [1]"` with correct source attached; out-of-context query *"What is the capital of France?"* → `"I don't know."` (grounding held); corrupted upload → clean `400`, no leaked stack trace.
- **Failure mode discovered:** port 8000 was already occupied by an unrelated, pre-existing DeliverIQ Docker container on this machine. The first `uvicorn` run failed to bind and exited immediately, but a `curl` against port 8000 still returned `200 {"status":"ok"}` — from DeliverIQ's own health check, not ours — because the port was serving a different app entirely. A passing-looking curl response is not proof your own server is the one answering; checking the actual server log caught it. Fixed by using port 8001.
- **Resume claim earned:** **"Built a naive RAG system end-to-end over FastAPI: PDF upload, chunking, embedding, pgvector retrieval, and LLM-generated answers with source citations, with verified grounding behavior."** First time the whole system has been exercised as a real running service rather than only through unit tests and Python REPL calls.

**Phase 4 code complete.** Concept notes (prompting, grounding, citations) next.

---

## Unit 11 — Citation filtering, document scoping, source B-tree index

- **Concept touched:** grounding/citation reliability (continued from Unit 10) plus a new, real one: retrieval without document scoping means multiple uploaded documents silently compete for the same top-k slots.
- **Files changed:** `services/rag.py` (citation filtering + tightened `SYSTEM_PROMPT`), `services/vector_store.py` + `schemas/query.py` + `routers/query.py` (optional `source` scoping param threaded through), `alembic/versions/3002213eec16_add_btree_index_on_chunks_source.py` (new).
- **Design decision:** citation filtering falls back to *all* retrieved sources if regex parsing finds zero `[n]` matches, rather than returning empty evidence — chosen because citation format is LLM-generated and best-effort, not guaranteed (proven live: the model used full-width brackets `〔2〕` on one run, silently breaking a stricter parser). B-tree added on `source` since equality filtering is exactly what B-trees are for — the standard, default Postgres index type for `WHERE column = value`, unrelated to HNSW/vector indexing.
- **Test/command run:** `.venv/bin/python -m pytest -v` (17/17); manual HTTP tests with two distinct real documents uploaded, queried scoped and unscoped.
- **Observed behavior:** scoped queries correctly isolated each document's answer; the unscoped query against both documents together returned `"I don't know"` for an ambiguous cross-document question — grounding correctly refused to guess between two different people's names rather than silently picking one.
- **Failure modes discovered:** (1) the exact bug that motivated this unit — a leftover chunk from earlier testing contaminated a real query, discovered by the developer through actual use, not a planned test. (2) A second, unrelated one found while verifying the fix: `test_vector_store.py` wipes and reseeds the `chunks` table on every `pytest` run, and shares the same database as manual dev testing — running the test suite silently destroyed uploaded demo documents mid-session. Documented as a known open issue (needs a separate test DB), not fixed in this unit.
- **Resume claim earned:** extends Unit 10 — retrieval is now document-scoped and citations reflect only what was actually used in the answer, both found and fixed through real usage rather than synthetic testing.

---

## Unit 12 — Auto-append `.pdf` to `source` in query requests

- **Concept touched:** none new — API ergonomics fix on top of Unit 11's exact-match filtering.
- **Files changed:** `schemas/query.py` (added a `field_validator` on `source`), `tests/test_query_schema.py` (new).
- **Design decision:** normalization at the Pydantic schema layer, so every downstream function (`answer_question`, `search`) still only ever sees a fully-qualified source string — the convenience is a request-parsing concern, not a retrieval concern.
- **Test/command run:** `.venv/bin/python -m pytest tests/test_query_schema.py -v` (3/3, scoped deliberately to avoid the known DB-wiping collision from Unit 11); confirmed live with `curl` using `source: "sample"`.
- **Observed behavior:** `source: "sample"` now correctly resolves to `sample.pdf` and returns Maya Chen's answer, matching what previously required the full filename.
- **Failure mode discovered:** none new — this fixes UX friction from an already-known, already-documented gotcha (Unit 11), doesn't change its underlying exact-match nature (a genuine typo still silently matches nothing).
- **Resume claim earned:** none new — polish, not new capability.
