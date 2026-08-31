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

---

## Unit 13 — 2-node LangGraph graph (retrieve → generate)

- **Concept touched:** chains vs. graphs, state, reducers.
- **Files changed:** `services/graph.py` (new), `requirements.txt` (added `langgraph==1.2.11`, pinned exactly per `CLAUDE.md`'s explicit rule since LangGraph's API changes frequently).
- **Design decision:** no custom reducers — `retrieve` and `generate` write disjoint state keys, so LangGraph's default overwrite-per-key merge is sufficient for a linear 2-node graph. Not wired into the `/query` route yet; `services/rag.py`'s straight-line `answer_question()` stays the live implementation until Phase 6 gives the graph its actual new behavior (grade + rewrite + bounded retry).
- **Test/command run:** manual side-by-side comparison against `answer_question()` on live data (no DB mutation) — same question, both implementations.
- **Observed behavior:** identical correctness — same answer, same citation, and grounding held the same way through the graph path (out-of-context question → "I don't know", sources fell back to all retrieved chunks per the Unit 11 rule).
- **Failure mode discovered:** none — this unit was about proving the mechanics work, not finding a bug.
- **Resume claim earned:** none new yet — a graph that reproduces the old function's output isn't "agentic" anything. That's earned in Phase 6, once the graph actually grades, retries, and rewrites.

**Phase 5 complete.** Code track (LangGraph rewrite) observed producing identical results to the pre-graph implementation; concept track (chains vs. graphs, state, reducers) written in `Interview_prep.md` §7.

---

## Unit 14 — Relevance grader (standalone, not wired to the graph)

- **Concept touched:** relevance grading / LLM-as-judge.
- **Files changed:** `services/grader.py` (new).
- **Design decision:** one LLM call per chunk, forced to a strict `yes`/`no` reply via a dedicated system prompt (`GRADER_SYSTEM_PROMPT`), parsed by checking the reply starts with "yes". Kept fully standalone — no graph, no conditional edge — so the grading mechanism itself could be verified correct in isolation before wiring it into any control flow. Rejected alternative: threshold on `search()`'s own cosine-distance score instead of a separate LLM call — rejected because a chunk can be embedding-close without actually answering the question (the negation failure mode already documented in `Interview_prep.md` §1 is the sharpest example); LLM-as-judge catches that, a pure distance cutoff can't.
- **Test/command run:** `.venv/bin/python -m services.grader`
- **Observed behavior:** graded a genuinely relevant chunk (Maya Chen's city) as relevant (`True`) and a genuinely irrelevant chunk (Nimbus Cloud Storage pricing) as irrelevant (`False`) — correct in both directions on real content.
- **Failure mode discovered:** none new — this unit was about proving the grading signal is trustworthy before building anything on top of it.
- **Resume claim earned:** none yet — a grading function that isn't wired into anything doesn't earn "self-correcting retrieval." That lands once it's part of the actual retry loop.

---

## Unit 15 — Graph rewired: grade + rewrite nodes, conditional edge, bounded retry

- **Concept touched:** self-correction / bounded retries via reducers.
- **Files changed:** `services/graph.py` (added `grade_node`, `rewrite_node`, `should_retry` conditional function, `MAX_RETRIES = 2`, `retry_count: Annotated[int, operator.add]` in `RAGState`; rewired edges to `retrieve → grade → (conditional: rewrite | generate)`, `rewrite → retrieve`).
- **Design decision:** `retry_count` uses a custom reducer (`operator.add`) so `rewrite_node` can return a delta (`{"retry_count": 1}`) each time it fires, rather than needing to read and recompute the running total itself — the concrete case the reducer concept (introduced in Unit 13/§7) was flagged for but hadn't yet been exercised. `should_retry` checks both `relevant_chunks` being empty *and* `retry_count < MAX_RETRIES`, so the bound is enforced by application logic, not by any framework-level step limit.
- **Test/command run:** (1) normal-path re-run of the Maya Chen query through `answer_question_graph` — no regression. (2) A forced-failure script using `graph.astream()` to trace node-by-node execution, asking a question the scoped document genuinely cannot answer.
- **Observed behavior:** normal path unchanged (`"Maya Chen works in Toronto. [1]"`). Forced-failure trace: `grade` found 0 relevant chunks → `rewrite` produced a rephrased query → `grade` found 0 again → `rewrite` fired a second time → `grade` found 0 a third time → routed to `generate`, which returned `"I don't know — no relevant documents found."` instead of looping a third time. `retry_count` correctly accumulated 0 → 1 → 2 across the two rewrite passes.
- **Failure mode discovered:** none new — the loop terminated exactly as designed on the first real test; no infinite-loop or reducer-not-applied bug was hit, but the test was specifically designed to be capable of exposing one (an unbounded or non-accumulating counter would have looped a third time or errored on LangGraph's internal recursion limit instead of stopping cleanly at `MAX_RETRIES`).
- **Resume claim earned:** none new yet — the graph now has the mechanics of self-correction, but it isn't serving live traffic yet (`/query` still calls the old `answer_question`). That's Unit 16.

---

## Unit 16 — Wired the graph into `/query`

- **Concept touched:** none new — this is the point the previous two units' work becomes real, not additional GenAI concept.
- **Files changed:** `routers/query.py` (swapped `services.rag.answer_question` for `services.graph.answer_question_graph`).
- **Design decision:** `services/rag.py`'s `answer_question()` is left in place, unused by any route — kept as the "before" reference implementation (and what `Interview_prep.md` §6/§7 and the retrieval-pipeline diagram compare against), not deleted.
- **Test/command run:** started the real server (`.venv/bin/uvicorn main:app --port 8001`), `curl -X POST http://localhost:8001/query` with a real question against `sample.pdf`.
- **Observed behavior:** `{"answer": "Maya Chen works in Toronto. [1]", "sources": [...]}` — identical, correct grounded answer with citation, now actually served by the graph (retrieve → grade → generate on this query, since grading passed first try).
- **Failure mode discovered:** none — this unit was wiring, not new logic; the failure modes worth knowing (empty-grade loop behavior, reducer accumulation) were already exercised and confirmed in Unit 15.
- **Resume claim earned:** **"Built an agentic RAG pipeline in LangGraph with self-correcting retrieval — a relevance-grading node and bounded query-rewrite retries — serving live queries end-to-end."** Earned now, not before — this is the point the graph stopped being a side experiment and became the actual code path answering real HTTP requests.

**Phase 6 complete.** Code track (relevance grader, query rewrite, conditional edge, bounded retry) built, wired into `/query`, and observed both on the happy path and under a forced failure that exercises the full retry-then-give-up behavior. Concept track (self-correction, bounded loops) written in `Interview_prep.md` §8; §7 updated to reflect the graph's final shape.

---

## Unit 17 — Eval harness on a 3-question golden set (LLM-as-judge)

- **Concept touched:** eval methodology / LLM-as-judge.
- **Files changed:** `eval/golden_set.py` (new), `eval/judge.py` (new), `eval/run_eval.py` (new).
- **Design decision:** judge is a separate LLM call (`llm_as_judge(question, reference_answer, actual_answer)`) forced to a strict `correct`/`incorrect` reply, not a string-similarity metric — chosen because DocMind's answers are full sentences that vary in phrasing even when correct. Built on 3 questions, not the full 25, to prove the judging mechanism works before scaling data volume.
- **Test/command run:** `docker compose up -d postgres` (container had stopped since the last session); `.venv/bin/python -m eval.run_eval`.
- **Observed behavior:** first run scored 2/3 — a real, unplanned failure. Investigation (`docker compose exec postgres psql ... SELECT content FROM chunks WHERE source='sample2.pdf'`) showed the golden set's own reference answer was wrong: it asked about a "free tier / 5GB" that doesn't exist anywhere in `sample2.pdf` (actual pricing is Starter/Pro/Enterprise, no free tier). The system had correctly answered "I don't know" — grounding held — but the eval flagged it as a failure because the *golden set* was fabricated, not grounded in the real document. Fixed by replacing the question with one actually answerable from the real text ("How many gigabytes does the Starter tier include?" → "50 gigabytes"). Re-run: 3/3 passed.
- **Failure mode discovered:** a golden set's own reference answers can be silently wrong if not verified against the actual source documents — an eval that "fails" doesn't always mean the system is wrong; it can mean the eval itself is wrong. This is a real, general eval-methodology gotcha, not specific to this project, and it was caught by inspecting the raw DB content before trusting the eval's verdict.
- **Resume claim earned:** none yet — 3 questions isn't the "25-question golden set" scope item. That's earned once scaled up and results are analyzed in aggregate.

---

## Unit 18 — Scaled golden set to 25 questions

- **Concept touched:** eval methodology (continued) — question design across answerable and deliberately-unanswerable cases.
- **Files changed:** `eval/golden_set.py` (grown from 3 to 25 entries: 12 questions against `sample.pdf`, 10 against `sample2.pdf`, 3 deliberately unanswerable — one out-of-scope topic, one cross-document scoping case, one topic absent from both documents).
- **Design decision:** every reference answer was written by reading the real chunk content out of Postgres first (`docker compose exec postgres psql ... SELECT content FROM chunks WHERE source=...`), not from memory or assumption — directly because Unit 17 caught a fabricated reference answer ("free tier / 5GB") that doesn't exist anywhere in `sample2.pdf`. The 3 unanswerable cases were chosen to cover three different reasons an answer can legitimately not exist: topic genuinely absent from the scoped document, a question scoped to the wrong document entirely, and a topic absent from both uploaded documents with no scoping at all.
- **Test/command run:** `docker compose up -d postgres` (container had stopped between sessions, data confirmed intact via `SELECT source, COUNT(*) FROM chunks GROUP BY source` before running); `.venv/bin/python -m eval.run_eval`.
- **Observed behavior:** 25/25 passed. All 22 answerable questions returned correct, grounded, cited answers; all 3 unanswerable questions correctly returned "I don't know" rather than guessing.
- **Failure mode discovered:** the citation-format gotcha from Unit 11 recurred live during this run — one answer ("Senior Backend Engineer") came back with full-width brackets (`【1】`) instead of ASCII `[1]`. Not a new bug: the existing fallback (`sources = cited-only or all-retrieved`) absorbed it silently, and since the eval judge scores answer *content*, not citation formatting, it didn't affect the pass/fail count. Logged because it's evidence the underlying non-determinism is still real and unfixed, just successfully contained by an existing safeguard.
- **Resume claim earned:** **"Built a 25-question golden evaluation set with an LLM-as-judge scoring harness, covering both correctly-answerable and deliberately-unanswerable queries, and used it to verify grounding held across the full agentic RAG pipeline."** Earned now — the eval ran against the live graph-based `/query` implementation (via `answer_question_graph`), not a mock, and scored both directions of correctness (right answers accepted, refusals accepted where warranted).

**Phase 7 complete.** Code track (25-question golden set, LLM-as-judge harness) built and observed at 25/25. Concept track (eval methodology, LLM-as-judge) written in `Interview_prep.md` §9.

---

## Unit 19 — Redis Stack service + connectivity (no caching logic yet)

- **Concept touched:** none new yet — this is the plumbing unit that precedes semantic caching, same pattern as "pgvector schema before search" (Unit 7) and "2-node graph before retry logic" (Unit 13).
- **Files changed:** `docker-compose.yml` (added `redis` service), `core/config.py` (added `redis_url`), `core/redis_client.py` (new), `requirements.txt` (added `redis>=5.0`).
- **Design decision:** `redis/redis-stack-server` rather than plain `redis` — Redis Stack bundles the RediSearch module, which provides the vector-similarity index the semantic cache will need in the next unit; plain Redis can only do exact-key lookup, which is precisely the approach being rejected. Deliberately **no volume mounted**: a cache is not a source of truth, and losing it on restart is correct behavior, not data loss. `get_redis_client()` mirrors `core/db.py`'s role for Postgres — client construction lives in `core/`, and no service code constructs its own connection.
- **Test/command run:** `docker compose up -d redis`; `docker compose exec -T redis redis-cli ping` → `PONG`; `.venv/bin/python -m core.redis_client`.
- **Observed behavior:** `Redis says: alive` — a real SET then GET round trip through the app's own async client, not just a container health check.
- **Failure mode discovered:** with Redis stopped (`docker compose stop redis`), the client raises `redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379`. This directly shapes the next unit's design: a cache being unavailable must **not** take the whole `/query` path down. The semantic cache has to treat a Redis failure as a cache miss and fall through to the normal graph, rather than letting the exception propagate — a cache that can break the app is worse than no cache.
- **Resume claim earned:** none yet — a reachable Redis container isn't "semantic caching." That's earned once a paraphrased question actually hits the cache and skips the LLM calls.

---

## Unit 20 — Exact-match cache (deliberately the naive version)

- **Concept touched:** cache key design — a cache is only as useful as its key.
- **Files changed:** `services/cache.py` (new: `get_cached_answer()`, `set_cached_answer()`, 1-hour TTL).
- **Design decision:** built the *exact-key* cache first, on purpose, knowing it's the version being rejected — same pedagogy as exact vector search before HNSW (Units 8/9). Seeing the paraphrase miss firsthand is what makes the semantic cache's added complexity justified rather than assumed. Two further decisions: (1) cache keys include `source`, so a cached answer for one document can never be served for a query scoped to a different one; (2) a fresh Redis client per call rather than an `lru_cache`d singleton — deliberately avoiding the cross-event-loop reuse bug already hit with SQLAlchemy pooling in Unit 8, at the cost of per-call connection overhead. Worth revisiting once the cache is wired into the long-lived FastAPI event loop.
- **Test/command run:** a throwaway script caching one question, then looking up (a) the identical string, (b) a paraphrase, (c) the same string scoped to a different document. Then the whole thing re-run with `docker compose stop redis`.
- **Observed behavior:** identical string → **HIT**. Paraphrase *"Which city is Maya Chen based in?"* → **MISS**, despite being the same question semantically. Different document scope → **MISS** (correct). With Redis stopped: every lookup → **MISS**, no exception raised.
- **Failure mode discovered:** the paraphrase miss *is* the finding, and it's the entire justification for Phase 8 — an exact-key cache isn't merely less useful, it's actively negative-value in real traffic: you pay a Redis round trip on every single request to hit approximately never, since real users don't retype character-identical questions. Separately, the Redis-down run confirms the safety property demanded by Unit 19: `RedisError` is swallowed and treated as a miss in both directions (a failed *write* must not fail the request either), so a cache outage degrades `/query` to its normal uncached path instead of taking it down.
- **Resume claim earned:** none — this is the strawman. The claim arrives when the paraphrase above returns a HIT.

---

## Unit 21 — Semantic cache (RediSearch vector index + similarity threshold)

- **Concept touched:** semantic caching, similarity thresholds.
- **Files changed:** `services/semantic_cache.py` (new).
- **Design decision — threshold picked from measurement, not intuition.** Before writing the lookup, measured pairwise cosine similarity across fixture questions: true paraphrase (*"work in?"* vs *"based in?"*) = **0.9399**; the dangerous near-miss (*"work in?"* vs *"**born** in?"*, different correct answers — Toronto vs Vancouver) = **0.8718**; unrelated-but-same-person (*"what university?"*) = **0.8011**; genuinely unrelated (*"Starter tier cost?"*) = **0.0377**. The usable window is only **0.068 wide**. Chose `0.92` — inside the gap but deliberately biased toward the strict end, because the costs are asymmetric: a miss just means doing the normal work, while a false hit means confidently serving a wrong answer.
- **Other decisions:** `FLAT` (exact brute-force) vector index rather than HNSW — same reasoning as Units 8/9, a cache holding hundreds of entries doesn't need ANN, and exact search removes approximation as a variable while the threshold is being tuned. `source` stored as a RediSearch `TAG` and filtered in the *same* query as the KNN search — structurally identical to the B-tree + HNSW combination in Unit 11, just in Redis. Key prefix `docmind:semcache:` deliberately distinct from Unit 20's `docmind:cache:` so the two caches can coexist without the index picking up the old keys.
- **Test/command run:** a throwaway script caching one question then looking up 5 variants plus a wrong-document scope; then a threshold sweep at `0.92` vs `0.85`.
- **Observed behavior:** all six cases correct — identical → HIT, **paraphrase → HIT** (the exact-match cache from Unit 20 missed this), born-in → MISS, different question → MISS, unrelated → MISS, other document → MISS.
- **Failure mode discovered:** the threshold sweep made the danger concrete rather than theoretical. At `0.85`, asking *"What city was Maya Chen **born** in?"* returns the cached **"Maya Chen works in Toronto"** — a confidently wrong answer, served instantly, with a citation attached, and **no LLM call in the loop to catch it**. This is strictly worse than having no cache: the grounding work from Phase 4 and the relevance grading from Phase 6 are both bypassed on a cache hit, so the cache is the one component in the pipeline with no safety net behind it. Second, smaller finding: embeddings of questions about the same entity cluster tightly regardless of *which fact* is being asked (0.80 for an entirely different question about the same person), so a threshold below ~0.9 is unsafe for this corpus in general, not just for the born/work pair.
- **Resume claim earned:** **"Implemented a Redis semantic query cache using RediSearch vector similarity with a measured similarity threshold, so paraphrased questions reuse prior answers while near-miss questions with different answers correctly fall through."** Earned — the paraphrase hits, the dangerous near-miss doesn't, and the threshold was chosen from measured data with the failure mode demonstrated.

---

## Unit 22 — Cache-aside wiring into `/query`

- **Concept touched:** cache-aside (lazy-loading) pattern; cache invalidation boundaries for evaluation.
- **Files changed:** `services/graph.py` (added `answer_question_cached()`), `routers/query.py` (route now calls the cached wrapper), `schemas/query.py` (`QueryResponse.cached: bool`).
- **Design decision — the wrapper sits *outside* the graph, not inside it as a node.** The entire value of a cache hit is skipping the graph and all 3+ of its Groq calls; making it an internal node would mean paying graph construction and routing a conditional edge to `END` for no benefit over an `if`. Second decision: **`eval/run_eval.py` deliberately still calls `answer_question_graph()`, not the cached wrapper.** If evaluation ran through the cache, the second eval run onward would replay cached answers and silently stop testing the actual pipeline — the eval would report a perfect score while exercising nothing. Third: the response carries an explicit `cached` boolean, so a hit is observable from the client rather than inferred from latency.
- **Test/command run:** `docker compose exec -T redis redis-cli FLUSHALL` (cold cache), server on port 8001, then four `curl` calls timed with `/usr/bin/time`.
- **Observed behavior:** (1) cold ask → **9.62s**, `cached: false`, "Toronto". (2) identical question → **0.01s**, `cached: true`. (3) **paraphrase never asked before** (*"Which city is Maya Chen based in?"*) → **0.01s**, `cached: true`, correct Toronto answer — the whole point of the phase, working end-to-end over HTTP. (4) near-miss (*"What city was Maya Chen **born** in?"*) → 3.95s, `cached: false`, correctly answered **Vancouver**, not the cached Toronto.
- **Failure mode discovered:** none new in the wiring, but the timing quantifies the earlier warning: a cache hit is ~**960× faster** because it does *nothing* — no retrieval, no grading, no generation. That's the benefit and the risk in one number, and it's why the threshold is a correctness parameter. Also noted: the full-width citation bracket quirk (`【1】`) persists on `openai/gpt-oss-120b` too, so it's a general model behaviour, not specific to `gpt-oss-20b`; the Unit 11 fallback continues to absorb it.
- **Resume claim earned:** extends Unit 21's claim to the live service — **"...wired into the query endpoint as a cache-aside layer, cutting repeat and paraphrased queries from ~9.6s to ~0.01s with zero LLM calls, while preserving correctness on near-miss questions."**

**Phase 8 complete.** Code track (Redis Stack, exact-match strawman, semantic cache, cache-aside wiring) built and observed end-to-end. Concept track (cache semantics, TTL, similarity thresholds) written in `Interview_prep.md` §10.

---

## Unit 23 — Negation test set (embedding, retrieval, and cache impact)

- **Concept touched:** embedding failure modes — negation.
- **Files changed:** `eval/negation_set.py` (new: 6 statement/negation pairs + 3 control pairs), `eval/run_negation.py` (new: measures embedding-level and retrieval-level impact). Zero Groq calls — pure embedding math plus pgvector search, deliberately chosen while the daily quota was constrained.
- **Design decision:** measured against a **control set** rather than reporting negation scores alone. A raw 0.87 means nothing without knowing what "genuinely different" scores; the comparison is what makes the result interpretable. Pairs drawn partly from the real fixture documents (the Enterprise refund clause in `sample2.pdf` is an actual negated fact) so the finding is about this system, not a textbook example.
- **Test/command run:** `.venv/bin/python -m eval.run_negation`, then two targeted cache probes.
- **Observed behavior:**
  - **Embedding level:** statement vs. its own negation averaged **0.8728**; genuinely different statements averaged **0.4692** — a **+0.4036** gap in exactly the wrong direction. Worst case: *"Nimbus is SOC 2 Type II certified"* vs *"...is **not** SOC 2 Type II certified"* = **0.9586**. Opposites score nearly twice as similar as merely-different statements.
  - **Retrieval level:** *"Are Enterprise customers eligible for the 14-day refund window?"* and its negated form retrieved **identical chunks** (same ids, both k=2), at 0.9885 query similarity. This one is survivable — the retrieved chunk contains the negated fact, so the grounded LLM can still answer correctly; retrieval being negation-blind is masked by generation.
  - **Cache level — not survivable.** *"Which tiers **are** eligible for the 14-day refund?"* (answer: Starter and Pro) vs *"Which tiers are **not** eligible?"* (answer: Enterprise) scored **0.9879**. The cache returned a HIT and served the wrong answer instantly, with a citation, no LLM in the path.
- **Failure mode discovered — the important one:** **no similarity threshold can fix this.** The negation pair scores **0.9879**, while the paraphrase the cache exists to catch scores **0.9399**. The thing we must reject scores *higher* than the thing we must accept, so any threshold that admits paraphrases necessarily admits negations. Phase 8's threshold tuning is therefore provably insufficient against negation — the defect is in the embedding space, not the cutoff. This also reframes Unit 21's threshold work honestly: 0.92 protects against *near-miss* questions (born vs. work, 0.8718) and does nothing whatsoever against negation.
- **Resume claim earned:** **"Built a negation test set demonstrating that embedding similarity cannot distinguish a statement from its opposite (0.87 avg vs 0.47 for genuinely different text), and showed this defeats similarity-threshold semantic caching by construction — the negated query scores higher than the paraphrase the cache is designed to accept."** Earned — measured, reproduced end-to-end, and the impossibility argument is demonstrated rather than asserted.

---

## Unit 24 — Lexical negation guard on cache lookups

- **Concept touched:** mitigating an embedding failure mode from *outside* the embedding.
- **Files changed:** `services/semantic_cache.py` (added `has_negation()` and a polarity check after the threshold test).
- **Design decision:** the guard is deliberately **not** similarity-based, because Unit 23 proved similarity cannot work here — the negation (0.9879) outscores the paraphrase (0.9399), so no cutoff separates them. Instead the cached question text is stored and returned by the search, and a hit is rejected when the incoming question and the cached question **disagree on the presence of negation markers**. Cheap (one regex, no extra LLM call, no extra round trip) and orthogonal to the failing signal. Placed *after* the threshold check so it only runs on candidates that already passed similarity.
- **Test/command run:** `redis-cli FLUSHALL`, then the Unit 21 suite re-run as a regression check, plus a negation suite and a deliberate failure-probe suite.
- **Observed behavior:**
  - **Fixed:** *"Which tiers are **not** eligible..."* (0.9879) and *"...**aren't** eligible..."* (0.9896) both now **MISS**. Previously both were HITs serving the wrong answer.
  - **No regression:** all six Unit 21 cases still correct, and a genuine paraphrase *"Which tiers **can get** the 14-day refund?"* (0.9539, no negation on either side) still **HITs**.
- **Failure mode discovered — the guard's own limits, measured in both directions:**
  - **False negative (dangerous):** *"Which tiers are **barred from** the 14-day refund?"* scores **0.9273** — above threshold — and contains **no lexical negation marker**, so the guard passes it through and the wrong answer is still served. Semantic negation expressed through vocabulary ("barred", "denied", "excluded from" phrasings outside the marker list) defeats it entirely.
  - **False positive (safe):** *"Which tiers can get a refund with **no** restrictions?"* contains "no" in a non-negating role, so the guard rejects a hit that would have been legitimate. Costs a cache miss, which is the acceptable direction.
  - Net: this is a **mitigation, not a fix**. It converts the common, lexically-marked case from "silently wrong" to "correctly missed", and leaves vocabulary-level negation unsolved. A real fix needs a model that encodes negation — a cross-encoder or an LLM verification step on cache hits — which costs the latency the cache exists to save.
- **Resume claim earned:** extends Unit 23 — **"...and mitigated it with a lexical negation guard on cache lookups, verified to block negated hits without regressing legitimate paraphrase hits, with the guard's own residual failure mode (semantic negation without lexical markers) measured rather than assumed."**

**Phase 9 complete.** Code track (negation set, threshold analysis, negation guard) built and measured. Concept track (embedding failure modes) written in `Interview_prep.md` §11.
