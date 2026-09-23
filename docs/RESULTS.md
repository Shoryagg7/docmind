# Results

Every number in the README comes from a command in this file, run on the current code.
The raw output is pasted as printed. Nothing is paraphrased.

Machine: Ubuntu, 8 CPU cores, 14 GB RAM, no GPU. Python 3.14.4. LLM: Groq `openai/gpt-oss-120b`.

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
