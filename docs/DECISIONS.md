# Decisions

Each entry: **decision / alternatives / why / cost.** Simplest workable option unless stated.

## Environment

### Stay on Python 3.14
- **Decision:** keep Python 3.14.
- **Alternatives:** move to 3.12 for Presidio/spaCy compatibility.
- **Why:** `presidio-analyzer 2.2.364` and `spacy 3.8.16` install and run on 3.14.4 (verified by running a Presidio analysis on this machine). No reason to move.
- **Cost:** 3.14 is new, so a future dependency may lack wheels for it. Then the fallback is 3.12.

### CPU-only torch index in requirements.txt
- **Decision:** `--extra-index-url https://download.pytorch.org/whl/cpu` at the top of `requirements.txt`.
- **Alternatives:** default PyPI torch; tell users to install torch by hand.
- **Why:** the embedder runs on CPU. Default PyPI torch on Linux also pulls the `nvidia-*` CUDA wheels. `du -sh .venv` measured 6.4 GB with them and 1.8 GB after a clean reinstall with CPU wheels.
- **Cost:** it adds a second package index. On a GPU machine, you'd have to remove the line to get GPU embeddings.

### Exact version pins
- **Decision:** pin every top-level dependency to the exact version verified tonight.
- **Alternatives:** `>=` ranges (the previous state); a full lock file (pip-tools / uv).
- **Why:** a fresh clone installs the same thing that was tested. A lock file would pin transitive dependencies too, but it adds a tool.
- **Cost:** transitive dependencies still float. Upgrades are manual.

### Small spaCy model (`en_core_web_sm`)
- **Decision:** Presidio uses `en_core_web_sm`, installed from `requirements.txt` via its GitHub wheel URL.
- **Alternatives:** `en_core_web_lg` (Presidio's default, much larger); a transformer model.
- **Why:** it's small, fast on CPU, and installs with one `pip install -r`.
- **Cost:** lower NER recall on PERSON than the large model. A missed name is sent to Groq in clear. See the threat model in the README.

## Testing

### Separate test database as its own compose service
- **Decision:** `postgres-test` service (port 5433, tmpfs storage). `tests/conftest.py` overrides `DATABASE_URL` with `TEST_DATABASE_URL` before any app module is imported, then runs `alembic upgrade head`.
- **Alternatives:** a second database in the same container (an init script only runs on an empty volume, so existing dev data would have to be wiped); wrapping each test in a rolled-back transaction.
- **Why:** complete isolation. The suite can truncate freely, and the real migrations get exercised on every run.
- **Cost:** one more container to start. Tests fail if it isn't running.

### Tests force a fake Groq key
- **Decision:** `conftest.py` sets `GROQ_API_KEY=test-key-never-sent`.
- **Alternatives:** use the developer's real key from `.env`.
- **Why:** any accidental network call fails with 401 instead of quietly spending quota and making the tests flaky.
- **Cost:** none for unit tests. Live checks go through the running app and the eval scripts, not pytest.

### Seed script replaces a document's chunks
- **Decision:** `scripts/seed_demo.py` deletes each demo document's chunks by `source`, then re-ingests it.
- **Alternatives:** skip documents that already exist; truncate the whole table.
- **Why:** it's safe to rerun and never produces duplicates. It leaves user-uploaded documents alone.
- **Cost:** re-embeds every run (a few seconds on CPU).
