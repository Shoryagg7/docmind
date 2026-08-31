# DocMind

Agentic RAG over PDFs — retrieval, self-grading, bounded retry, and a semantic query cache, built one observable unit at a time with every design decision measured rather than assumed.

Ask a question about an uploaded PDF and DocMind retrieves candidate chunks from pgvector, **grades each one for relevance with an LLM**, rewrites the query and retries if nothing useful came back (bounded to 2 attempts), then generates a grounded answer with citations — streaming each pipeline stage and each answer token to the browser as it happens.

---

## What makes this more than a RAG tutorial

Every claim below was measured on this codebase, not asserted:

| Finding | Number |
|---|---|
| Relevance grading's share of per-query token cost | **70%** (857 of 1221 tokens) |
| Cache hit vs. cold query latency | **0.01s vs 9.62s** |
| Golden-set accuracy (25 questions, LLM-as-judge) | **25/25** |
| Chunk size 500→150 effect on accuracy | **25/25 → 18/25** |
| Statement vs. its own negation similarity | **0.87** (vs 0.47 for genuinely different text) |
| A single trailing `?`, in similarity terms | **0.065** — nearly the entire safe threshold window |

Two of those are load-bearing:

**Negation defeats similarity thresholds by construction.** A negated question scores **0.9879** against its positive form, while the paraphrase the cache exists to serve scores **0.9399**. The case that must be *rejected* scores higher than the case that must be *accepted*, so no threshold separates them. The mitigation is a lexical negation guard — deliberately a signal from outside the embedding — and its own residual failure mode ("barred from", 0.9273, no marker) is documented rather than hidden.

**A cache hit bypasses every safety mechanism.** Grounding (Phase 4) and relevance grading (Phase 6) both sit *behind* the cache, so the similarity threshold is a correctness parameter, not a performance knob. At 0.85 the system confidently answers "Toronto" to "what city was Maya Chen **born** in?" — instantly, with a citation.

---

## Architecture

```
              ┌──────────── DocMind API (container) ─────────────┐
 Client ─────>│  POST /query/stream                              │
              │        │                                         │
              │        v         LangGraph                       │
              │   ┌─ retrieve ──> grade ──> ⟨relevant? retries?⟩ │
              │   │                │              │              │
              │   └── rewrite <────┘              v              │
              │      (max 2)                  generate           │
              └──────┬──────────────────────────┬────────────────┘
                     │                          │
              ┌──────v───────┐          ┌───────v────────┐
              │  Postgres    │          │  Groq API      │
              │  + pgvector  │          │  (external)    │
              │  HNSW/B-tree │          │  gpt-oss-120b  │
              └──────────────┘          └────────────────┘
                     ▲
              ┌──────┴───────┐
              │ Redis Stack  │  semantic cache — RediSearch KNN
              │ (cache only) │  + similarity threshold + negation guard
              └──────────────┘
```

**Ingestion:** `POST /documents` → pypdf extraction → 500-char chunks with 50 overlap → `all-MiniLM-L6-v2` embeddings (384-dim, in-process on CPU) → `chunks` table with an HNSW index on `embedding` and a B-tree on `source`.

**Retrieval:** semantic cache lookup → LangGraph (`retrieve → grade → conditional → rewrite | generate`) → grounded answer with `[n]` citations filtered to only the chunks actually cited.

---

## Quick start

```bash
# 1. services
docker compose up -d postgres redis

# 2. environment
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env        # then add your GROQ_API_KEY

# 3. schema
.venv/bin/alembic upgrade head

# 4. run
.venv/bin/uvicorn main:app --port 8001
```

Open **http://localhost:8001/** — upload a PDF and ask questions. The page must be served by the app; opening `static/index.html` from disk cannot reach the API.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/documents` | Upload a PDF (extract → chunk → embed → store) |
| `GET` | `/documents` | List ingested documents and chunk counts |
| `POST` | `/query` | Ask a question, JSON response |
| `POST` | `/query/stream` | Ask a question, SSE stream of stages + tokens |
| `GET` | `/health` | Liveness |

---

## Evaluation

```bash
.venv/bin/python -m eval.run_eval        # 25-question golden set, LLM-as-judge
.venv/bin/python -m eval.run_negation    # negation failure measurement (no LLM calls)
.venv/bin/python -m pytest               # unit tests
```

The golden set covers 22 answerable questions across two documents plus 3 deliberately unanswerable ones (out-of-scope topic, wrong-document scoping, topic absent from both) — because a RAG system that can't say "I don't know" isn't grounded, it's lucky.

Scoring is **LLM-as-judge**, not string matching, since correct answers vary in phrasing. Two caveats worth knowing: the judge is itself an LLM and can be wrong, and eval runs are **not deterministic** (grading and generation use non-zero temperature), so only differences larger than run-to-run noise are meaningful.

`eval/run_eval.py` deliberately calls the **uncached** graph. Routing evaluation through the cache would make every run after the first replay cached answers — reporting a perfect score while testing nothing.

---

## Stack

Python 3.14 · FastAPI · SQLAlchemy 2.0 (async) + Alembic · PostgreSQL 18 + pgvector · Redis Stack (RediSearch) · LangGraph 1.2.11 (pinned) · Groq `openai/gpt-oss-120b` · sentence-transformers `all-MiniLM-L6-v2` · Docker Compose · pytest

---

## Layout

```
core/       config, db engine, models, errors, redis client, token accounting
services/   pdf_extractor, chunker, ingest, embedder, vector_store,
            llm_client, grader, graph (LangGraph), semantic_cache, rag
routers/    documents, query, stream
schemas/    request/response models
eval/       golden set + LLM-as-judge harness, negation set
static/     single-page UI
alembic/    migrations (vector extension, HNSW index, B-tree index)
```

`services/rag.py` holds the pre-LangGraph straight-line implementation. It's kept deliberately as the "before" reference — no route calls it.

---

## Known limitations

Stated explicitly, because a portfolio project that claims no weaknesses isn't being honest about engineering.

- **Semantic negation defeats the cache guard.** Lexically marked negation ("not", "aren't") is caught; vocabulary-level negation ("barred from", 0.9273) is not. A real fix needs a cross-encoder or an LLM verification step on hits — which costs the latency the cache exists to save.
- **Cache errors are swallowed silently.** Redis being down degrades to a cache miss (correct — a cache must never take down the API), but nothing logs or alerts, so a permanently dead Redis is invisible and looks identical to an empty cache.
- **Tests share the dev database.** `tests/test_vector_store.py` truncates and reseeds `chunks`; running the full suite destroys uploaded documents. Needs a separate test database.
- **Citations are prompt-instructed, not verified.** Nothing checks that a cited chunk actually supports the claim attached to it. The model has also been observed emitting full-width `【1】` brackets, which a fallback absorbs.
- **Single-user, no auth.** Out of scope by design.
- **Free-tier quota is the practical ceiling.** ~163 queries or ~5 full eval runs per day at measured token cost.

---

## Documentation

- **[`PLAN.md`](PLAN.md)** — per-unit implementation record: what, why, command, observed result
- **[`BUILD_LOG.md`](BUILD_LOG.md)** — per-unit design decisions, failure modes discovered, claims earned
- **[`Interview_prep.md`](Interview_prep.md)** — 12 concept sections (embeddings → cosine similarity → chunking → HNSW → top-k → grounding → graphs/reducers → self-correction → eval → caching → negation → streaming/cost), each with the decision, the trade-off, the gotcha, and self-test questions
