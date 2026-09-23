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

### Medium spaCy model (`en_core_web_md`)
- **Decision:** Presidio uses `en_core_web_md`, installed from `requirements.txt` via its GitHub wheel URL.
- **Alternatives:** `en_core_web_sm` (smaller); `en_core_web_lg` (Presidio's default); a transformer model.
- **Why:** on a 7-sentence probe (docs/RESULTS.md), `sm` found the fictional name in 2 of the 7 sentences and `md` in 5. `lg` also found 5 and caught one more first-name mention, but it tagged more non-people ("Tamarind Labs", "Flink") as PERSON and is a much larger download.
- **Cost:** it still misses some names (e.g. a bare first name in a question) and tags some product names ("Kafka") as PERSON. A miss goes to Groq in clear. A false positive hides a harmless word from the model.

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

## Privacy boundary

### Pseudonymize (reversible), don't just redact
- **Decision:** replace each sensitive value with a typed placeholder (`<EMAIL_1>`), then swap it back locally in the answer.
- **Alternatives:** irreversible redaction (`[REDACTED]`); run a local LLM so nothing leaves.
- **Why:** with redaction, a lookup like "what is her email?" can't be answered. With placeholders, the model copies `<EMAIL_1>` into the answer and the real value is restored on this machine. A local LLM is out of reach on a CPU-only box at useful quality and speed.
- **Cost:** the model can't reason about a value's content without consent (see REQUIRE_CONSENT). Placeholders also cost some answer quality; the privacy-cost experiment measures how much.

### Entity set: PERSON, EMAIL, PHONE, CARD, PAN, Aadhaar. Not ORG or LOCATION
- **Decision:** detect only those six types.
- **Alternatives:** Presidio's full default set (adds LOCATION, ORG-like NRP, DATE_TIME, URL, ...).
- **Why:** nearly every document answer names a company or a city ("Maya Chen works in Toronto"). Hiding them destroys utility for little privacy gain. On their own they rarely identify a person.
- **Cost:** a company, city and job title together can still identify someone (a quasi-identifier). That's listed under what this does NOT protect.

### Detection: Presidio + spaCy, plus four regex recognizers
- **Decision:** Presidio's built-ins for PERSON (spaCy NER), PHONE_NUMBER, CREDIT_CARD (Luhn-checked), EMAIL_ADDRESS. Custom regexes for PAN, Aadhaar-like 12-digit numbers, +91 mobiles, and emails.
- **Alternatives:** regex only; a cloud DLP API (sending data to another third party defeats the point).
- **Why:** names need NER, and fixed-format IDs are exact with regex. The extra email regex exists because Presidio's email recognizer rejected `rohan.deshpande@tamarind.example`: it validates the TLD, and that address went out in clear during development until the regex was added.
- **Cost:** the Aadhaar regex matches any 12-digit number, so some harmless numbers get hidden. No minimum score threshold is set: for a privacy gate, over-hiding is cheaper than a leak.

### One value, one placeholder, for the whole request
- **Decision:** the value→placeholder map lives in a request-scoped `ContextVar` (the same pattern as `core/usage.py`). Once a value has been seen in a request, it's replaced wherever it appears later, even where NER misses it. For names, each part of 3+ characters maps to the full name's placeholder ("Ananya" → `<PERSON_1>`).
- **Alternatives:** detect each text independently; a global map.
- **Why:** the model has to see the same `<PERSON_1>` in the question and in the chunks to connect them. NER is inconsistent from one sentence to the next (see the model probe in docs/RESULTS.md). A global map would mix up concurrent users.
- **Cost:** a surname shared by two people ("Kulkarni") maps to whichever full name came first.

### The gate is `services/llm_client.py`, both ways
- **Decision:** `_gate()` pseudonymizes every message (system + user) and records it in the egress record before the HTTP call. `generate()` / `generate_stream()` restore placeholders before returning. A test fails if any other module imports the Groq SDK.
- **Alternatives:** redact at each call site (grader, rewrite, generate).
- **Why:** one place to audit, and a new LLM call site can't forget it. Restoring there too means a rewritten query (which comes back with placeholders) is turned back into real text before local retrieval embeds it.
- **Cost:** everything gets pseudonymized, including system prompts that never contain PII (a small amount of wasted CPU).

### Fail closed with a catch-all
- **Decision:** any exception from the detector becomes `PrivacyBlockedError` at the gate and `BLOCK` at the start of the request. Both use a deliberate `except Exception`.
- **Alternatives:** catch only known Presidio errors.
- **Why:** an unexpected error type from spaCy must not open the gate. The request-start check runs the detector on the question before any call, so a broken detector means zero outbound calls.
- **Cost:** a bug in our own code can also show up as BLOCK. The error is chained (`from exc`) so it can still be debugged.

### REQUIRE_CONSENT: deterministic keyword + type rules
- **Decision:** a question needs consent when it has a "look inside the value" word (valid, domain, starts with, digits, compare, same, sum, ...) AND refers to a sensitive type, either by keyword (email, phone, PAN, card, Aadhaar, name) or by containing a value. Consent releases only the named types. Everything else stays hidden.
- **Alternatives:** ask an LLM to classify the question (that would send it before the policy has run); always require consent when PII is present (lookups would break).
- **Why:** it's local, instant, explainable, and easy to test.
- **Cost, known false negatives** (questions that need content but won't be flagged; the model then sees only a placeholder and should say it can't tell):
  - Paraphrases without a listed word: "Is her address a Google one?", "Is her number from Mumbai?", "Which email looks older?"
  - Type implied, not named: "Is it valid?" with no type word and no value in the question.
  - Non-English questions.
  - Reasoning words outside the list ("resembles", "overlap", "differ").
- **Known false positives:** "Does the card tier include the same storage?" (a type word and "same", but no PII involved) asks for consent unnecessarily.

### Consent answers never touch the cache
- **Decision:** when consent is used, the request skips both cache read and cache write.
- **Alternatives:** cache with a "consented" tag.
- **Why:** the cache matches by similarity. A later paraphrase asked without consent would hit and receive an answer that depended on releasing the value.
- **Cost:** consented questions always cost a full pipeline run.

### Egress record contents
- **Decision:** per request: mode, action, entity types with counts, every outbound message exactly as sent, placeholders restored, and unrestored placeholders. Values released by consent are shown as `[EMAIL sent in clear]`, never copied. With `PRIVACY_MODE=off`, message text isn't recorded at all.
- **Alternatives:** counts only.
- **Why:** "what left this machine" should be checkable text, not a claim. The record never adds a raw value that isn't in what was actually sent.
- **Cost:** the `/query` response gets larger (every prompt is included).

### Tolerant restore; unknown placeholders are left and flagged
- **Decision:** `<PHONE 1>`, `<phone_1>`, `[PHONE_1]` normalize to `<PHONE_1>`. A placeholder that isn't in the map (`<EMAIL_7>`, `<PERSON>`) stays as literal text and is added to `restore_failures`.
- **Alternatives:** strip unknown placeholders; guess the nearest one.
- **Why:** guessing could put the wrong person's value into an answer. Visible and counted is better than silently wrong.
- **Cost:** a user may see a raw `<EMAIL_7>` token in the answer.

### Streaming: hold back a possible partial placeholder
- **Decision:** `StreamRestorer` holds text from the last unclosed `<` or `[` until it closes or passes 24 characters.
- **Alternatives:** buffer the whole answer (loses streaming).
- **Why:** the model emits `<PER` + `SON_1>` as separate tokens. Holding back only the possible placeholder keeps the stream live.
- **Cost:** a literal `<` in an answer delays up to 24 characters of output.

### Two clean-up rules on spaCy PERSON spans
- **Decision:** cut a PERSON span at its first line break, and drop it if it doesn't start with a capital letter.
- **Alternatives:** use NER output as-is; keep a stoplist of known non-names.
- **Why:** on the demo docs spaCy produced `"Maya Chen\nPersonal"` (a separate placeholder from "Maya Chen") and tagged the word "bin" as a person. Both rules are one line each and easy to justify.
- **Cost:** capitalized non-names are still hidden ("Starter", "Kafka", "Java", "Cassandra", "Terraform"). They round-trip correctly (the model copies `<PERSON_2>` and it's restored to "Kafka"), but the model can't use what the word means. The privacy-cost experiment measures the effect.

## Cleanup

### Delete `services/rag.py` and `services/cache.py`
- **Decision:** move the two constants still in use (`SYSTEM_PROMPT`, `CITATION_PATTERN`) into `services/graph.py`, then delete both files.
- **Alternatives:** keep `rag.py` as a "straight-line baseline for comparison".
- **Why:** no route, eval or test called either module (`rag.answer_question` or the exact-match `cache.py`). Dead code is one more thing to explain and to keep inside the privacy gate. Git history still has both.
- **Cost:** there's no runnable non-agentic baseline to compare against.
