# Results

Every number in the README comes from a command in this file, run on the current code.
Output is pasted as printed. The only edits are removed noise lines (progress bars,
library warnings), and each section says where it removed them.

Machine: Ubuntu, 8 CPU cores, 14 GB RAM, no GPU. Python 3.14.4. LLM: Groq `openai/gpt-oss-120b`.

### Where each README number comes from

The README rounds raw values to 2–3 decimal places.

| README number | Raw value | Section below |
|---|---|---|
| recall@1 19/27, recall@3 27/27, MRR@5 0.840 | same | Retrieval |
| 4/4 refused, 1/27 wrongly refused, 30/31, 29/31, consent 2/2 / 0 | same | Golden set, runs 1 and 2 |
| off 29/31 includes a judge error | the `[FAIL]` on the emergency-contact phone, whose answer is the correct +91 90000 00002 | Golden set, run 2 |
| 28 both pass / 1 lost / 2 gained, p = 1.000 | same | Privacy cost experiment |
| tokens 1741.0 → 1847.6 (+106.6), "~6%" | 1740.97 → 1847.55, +106.58; 106.58 / 1740.97 = 6.1% | Privacy cost experiment |
| latency 12.03 s → 12.32 s (+0.28 s) | same | Privacy cost experiment |
| 25 restores / 0 failures | same | Privacy cost experiment |
| grading 72.7%, generate 23.1%, rewrite 4.2% | same | Token share |
| "1.7–1.8k tokens per question", "54–57k per run" | means 1740.97 / 1847.55; totals 53970 / 57274 | Golden set, Privacy cost |
| cache 2.58 s vs 0.017 s vs 0.021 s | 2.578793 s, 0.016756 s, 0.020681 s | Semantic cache latency |
| 0.9879, 0.9399, 0.8754, 0.8718, 0.9262, 0.9654, 0.8693 | same | Semantic-cache threshold probe |
| 0.8728 vs 0.4692 | same | Negation |
| spaCy sm 2/6, md 5/6 names found | counted from the probe output | spaCy model choice |

## spaCy model choice for PERSON detection (probe, not a benchmark)

Seven hand-written sentences, PERSON only, run through Presidio with each spaCy model.
This picks the model. It's too small to be a recall measurement. It ran as a one-off script with all three models installed temporarily. Source:

```python
import time
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
S=["Employee record for Ananya Kulkarni, a fictional test person.",
   "Her manager is Rohan Deshpande.",
   "Ananya Kulkarni joined Tamarind Labs in Pune in 2022.",
   "My name is Maya Chen and I am a 27-year-old backend engineer based in Toronto.",
   "RiverStream was built with Kafka and Flink. CoralCache is written in Go. TidalMap is a routing library.",
   "What is Ananya's work email?", "Who is Ananya Kulkarni's manager?"]
for m in ["en_core_web_sm","en_core_web_md","en_core_web_lg"]:
    t0=time.time()
    a = AnalyzerEngine(nlp_engine=NlpEngineProvider(nlp_configuration={'nlp_engine_name':'spacy','models':[{'lang_code':'en','model_name':m}]}).create_engine())
    load=time.time()-t0
    print(f"== {m} load={load:.1f}s")
    for t in S:
        print("  ", [t[r.start:r.end] for r in a.analyze(t,language='en',entities=["PERSON"])], '|', t[:45])
```

```
$ .venv/bin/python ner_cmp.py
== en_core_web_sm load=0.2s
   [] | Employee record for Ananya Kulkarni, a fictio
   ['Rohan Deshpande'] | Her manager is Rohan Deshpande.
   ['Tamarind Labs'] | Ananya Kulkarni joined Tamarind Labs in Pune
   ['Maya Chen'] | My name is Maya Chen and I am a 27-year-old b
   ['Kafka', 'Flink'] | RiverStream was built with Kafka and Flink. C
   [] | What is Ananya's work email?
   [] | Who is Ananya Kulkarni's manager?
== en_core_web_md load=0.8s
   ['Ananya Kulkarni'] | Employee record for Ananya Kulkarni, a fictio
   ['Rohan Deshpande'] | Her manager is Rohan Deshpande.
   ['Ananya Kulkarni'] | Ananya Kulkarni joined Tamarind Labs in Pune
   ['Maya Chen'] | My name is Maya Chen and I am a 27-year-old b
   ['Kafka'] | RiverStream was built with Kafka and Flink. C
   [] | What is Ananya's work email?
   ["Ananya Kulkarni's"] | Who is Ananya Kulkarni's manager?
== en_core_web_lg load=1.0s
   ['Ananya Kulkarni'] | Employee record for Ananya Kulkarni, a fictio
   ['Rohan Deshpande'] | Her manager is Rohan Deshpande.
   ['Ananya Kulkarni', 'Tamarind Labs'] | Ananya Kulkarni joined Tamarind Labs in Pune
   ['Maya Chen'] | My name is Maya Chen and I am a 27-year-old b
   ['Kafka', 'Flink'] | RiverStream was built with Kafka and Flink. C
   ['Ananya'] | What is Ananya's work email?
   ["Ananya Kulkarni's"] | Who is Ananya Kulkarni's manager?
```

## Retrieval (no LLM)

Recall@k and MRR over the 27 answerable golden items. An item is retrieved at rank r
if the r-th chunk from vector search (scoped to its document) contains its `evidence`
string. First retrieval only, before grading or rewrite. The script first checks that
every evidence string exists in the ingested chunks and exits if one is missing.

**Read with care:** each document is only 2–5 chunks, so recall@3 is close to trivial.
recall@1 and MRR are the informative numbers.

```
$ .venv/bin/python -m eval.run_retrieval
rank= 1  What city does Maya Chen work in?
rank= 1  What city was Maya Chen born in?
rank= 1  What year did Maya Chen move to Toronto?
rank= 1  What university did Maya Chen graduate from?
rank= 3  What company does Maya Chen currently work for?
rank= 2  What is Maya Chen's current job title?
rank= 2  What company did Maya Chen work at before her current job?
rank= 3  What was the name of the fintech company where Maya Chen had her first job?
rank= 1  What technologies were used to build RiverStream?
rank= 1  What programming language is CoralCache written in?
rank= 1  What does TidalMap do?
rank= 2  What instrument does Maya Chen play?
rank= 1  How much does the Starter tier cost per month?
rank= 1  How many gigabytes of storage does the Starter tier include?
rank= 1  How much does the Pro tier cost per month?
rank= 1  How many gigabytes of storage does the Pro tier include?
rank= 1  What kind of support does the Pro tier include?
rank= 2  What uptime SLA does the Enterprise tier guarantee?
rank= 1  Within how many days can Starter and Pro customers request a refund?
rank= 1  How long are deleted files kept in the recovery bin before permanent deletion?
rank= 1  How long is account data for cancelled subscriptions retained?
rank= 1  What encryption is used to protect data at rest?
rank= 1  What is Ananya Kulkarni's work email address?
rank= 2  Who is Ananya Kulkarni's manager?
rank= 2  What is the mobile number of Ananya Kulkarni's emergency contact?
rank= 1  Is Ananya Kulkarni's personal email address on the example.com domain?
rank= 1  Does Ananya Kulkarni's PAN start with the letters ABC?

answerable items: 27 (every evidence string verified present in the DB)
recall@1: 19/27 = 0.704
recall@3: 27/27 = 1.000
recall@5: 27/27 = 1.000
MRR@5: 0.840
```

## Negation (no LLM)

Re-run on current code. It reproduces the earlier findings: a statement and its own
negation embed almost as close as a paraphrase, and a negated query retrieves the same chunks.

```
$ .venv/bin/python -m eval.run_negation
==============================================================================
A statement vs. its own NEGATION (opposite meaning — should score LOW)
==============================================================================
  0.8881  drug approval
  0.9076  refund eligibility (from sample2.pdf)
  0.8358  support hours
  0.8712  encryption
  0.7755  employment
  0.9586  certification

==============================================================================
Control: genuinely DIFFERENT statements (should score lower than above)
==============================================================================
  0.7270  different fact, same doc
  0.6706  different fact, same person
  0.0101  unrelated topics

  average, statement vs its negation : 0.8728
  average, genuinely different pairs : 0.4692
  gap                                : +0.4036

==============================================================================
Retrieval level: does a negated query retrieve different chunks?
==============================================================================
  query A (positive): Are Enterprise customers eligible for the 14-day refund window?
    -> chunk ids [36, 37]
  query B (negated) : Are Enterprise customers not eligible for the 14-day refund window?
    -> chunk ids [36, 37]

  same chunks retrieved: True
  query A vs query B similarity: 0.9885
```

## Semantic-cache threshold probe (no LLM, no Redis)

The same question pairs as the original cache experiments, re-measured on current code.
"HIT" applies the cache's own rule: normalized similarity >= 0.92 and both questions
agree on negation.

```
$ .venv/bin/python -m eval.run_cache_probe
threshold = 0.92
paraphrase (should hit)
    'What city does Maya Chen work in?' vs 'Which city is Maya Chen based in?'
    raw 0.9399  normalized 0.9654  -> HIT
paraphrase, no '?' (should hit)
    'What city does Maya Chen work in?' vs 'Which city is Maya Chen based in'
    raw 0.8754  normalized 0.9654  -> HIT
different answer: born vs work (must miss)
    'What city does Maya Chen work in?' vs 'What city was Maya Chen born in?'
    raw 0.8718  normalized 0.8693  -> miss
negation (must miss)
    'Which tiers are eligible for the 14-day refund?' vs 'Which tiers are not eligible for the 14-day refund?'
    raw 0.9879  normalized 0.9841  -> miss
negation, no marker word (must miss)
    'Which tiers are eligible for the 14-day refund?' vs 'Which tiers are barred from the 14-day refund?'
    raw 0.9273  normalized 0.9262  -> HIT
```

## Golden set: answer quality, refusals, consent (LLM-as-judge)

31 items: 22 answerable on the two original documents, 5 answerable on
synthetic_pii.pdf (2 of them need consent), and 4 unanswerable. Semantic cache off,
temperature 0 (`EVAL_MODE=1`). Each arm is a single run (n=1). The judge is itself an
LLM and can be wrong: in the `off` run it marked a correct answer ("+91 90000 00002")
as incorrect.

`INFO` log lines (one per LLM call), tqdm `Batches:` progress bars and Presidio's
"entity not mapped" warnings are removed below. They're kept in
`eval/results/*.log`, and per-item JSON is in `eval/results/*.json`.

### Run 1: PRIVACY_MODE=minimize (the default)

```
$ EVAL_MODE=1 PRIVACY_MODE=minimize .venv/bin/python -m eval.run_eval --out eval/results/minimize.json
[PASS] What city does Maya Chen work in?
  reference: Toronto
  actual:    Maya Chen works in Toronto【1】.
[PASS] What city was Maya Chen born in?
  reference: Vancouver
  actual:    Maya Chen was born in Vancouver【1】.
[PASS] What year did Maya Chen move to Toronto?
  reference: 2019
  actual:    Maya Chen moved to Toronto in 2019【1】.
[PASS] What university did Maya Chen graduate from?
  reference: University of Waterloo
  actual:    Maya Chen graduated from the University of Waterloo【1】.
[PASS] What company does Maya Chen currently work for?
  reference: Northwind Analytics
  actual:    Maya Chen currently works for Northwind Analytics【[1]】.
[PASS] What is Maya Chen's current job title?
  reference: Senior Backend Engineer
  actual:    Maya Chen’s current job title is Senior Backend Engineer【2】.
[PASS] What company did Maya Chen work at before her current job?
  reference: Bluefin Logistics
  actual:    Maya Chen worked at Bluefin Logistics before her current job at Northwind Analytics [1].
[PASS] What was the name of the fintech company where Maya Chen had her first job?
  reference: Ledgerly
  actual:    The fintech company was called Ledgerly【1】.
[PASS] What technologies were used to build RiverStream?
  reference: Kafka and Flink
  actual:    RiverStream was built with Kafka and Flink [1]
[PASS] What programming language is CoralCache written in?
  reference: Go
  actual:    CoralCache is written in Go【1】.
[PASS] What does TidalMap do?
  reference: It's an open source geospatial routing library.
  actual:    TidalMap is an open‑source geospatial routing library that the author maintains in their spare time and that is used by several small logistics companies【1】.
[FAIL] What instrument does Maya Chen play?
  reference: Violin
  actual:    I don't know — no relevant documents found.
[PASS] How much does the Starter tier cost per month?
  reference: 5 dollars per month
  actual:    The Starter tier costs 5 dollars per month【1】.
[PASS] How many gigabytes of storage does the Starter tier include?
  reference: 50 gigabytes
  actual:    The Starter tier includes 50 gigabytes of storage【1】.
[PASS] How much does the Pro tier cost per month?
  reference: 15 dollars per month
  actual:    The Pro tier costs 15 dollars per month【1】.
[PASS] How many gigabytes of storage does the Pro tier include?
  reference: 500 gigabytes
  actual:    The Pro tier includes **500 gigabytes of storage**【1】.
[PASS] What kind of support does the Pro tier include?
  reference: Priority email support
  actual:    The Pro tier includes priority email support (with a 12‑hour response time)【1】【2】
[PASS] What uptime SLA does the Enterprise tier guarantee?
  reference: 99.99 percent
  actual:    The Enterprise tier guarantees a 99.99 percent uptime SLA【1】.
[PASS] Within how many days can Starter and Pro customers request a refund?
  reference: 14 days
  actual:    Customers on the Starter and Pro tiers can request a full refund within 14 days of their initial purchase, as long as they have used less than 10 percent of their storage allocation. [1]
[PASS] How long are deleted files kept in the recovery bin before permanent deletion?
  reference: 30 days
  actual:    Deleted files are kept in the recovery bin for 30 days before they are permanently deleted. [1]
[PASS] How long is account data for cancelled subscriptions retained?
  reference: 90 days
  actual:    Account data for cancelled subscriptions is retained for 90 days before it is permanently purged. [1][2]
[PASS] What encryption is used to protect data at rest?
  reference: AES-256
  actual:    Data at rest is protected with AES‑256 encryption【1】.
[PASS] What is the capital of France?
  reference: Not answerable — the document is a bio, not a geography reference.
  actual:    I don't know — no relevant documents found.
[PASS] What city does Maya Chen work in?
  reference: Not answerable — sample2.pdf is a product doc and never mentions Maya Chen.
  actual:    I don't know — no relevant documents found.
[PASS] What is the boiling point of water in Celsius?
  reference: Not answerable — neither uploaded document covers this topic.
  actual:    I don't know — no relevant documents found.
[PASS] What is Ananya Kulkarni's work email address?
  reference: ananya.kulkarni@tamarind.example
  actual:    ananya.kulkarni@tamarind.example [1]
[PASS] Who is Ananya Kulkarni's manager?
  reference: Rohan Deshpande
  actual:    Rohan Deshpande [1]
[PASS] What is the mobile number of Ananya Kulkarni's emergency contact?
  reference: +91 90000 00002 (her sister, Meera Kulkarni)
  actual:    The mobile number of Ananya Kulkarni’s emergency contact is +91 90000 00002 [1].
[PASS] Is Ananya Kulkarni's personal email address on the example.com domain?
  reference: Yes (ananya.k@example.com)
  actual:    Yes, Ananya Kulkarni's personal email address is on the **example.com** domain【1】.
[PASS] Does Ananya Kulkarni's PAN start with the letters ABC?
  reference: Yes (ABCPK1234Z)
  actual:    Yes, Ananya Kulkarni’s PAN begins with the letters “ABC” [1].
[PASS] What is Ananya Kulkarni's passport number?
  reference: Not answerable — the record has no passport number.
  actual:    I don't know — no relevant documents found.

model=openai/gpt-oss-120b privacy_mode=minimize eval_mode=True
judge correct (all):        30/31
judge correct (answerable): 26/27
correct-refusal rate:       4/4 unanswerable items refused
false-refusal rate:         1/27 answerable items refused
consent requested:          2/2 expected, 0 unexpected
tokens (pipeline, excl. judge): 57274 total
latency mean:               12.32s per item
placeholder restores:       25 ok, 0 failed (failure rate 0.000)

wrote eval/results/minimize.json
```

### Run 2: PRIVACY_MODE=off (the controlled experiment's baseline)

```
$ EVAL_MODE=1 PRIVACY_MODE=off .venv/bin/python -m eval.run_eval --out eval/results/off.json
WARNING huggingface_hub.utils._http Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.


WARNING presidio-analyzer Recognizer not added to registry because language is not supported by registry - CreditCardRecognizer supported languages: es, registry supported languages: en
WARNING presidio-analyzer Recognizer not added to registry because language is not supported by registry - CreditCardRecognizer supported languages: it, registry supported languages: en
WARNING presidio-analyzer Recognizer not added to registry because language is not supported by registry - CreditCardRecognizer supported languages: pl, registry supported languages: en
WARNING presidio-analyzer Recognizer not added to registry because language is not supported by registry - EsNifRecognizer supported languages: es, registry supported languages: en
WARNING presidio-analyzer Recognizer not added to registry because language is not supported by registry - EsNieRecognizer supported languages: es, registry supported languages: en
WARNING presidio-analyzer Recognizer not added to registry because language is not supported by registry - ItDriverLicenseRecognizer supported languages: it, registry supported languages: en
WARNING presidio-analyzer Recognizer not added to registry because language is not supported by registry - ItFiscalCodeRecognizer supported languages: it, registry supported languages: en
WARNING presidio-analyzer Recognizer not added to registry because language is not supported by registry - ItVatCodeRecognizer supported languages: it, registry supported languages: en
WARNING presidio-analyzer Recognizer not added to registry because language is not supported by registry - ItIdentityCardRecognizer supported languages: it, registry supported languages: en
WARNING presidio-analyzer Recognizer not added to registry because language is not supported by registry - ItPassportRecognizer supported languages: it, registry supported languages: en
WARNING presidio-analyzer Recognizer not added to registry because language is not supported by registry - PlPeselRecognizer supported languages: pl, registry supported languages: en
[PASS] What city does Maya Chen work in?
  reference: Toronto
  actual:    Maya Chen works in Toronto【1】.

[PASS] What city was Maya Chen born in?
  reference: Vancouver
  actual:    Maya Chen was born in Vancouver【1】.

[PASS] What year did Maya Chen move to Toronto?
  reference: 2019
  actual:    Maya Chen moved to Toronto in 2019【1】.

[PASS] What university did Maya Chen graduate from?
  reference: University of Waterloo
  actual:    Maya Chen graduated from the University of Waterloo【1】.

[FAIL] What company does Maya Chen currently work for?
  reference: Northwind Analytics
  actual:    I don't know.

[PASS] What is Maya Chen's current job title?
  reference: Senior Backend Engineer
  actual:    Maya Chen’s current job title is **Senior Backend Engineer**【2】.

[PASS] What company did Maya Chen work at before her current job?
  reference: Bluefin Logistics
  actual:    Maya Chen worked at **Bluefin Logistics** before her current position at Northwind Analytics【1】.

[PASS] What was the name of the fintech company where Maya Chen had her first job?
  reference: Ledgerly
  actual:    Maya Chen’s first job was at a fintech company called Ledgerly【1】.

[PASS] What technologies were used to build RiverStream?
  reference: Kafka and Flink
  actual:    RiverStream was built using **Kafka** and **Flink** as its core technologies【1】.

[PASS] What programming language is CoralCache written in?
  reference: Go
  actual:    CoralCache is written in Go【1】.

[PASS] What does TidalMap do?
  reference: It's an open source geospatial routing library.
  actual:    TidalMap is an open‑source geospatial routing library that the author maintains in spare time and that is used by several small logistics companies【1】.

[PASS] What instrument does Maya Chen play?
  reference: Violin
  actual:    Maya Chen plays the violin【1】.

[PASS] How much does the Starter tier cost per month?
  reference: 5 dollars per month
  actual:    The Starter tier costs 5 dollars per month【1】.

[PASS] How many gigabytes of storage does the Starter tier include?
  reference: 50 gigabytes
  actual:    The Starter tier includes **50 gigabytes** of storage【1】.

[PASS] How much does the Pro tier cost per month?
  reference: 15 dollars per month
  actual:    The Pro tier costs 15 dollars per month【1】.

[PASS] How many gigabytes of storage does the Pro tier include?
  reference: 500 gigabytes
  actual:    The Pro tier includes **500 gigabytes of storage**【1】.

[PASS] What kind of support does the Pro tier include?
  reference: Priority email support
  actual:    The Pro tier provides **priority email support** (with a typical 12‑hour response time)【1】. It is also mentioned as part of the Pro offering in the product overview【2】.

[PASS] What uptime SLA does the Enterprise tier guarantee?
  reference: 99.99 percent
  actual:    The Enterprise tier guarantees a 99.99 percent uptime SLA【1】.

[PASS] Within how many days can Starter and Pro customers request a refund?
  reference: 14 days
  actual:    Starter and Pro customers can request a full refund within 14 days of their initial purchase【1】.

[PASS] How long are deleted files kept in the recovery bin before permanent deletion?
  reference: 30 days
  actual:    Deleted files are kept in the recovery bin for 30 days before they are permanently deleted. [1]

[PASS] How long is account data for cancelled subscriptions retained?
  reference: 90 days
  actual:    Account data for cancelled subscriptions is retained for 90 days before it is permanently purged. [1][2]

[PASS] What encryption is used to protect data at rest?
  reference: AES-256
  actual:    Data at rest is protected with AES‑256 encryption【1】.



[PASS] What is the capital of France?
  reference: Not answerable — the document is a bio, not a geography reference.
  actual:    I don't know — no relevant documents found.



[PASS] What city does Maya Chen work in?
  reference: Not answerable — sample2.pdf is a product doc and never mentions Maya Chen.
  actual:    I don't know — no relevant documents found.



[PASS] What is the boiling point of water in Celsius?
  reference: Not answerable — neither uploaded document covers this topic.
  actual:    I don't know — no relevant documents found.

[PASS] What is Ananya Kulkarni's work email address?
  reference: ananya.kulkarni@tamarind.example
  actual:    Ananya Kulkarni's work email address is **ananya.kulkarni@tamarind.example**【1】.

[PASS] Who is Ananya Kulkarni's manager?
  reference: Rohan Deshpande
  actual:    Ananya Kulkarni’s manager is Rohan Deshpande【1】.

[FAIL] What is the mobile number of Ananya Kulkarni's emergency contact?
  reference: +91 90000 00002 (her sister, Meera Kulkarni)
  actual:    The mobile number of Ananya Kulkarni's emergency contact is +91 90000 00002【1】.

[PASS] Is Ananya Kulkarni's personal email address on the example.com domain?
  reference: Yes (ananya.k@example.com)
  actual:    Yes, her personal email address is on the **example.com** domain (ananya.k@example.com)【1】.

[PASS] Does Ananya Kulkarni's PAN start with the letters ABC?
  reference: Yes (ABCPK1234Z)
  actual:    Yes, Ananya Kulkarni’s PAN begins with “ABC” — it is listed as **ABCPK1234Z**【1】.



[PASS] What is Ananya Kulkarni's passport number?
  reference: Not answerable — the record has no passport number.
  actual:    I don't know — no relevant documents found.

model=openai/gpt-oss-120b privacy_mode=off eval_mode=True
judge correct (all):        29/31
judge correct (answerable): 25/27
correct-refusal rate:       4/4 unanswerable items refused
false-refusal rate:         1/27 answerable items refused
consent requested:          0/2 expected, 0 unexpected
tokens (pipeline, excl. judge): 53970 total
latency mean:               12.03s per item
placeholder restores:       0 ok, 0 failed (failure rate 0.000)

wrote eval/results/off.json
```

## Privacy cost experiment (off vs minimize, paired)

Latency is wall-clock per item on a shared free-tier API, so ±0.3 s is within noise.

```
$ .venv/bin/python -m eval.compare_privacy eval/results/off.json eval/results/minimize.json
paired questions: 31 (eval_mode off=True minimize=True)
accuracy off:      29/31
accuracy minimize: 30/31
both pass: 28   both fail: 0
pass off -> fail minimize: 1
    What instrument does Maya Chen play?
fail off -> pass minimize: 2
    What company does Maya Chen currently work for?
    What is the mobile number of Ananya Kulkarni's emergency contact?
exact two-sided sign test on 3 discordant pairs: p = 1.000
tokens: off mean 1740.97 median 1511.00 | minimize mean 1847.55 median 1547.00 | mean delta +106.58
latency_s: off mean 12.03 median 10.62 | minimize mean 12.32 median 10.93 | mean delta +0.28
placeholder restores (minimize): 25 ok, 0 failed, failure rate 0.000
```

## Token share per pipeline stage

From the per-call `llm_call` log lines of the `off` run (31 questions, judge excluded).

```
$ .venv/bin/python -m eval.token_share eval/results/off.log
    grade:  39232 tokens in 109 calls =  72.7%
 generate:  12464 tokens in  27 calls =  23.1%
  rewrite:   2274 tokens in   8 calls =   4.2%
    total:  53970 tokens
```

## Semantic cache latency (live, via POST /query)

Server running locally, Redis flushed first. The first request after server start also
loads spaCy and the embedding model, so the second cold question is the fair cold number.

```
$ bash cache_latency.sh   # curl -w %{time_total} against POST /query, see below
OK
13.587588s  cached=False llm_calls=4 tokens=1475 | What city does Maya Chen work in? -> Maya Chen works in Toronto. [1]
0.024739s  cached=True llm_calls=0 tokens=0 | What city does Maya Chen work in? -> Maya Chen works in Toronto. [1]
0.020681s  cached=True llm_calls=0 tokens=0 | Which city is Maya Chen based in? -> Maya Chen works in Toronto. [1]
2.578793s  cached=False llm_calls=4 tokens=1473 | What year did Maya Chen move to Toronto? -> Maya Chen moved to Toronto in 2019【1】.
0.016756s  cached=True llm_calls=0 tokens=0 | What year did Maya Chen move to Toronto? -> Maya Chen moved to Toronto in 2019【1】.
```

Script used:

```bash
docker compose exec -T redis redis-cli FLUSHALL
for q in "What city does Maya Chen work in?" "What city does Maya Chen work in?" "Which city is Maya Chen based in?"; do
  curl -s -o $SCRATCH/r.json -w "%{time_total}s  " -X POST localhost:8001/query \
    -H 'content-type: application/json' -d "{\"question\": \"$q\", \"source\": \"sample.pdf\"}"
  .venv/bin/python -c "import json; r=json.load(open('$SCRATCH/r.json')); print(f\"cached={r['cached']} llm_calls={r['llm_calls']} tokens={r['tokens']} | $q -> {r['answer']}\")"
done
```
