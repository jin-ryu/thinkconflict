"""Select a diverse proposal set for direct Codex review in Pilot 2.

The lexical score is only a recall-oriented proposal mechanism. It is never used
as the validity label; every selected pair must be judged against the rubric.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


LINKS = (
    ("work", "free", "busy", "business trip", "career", "job", "company", "industry", "professional", "commut", "conference", "presentation", "interview", "break", "after work", "evening", "weekend"),
    ("health", "fatig", "unwell", "stress", "distress", "recovery", "light", "exercise", "fitness", "relax", "wind down", "low-energy"),
    ("residence", "moved", "relocat", "travel", "trip", "site", "local", "heritage", "hotel", "hostel", "resort"),
    ("social", "marital", "dating", "single", "friend", "date", "gathering", "movie night"),
    ("child", "children", "family", "parent", "school", "nap"),
)


def score(row: dict) -> int:
    left = f"{row['questions'][0]} {row['answers'][0]}".lower()
    right = f"{row['questions'][1]} {row['answers'][1]}".lower()
    value = 0
    for group in LINKS:
        if any(term in left for term in group) and any(term in right for term in group):
            value += 5
            value += min(sum(term in left for term in group), 3)
            value += min(sum(term in right for term in group), 3)
    if row["policies"] == ["SUPERSEDE", "CONDITION"]:
        value += 2
    if row["policies"] == ["CONDITION", "SUPERSEDE"]:
        value += 2
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pool", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    with args.pool.open() as handle:
        rows = [json.loads(line) for line in handle]

    ranked = sorted(
        (row for row in rows if row["condition"] == "heterogeneous" and score(row) > 0),
        key=lambda row: (-score(row), row["pair_id"]),
    )

    selected = []
    per_persona = Counter()
    seen_sessions = set()
    for row in ranked:
        session_key = (row["persona_id"], row["session_id"])
        if session_key in seen_sessions or per_persona[row["persona_id"]] >= 3:
            continue
        proposed = dict(row)
        proposed["proposal_score"] = score(row)
        proposed["proposal_method"] = "lexical-recall-v1; not a validity label"
        selected.append(proposed)
        seen_sessions.add(session_key)
        per_persona[row["persona_id"]] += 1
        if len(selected) >= args.limit:
            break

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        for row in selected:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"selected": len(selected), "personas": len(per_persona)}, indent=2))


if __name__ == "__main__":
    main()
