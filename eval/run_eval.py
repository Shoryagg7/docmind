"""Golden-set eval: answer correctness (LLM-as-judge), refusals, consent, cost.

EVAL_MODE=1 PRIVACY_MODE=minimize python -m eval.run_eval --out eval/results/minimize.json

Each item runs the full request path (privacy policy -> graph) with the semantic
cache off. Reading from the cache would replay stored answers and test nothing.
When the policy asks for consent, the item is asked again with consent, as a user
would do, so every item ends with an answer to judge.
"""

import argparse
import asyncio
import json
import logging
import re
import time
from pathlib import Path

from core.config import get_settings
from core.db import async_session
from core.enums import PrivacyAction
from eval.golden_set import GOLDEN_SET
from eval.judge import llm_as_judge
from services.graph import answer_query
from services.llm_client import MODEL

# Deterministic refusal detector: the pipeline's own "no relevant documents" reply,
# or the model saying the context doesn't have the answer.
REFUSAL_RE = re.compile(
    r"i don't know|i do not know|no relevant|not (?:mentioned|provided|specified|stated|included|available)|"
    r"(?:does not|doesn't|do not|don't) (?:mention|say|contain|provide|include|specify|state)|"
    r"(?:cannot|can't|unable to) (?:find|determine|answer)|no information",
    re.IGNORECASE,
)


def is_refusal(answer: str) -> bool:
    return REFUSAL_RE.search(answer.replace("’", "'")) is not None


async def main(out: Path) -> None:
    settings = get_settings()
    items = []
    async with async_session() as session:
        for case in GOLDEN_SET:
            started = time.perf_counter()
            kwargs = {"source": case["source"], "use_cache": False}
            result = await answer_query(session, case["question"], **kwargs)
            consent_requested = result["privacy"]["action"] == PrivacyAction.REQUIRE_CONSENT
            if consent_requested:
                # A policy-only reply (no LLM calls); time the consented run instead.
                started = time.perf_counter()
                result = await answer_query(session, case["question"], allow_sensitive=True, **kwargs)
            latency = time.perf_counter() - started

            correct = llm_as_judge(case["question"], case["reference_answer"], result["answer"])
            egress = result["privacy"]
            item = {
                "question": case["question"],
                "source": case["source"],
                "answerable": case["evidence"] is not None,
                "needs_consent": case.get("needs_consent", False),
                "consent_requested": consent_requested,
                "answer": result["answer"],
                "correct": correct,
                "refused": is_refusal(result["answer"]),
                "tokens": result["tokens"],
                "llm_calls": result["llm_calls"],
                "latency_s": round(latency, 3),
                "restored": egress["restored"],
                "restore_failures": egress["restore_failures"],
            }
            items.append(item)
            status = "PASS" if correct else "FAIL"
            print(f"[{status}] {case['question']}")
            print(f"  reference: {case['reference_answer']}")
            print(f"  actual:    {result['answer']}")

    out.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "model": MODEL,
        "privacy_mode": settings.privacy_mode.value,
        "eval_mode": settings.eval_mode,
        "items": items,
    }
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print()
    print_summary(report)
    print(f"\nwrote {out}")


def print_summary(report: dict) -> None:
    items = report["items"]
    answerable = [i for i in items if i["answerable"]]
    unanswerable = [i for i in items if not i["answerable"]]
    consent_items = [i for i in items if i["needs_consent"]]
    restored = sum(i["restored"] for i in items)
    failures = sum(len(i["restore_failures"]) for i in items)

    print(f"model={report['model']} privacy_mode={report['privacy_mode']} eval_mode={report['eval_mode']}")
    print(f"judge correct (all):        {sum(i['correct'] for i in items)}/{len(items)}")
    print(f"judge correct (answerable): {sum(i['correct'] for i in answerable)}/{len(answerable)}")
    print(f"correct-refusal rate:       {sum(i['refused'] for i in unanswerable)}/{len(unanswerable)} unanswerable items refused")
    print(f"false-refusal rate:         {sum(i['refused'] for i in answerable)}/{len(answerable)} answerable items refused")
    print(
        f"consent requested:          {sum(i['consent_requested'] for i in consent_items)}/{len(consent_items)} expected, "
        f"{sum(i['consent_requested'] for i in items if not i['needs_consent'])} unexpected"
    )
    print(f"tokens (pipeline, excl. judge): {sum(i['tokens'] for i in items)} total")
    print(f"latency mean:               {sum(i['latency_s'] for i in items) / len(items):.2f}s per item")
    rate = failures / (restored + failures) if restored + failures else 0.0
    print(f"placeholder restores:       {restored} ok, {failures} failed (failure rate {rate:.3f})")


if __name__ == "__main__":
    # Per-call token lines ("llm_call ... label=grade total=...") go to stderr, so the
    # token share of each pipeline stage can be read from a run's log.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    asyncio.run(main(parser.parse_args().out))
