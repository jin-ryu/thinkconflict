"""Compare two judge protocols (e.g. v3_evidence vs v4_unit_isolated) on the same outputs.

Reports unit-level agreement, Cohen's kappa, and the atomic-to-composite gap
under each protocol, so that a protocol change can be audited rather than
silently adopted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from composite_conflict.analyze_pilot2_stage_j_independence import analyse, read_jsonl, unit_judgments


def kappa(pairs: list[tuple[bool, bool]]) -> float | None:
    n = len(pairs)
    if not n:
        return None
    agree = sum(1 for a, b in pairs if a == b) / n
    pa = sum(1 for a, _ in pairs if a) / n
    pb = sum(1 for _, b in pairs if b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return round((agree - expected) / (1 - expected), 4) if expected < 1 else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--composites", type=Path, required=True)
    parser.add_argument("--probes", type=Path, required=True)
    parser.add_argument("--judgments-a", type=Path, required=True)
    parser.add_argument("--judgments-b", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    composites, probes = read_jsonl(args.composites), read_jsonl(args.probes)
    ja, jb = read_jsonl(args.judgments_a), read_jsonl(args.judgments_b)
    va, vb = unit_judgments(ja), unit_judgments(jb)
    probe_ids = {row["instance_id"] for row in probes}
    pairs = {"atomic": [], "composite": []}
    for instance_id, units in va.items():
        if instance_id not in vb:
            continue
        kind = "atomic" if instance_id in probe_ids else "composite"
        for unit_id, verdict in units.items():
            if unit_id in vb[instance_id]:
                pairs[kind].append((verdict, vb[instance_id][unit_id]))
    report: dict[str, Any] = {"label": args.label}
    for kind, items in pairs.items():
        n = len(items)
        report[kind] = {
            "n": n,
            "agreement": round(sum(1 for a, b in items if a == b) / n, 4) if n else None,
            "kappa": kappa(items),
            "a_true_b_false": sum(1 for a, b in items if a and not b),
            "a_false_b_true": sum(1 for a, b in items if b and not a),
            "accuracy_a": round(sum(1 for a, _ in items if a) / n, 4) if n else None,
            "accuracy_b": round(sum(1 for _, b in items if b) / n, 4) if n else None,
        }
    ra, rb = analyse(composites, probes, ja, 0), analyse(composites, probes, jb, 0)
    report["gap_worst_order"] = {
        "a": ra["unit_level"]["ALL"]["worst_order"]["gap"],
        "b": rb["unit_level"]["ALL"]["worst_order"]["gap"],
    }
    report["gap_per_order"] = {
        order: {
            "a": ra["unit_level"]["ALL"]["per_order_descriptive"][order]["gap"],
            "b": rb["unit_level"]["ALL"]["per_order_descriptive"][order]["gap"],
        }
        for order in ("original", "reverse", "interleaved")
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
