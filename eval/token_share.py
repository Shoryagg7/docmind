"""Token share per pipeline stage, read from an eval run's log.

python -m eval.token_share eval/results/off.log

Counts the `llm_call ... label=<stage> ... total=<n>` lines that core/usage.py
logs for every Groq call. Judge calls are eval overhead, so they're excluded.
"""

import re
import sys
from collections import Counter

LINE_RE = re.compile(r"llm_call model=\S+ label=(\S+) .* total=(\d+)")


def main(path: str) -> None:
    tokens, calls = Counter(), Counter()
    for line in open(path, encoding="utf-8"):
        match = LINE_RE.search(line)
        if match and match.group(1) != "judge":
            tokens[match.group(1)] += int(match.group(2))
            calls[match.group(1)] += 1
    total = sum(tokens.values())
    for label, count in tokens.most_common():
        print(f"{label:>9}: {count:6d} tokens in {calls[label]:3d} calls = {100 * count / total:5.1f}%")
    print(f"{'total':>9}: {total:6d} tokens")


if __name__ == "__main__":
    main(sys.argv[1])
