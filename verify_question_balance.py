#!/usr/bin/env python3
"""
Verifies that the interest-signal questions in seed.py don't systematically
favor one career category over another.

Why this exists: an earlier version of seed.py had "Management" as an option
in 10 out of 10 signal questions, while "Non-IT" appeared in just 1 out of 10.
That meant Management would win the routing vote almost regardless of what a
person actually said about themselves, and Non-IT was nearly unreachable.
The bug was found by manually tallying tags after the fact — this script
makes that check automatic, so it's caught the moment someone edits a
question's tags, not months later when reviewing results.

Run this after ANY edit to a question's "tags" list in seed.py:

    python3 verify_question_balance.py

Exit code 0 = balanced. Exit code 1 = imbalance detected, with details on
which category is over/under-represented.
"""
import re
import sys
from collections import Counter

SEED_PATH = "seed.py"

# How far a category's appearance rate is allowed to drift from the average
# before this is treated as a real imbalance rather than natural variation.
# With 6 categories, an evenly split design puts each category in 2/3 of
# questions (since 4 options are shown out of 6 real categories) — but this
# script doesn't hardcode that assumption, it just checks relative spread.
MAX_DEVIATION_RATIO = 0.15  # 15 percentage points from the mean is a flag


def check_balance(seed_path: str = SEED_PATH):
    """Returns (ok: bool, report: str). Used by both the standalone CLI below
    and by seed.py, which calls this before touching the database so a
    rebalancing mistake is caught before bad data ever gets seeded."""
    content = open(seed_path, encoding="utf-8").read()
    tag_lists = re.findall(r'"tags":\s*(\[[^\]]+\])', content)

    if not tag_lists:
        return True, "No interest-signal questions with \"tags\" found — nothing to check."

    tally = Counter()
    for t in tag_lists:
        for cat in re.findall(r'"([\w-]+)"', t):
            tally[cat] += 1

    n = len(tag_lists)
    rates = {cat: count / n for cat, count in tally.items()}
    mean_rate = sum(rates.values()) / len(rates)

    lines = [f"{n} interest-signal questions found, {len(tally)} distinct categories tagged.\n"]
    problems = []
    for cat, rate in sorted(rates.items(), key=lambda x: -x[1]):
        deviation = rate - mean_rate
        flag = "  <-- FLAGGED" if abs(deviation) > MAX_DEVIATION_RATIO else ""
        lines.append(f"  {cat:12s} {tally[cat]:2d}/{n} questions ({round(rate*100)}%){flag}")
        if abs(deviation) > MAX_DEVIATION_RATIO:
            problems.append((cat, rate, mean_rate))

    if problems:
        lines.append("\nFAILED — one or more categories are over/under-represented:")
        for cat, rate, mean in problems:
            direction = "over" if rate > mean else "under"
            lines.append(f"  {cat} is {direction}-represented ({round(rate*100)}% vs {round(mean*100)}% average)")
        lines.append("\nA category that appears in far more (or fewer) questions than others will")
        lines.append("win (or lose) the routing vote based on question design, not on what people")
        lines.append("actually say about themselves. Rebalance the 'tags' lists before deploying.")
        return False, "\n".join(lines)

    lines.append("\nOK — category representation is balanced.")
    return True, "\n".join(lines)


def main() -> int:
    ok, report = check_balance()
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
