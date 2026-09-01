"""Stage J-3: anchor-unit paired comparison.

For each anchor pair the same unit appears in a same-policy composite (A_SAME)
and a different-policy composite (A_DIFF). The paired outcome is the anchor's
verdict in each composite; the exact McNemar test over pairs asks whether the
partner's policy heterogeneity changes the anchor's success, with unit
difficulty held fixed by construction.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from composite_conflict.analyze_pilot2_stage_j_independence import (
    ORDERS,
    mcnemar_exact,
    rate,
    read_jsonl,
    unit_judgments,
)


def analyse(composites: list[dict[str, Any]], probes: list[dict[str, Any]], judgments: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts = unit_judgments(judgments)
    atomic = {}
    for probe in probes:
        uid = probe["unit_id"]
        atomic[uid] = verdicts.get(probe["instance_id"], {}).get(uid, False)

    pairs: dict[str, dict[str, Any]] = {}
    for row in composites:
        pair = pairs.setdefault(row["pair_id"], {"anchor_policy": row["policies"][0], "anchor": row["anchor_unit_id"], "same": {}, "diff": {}})
        tag = "same" if row["cell"] == "A_SAME" else "diff"
        v = verdicts.get(row["instance_id"], {})
        pair[tag][row["order_variant"]] = {
            "anchor": v.get(row["anchor_unit_id"], False),
            "partner": v.get(row["partner_unit_id"], False),
            "partner_unit": row["partner_unit_id"],
            "partner_policy": row["partner_policy"],
        }

    def summarise(subset: list[dict[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {"pairs": len(subset)}
        for name, agg in (("worst_order", all), ("best_order", any)):
            same = [agg(p["same"][o]["anchor"] for o in ORDERS) for p in subset]
            diff = [agg(p["diff"][o]["anchor"] for o in ORDERS) for p in subset]
            b = sum(1 for s, d in zip(same, diff) if s and not d)
            c = sum(1 for s, d in zip(same, diff) if d and not s)
            out[name] = {
                "anchor_in_same_policy_composite": rate(sum(same), len(subset)),
                "anchor_in_diff_policy_composite": rate(sum(diff), len(subset)),
                "same_ok_diff_fail": b,
                "diff_ok_same_fail": c,
                "mcnemar_exact_p": mcnemar_exact(b, c),
            }
        per_order = {}
        for o in ORDERS:
            same = [p["same"][o]["anchor"] for p in subset]
            diff = [p["diff"][o]["anchor"] for p in subset]
            b = sum(1 for s, d in zip(same, diff) if s and not d)
            c = sum(1 for s, d in zip(same, diff) if d and not s)
            per_order[o] = {"same": rate(sum(same), len(subset)), "diff": rate(sum(diff), len(subset)), "p": mcnemar_exact(b, c)}
        out["per_order"] = per_order
        # anchor atomic and partner accuracy for context
        out["anchor_atomic_accuracy"] = rate(sum(1 for p in subset if atomic.get(p["anchor"], False)), len(subset))
        out["partner_worst_order"] = {
            tag: rate(sum(1 for p in subset if all(p[tag][o]["partner"] for o in ORDERS)), len(subset))
            for tag in ("same", "diff")
        }
        out["partner_atomic_accuracy"] = {
            tag: rate(sum(1 for p in subset if atomic.get(p[tag]["original"]["partner_unit"], False)), len(subset))
            for tag in ("same", "diff")
        }
        return out

    report = {"ALL": summarise(list(pairs.values()))}
    by_policy = defaultdict(list)
    for p in pairs.values():
        by_policy[p["anchor_policy"]].append(p)
    for policy, subset in sorted(by_policy.items()):
        report[policy] = summarise(subset)
    # restricted to anchors solved alone
    solved = [p for p in pairs.values() if atomic.get(p["anchor"], False)]
    report["anchor_atomic_correct_only"] = summarise(solved) if solved else {"pairs": 0}
    by_partner = defaultdict(list)
    for p in pairs.values():
        by_partner[f"{p['anchor_policy']}->{p['diff']['original']['partner_policy']}"].append(p)
    report["by_anchor_and_diff_partner"] = {k: summarise(v) for k, v in sorted(by_partner.items())}
    return report


def markdown(report: dict[str, Any], label: str) -> str:
    lines = [f"### {label}", "", "| subset | pairs | anchor atomic | anchor in SAME (worst) | anchor in DIFF (worst) | same ok/diff fail | diff ok/same fail | p | SAME (best) | DIFF (best) | p |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    keys = ["ALL", "SUPERSEDE", "VERIFY_PREFER", "CONDITION", "anchor_atomic_correct_only"] + [f"by:{k}" for k in report["by_anchor_and_diff_partner"]]
    for key in keys:
        r = report["by_anchor_and_diff_partner"][key[3:]] if key.startswith("by:") else report[key]
        if not r.get("pairs"):
            continue
        w, b = r["worst_order"], r["best_order"]
        lines.append(
            f"| {key} | {r['pairs']} | {r['anchor_atomic_accuracy']['rate']:.2f} | {w['anchor_in_same_policy_composite']['rate']:.2f} | {w['anchor_in_diff_policy_composite']['rate']:.2f} | {w['same_ok_diff_fail']} | {w['diff_ok_same_fail']} | {w['mcnemar_exact_p']:.3g} | {b['anchor_in_same_policy_composite']['rate']:.2f} | {b['anchor_in_diff_policy_composite']['rate']:.2f} | {b['mcnemar_exact_p']:.3g} |"
        )
    lines += ["", "Per order (ALL): " + ", ".join(f"{o}: same {v['same']['rate']:.2f} / diff {v['diff']['rate']:.2f} (p={v['p']:.3g})" for o, v in report["ALL"]["per_order"].items())]
    lines += ["", "Partner worst-order accuracy (ALL): " + ", ".join(f"{t}: {v['rate']:.2f}" for t, v in report["ALL"]["partner_worst_order"].items()) + "; partner atomic: " + ", ".join(f"{t}: {v['rate']:.2f}" for t, v in report["ALL"]["partner_atomic_accuracy"].items())]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--composites", type=Path, required=True)
    parser.add_argument("--probes", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    report = analyse(read_jsonl(args.composites), read_jsonl(args.probes), read_jsonl(args.judgments))
    report["label"] = args.label
    args.out_dir.mkdir(parents=True, exist_ok=True)
    slug = args.label.replace("/", "_")
    (args.out_dir / f"{slug}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / f"{slug}.md").write_text(markdown(report, args.label), encoding="utf-8")
    print(markdown(report, args.label))


if __name__ == "__main__":
    main()
