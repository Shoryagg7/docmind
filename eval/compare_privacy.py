"""Privacy-cost experiment: pair the same questions under PRIVACY_MODE=off vs minimize.

python -m eval.compare_privacy eval/results/off.json eval/results/minimize.json

Reports agreement, flips in each direction, an exact two-sided sign test on the
discordant pairs, token and latency deltas, and the placeholder restore failure rate.
"""

import argparse
import json
from math import comb
from pathlib import Path
from statistics import mean, median


def sign_test_p(b: int, c: int) -> float:
    """Exact two-sided sign test: P(a split at least this uneven | flips are 50/50)."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(min(b, c) + 1)) / 2**n
    return min(1.0, 2 * tail)


def main(off_path: Path, minimize_path: Path) -> None:
    off = json.loads(off_path.read_text())
    mini = json.loads(minimize_path.read_text())
    assert off["privacy_mode"] == "off" and mini["privacy_mode"] == "minimize"
    pairs = list(zip(off["items"], mini["items"], strict=True))
    assert all(a["question"] == b["question"] for a, b in pairs), "runs are not paired"

    both_pass = sum(a["correct"] and b["correct"] for a, b in pairs)
    both_fail = sum(not a["correct"] and not b["correct"] for a, b in pairs)
    lost = [a["question"] for a, b in pairs if a["correct"] and not b["correct"]]
    gained = [a["question"] for a, b in pairs if not a["correct"] and b["correct"]]

    print(f"paired questions: {len(pairs)} (eval_mode off={off['eval_mode']} minimize={mini['eval_mode']})")
    print(f"accuracy off:      {sum(a['correct'] for a, _ in pairs)}/{len(pairs)}")
    print(f"accuracy minimize: {sum(b['correct'] for _, b in pairs)}/{len(pairs)}")
    print(f"both pass: {both_pass}   both fail: {both_fail}")
    print(f"pass off -> fail minimize: {len(lost)}")
    for q in lost:
        print(f"    {q}")
    print(f"fail off -> pass minimize: {len(gained)}")
    for q in gained:
        print(f"    {q}")
    print(f"exact two-sided sign test on {len(lost) + len(gained)} discordant pairs: p = {sign_test_p(len(lost), len(gained)):.3f}")

    for name, key in (("tokens", "tokens"), ("latency_s", "latency_s")):
        a = [x[key] for x, _ in pairs]
        b = [y[key] for _, y in pairs]
        print(
            f"{name}: off mean {mean(a):.2f} median {median(a):.2f} | "
            f"minimize mean {mean(b):.2f} median {median(b):.2f} | "
            f"mean delta {mean(b) - mean(a):+.2f}"
        )

    restored = sum(y["restored"] for _, y in pairs)
    failures = [f for _, y in pairs for f in y["restore_failures"]]
    attempts = restored + len(failures)
    rate = len(failures) / attempts if attempts else 0.0
    print(f"placeholder restores (minimize): {restored} ok, {len(failures)} failed, failure rate {rate:.3f}")
    if failures:
        print(f"    unrestored: {failures}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("off", type=Path)
    parser.add_argument("minimize", type=Path)
    args = parser.parse_args()
    main(args.off, args.minimize)
