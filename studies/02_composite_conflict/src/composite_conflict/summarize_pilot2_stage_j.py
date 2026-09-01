"""Collect Stage J analysis JSONs into one cross-model markdown table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results/pilot2_memory"))
    parser.add_argument("--labels", nargs="+", required=True, help="analysis labels, e.g. qwen3_8b_gen__llama3_1_70b_judge__v4_unit_isolated")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    lines = ["| generation / judge | conflict gap (worst) | conflict gap (orig) | C0 gap (worst) | C0 gap (orig) | excess K2 (worst) [CI] | excess K3 (worst) [CI] | anchor SAME / DIFF (worst, p) | anchor SAME / DIFF (best, p) |", "|---|---:|---:|---:|---:|---|---|---|---|"]
    for label in args.labels:
        ind = load(args.results / "stage_j_independence" / f"{label}.json")
        ctrl = load(args.results / "stage_j_controls" / "analysis" / f"{label}.json")
        exc = load(args.results / "stage_j_controls" / "excess" / f"{label}.json")
        anc = load(args.results / "stage_j_anchor" / "analysis" / f"{label}.json")
        def g(rep, key):
            return f"{rep['unit_level']['ALL']['worst_order']['gap']:+.2f}" if rep else "-"
        def go(rep):
            return f"{rep['unit_level']['ALL']['per_order_descriptive']['original']['gap']:+.2f}" if rep else "-"
        def ex(name):
            if not exc or name not in exc["comparisons"]:
                return "-"
            w = exc["comparisons"][name]["worst"]
            return f"{w['excess']:+.2f} [{w['ci95'][0]:+.2f}, {w['ci95'][1]:+.2f}]"
        def an(kind):
            if not anc:
                return "-"
            r = anc["ALL"][kind]
            return f"{r['anchor_in_same_policy_composite']['rate']:.2f} / {r['anchor_in_diff_policy_composite']['rate']:.2f} (p={r['mcnemar_exact_p']:.2g})"
        short = label.replace("_gen__", " / ").replace("_judge__v4_unit_isolated", "")
        lines.append(f"| {short} | {g(ind,'w')} | {go(ind)} | {g(ctrl,'w')} | {go(ctrl)} | {ex('K2_all_conflict_vs_K2_C0')} | {ex('K3_all_conflict_vs_K3_C0')} | {an('worst_order')} | {an('best_order')} |")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
