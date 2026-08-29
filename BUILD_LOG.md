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
