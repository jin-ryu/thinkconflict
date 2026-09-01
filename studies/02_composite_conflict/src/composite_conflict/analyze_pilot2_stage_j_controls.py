"""Stage J-2: conflict-specific excess = gap(conflict cells) - gap(no-conflict controls).

Unit-level gap = atomic accuracy - in-composite accuracy. Conflict cells and
control cells are independent sets of bases, so the difference in gaps gets a
two-sample cluster bootstrap over bases (2,000 draws), reported for the
worst-order criterion and for each evidence order separately.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from composite_conflict.analyze_pilot2_stage_j_independence import ORDERS, read_jsonl, unit_judgments


def unit_pairs(composites, probes, judgments) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """cell -> base -> list of {atomic, worst, per_order{...}} per unit."""
    verdicts = unit_judgments(judgments)
    by_base: dict[str, dict[str, Any]] = {}
    for row in composites:
        b = by_base.setdefault(row["base_instance_id"], {"cell": row.get("cell") or f"K{row['K']}_H{row['H']}", "K": int(row["K"]), "units": [u["unit_id"] for u in row["gold_units"]], "orders": {}})
        b["orders"][row["order_variant"]] = verdicts.get(row["instance_id"], {})
    atomic = {}
    for p in probes:
        uid = p["gold_units"][0]["unit_id"]
        atomic[(p["base_instance_id"], uid)] = verdicts.get(p["instance_id"], {}).get(uid, False)
    out: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for base_id, b in by_base.items():
        for uid in b["units"]:
            per_order = {o: b["orders"].get(o, {}).get(uid, False) for o in ORDERS}
            out[b["cell"]][base_id].append({"atomic": atomic.get((base_id, uid), False), "worst": all(per_order.values()), "per_order": per_order})
    return out


def gap(units: list[dict[str, Any]], key: str) -> float:
    if not units:
        return 0.0
    a = sum(u["atomic"] for u in units)
    c = sum(u["worst"] if key == "worst" else u["per_order"][key] for u in units)
    return (a - c) / len(units)


def bootstrap_diff(conf: dict[str, list], ctrl: dict[str, list], key: str, rng: random.Random, draws: int = 2000) -> tuple[float, tuple[float, float]]:
    cb, kb = sorted(conf), sorted(ctrl)
    point = gap([u for b in cb for u in conf[b]], key) - gap([u for b in kb for u in ctrl[b]], key)
    diffs = []
    for _ in range(draws):
        cs = [u for _ in cb for u in conf[rng.choice(cb)]]
        ks = [u for _ in kb for u in ctrl[rng.choice(kb)]]
        diffs.append(gap(cs, key) - gap(ks, key))
    diffs.sort()
    return round(point, 4), (round(diffs[int(0.025 * draws)], 4), round(diffs[int(0.975 * draws) - 1], 4))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conflict-composites", type=Path, required=True)
    parser.add_argument("--conflict-probes", type=Path, required=True)
    parser.add_argument("--conflict-judgments", type=Path, required=True)
    parser.add_argument("--control-composites", type=Path, required=True)
    parser.add_argument("--control-probes", type=Path, required=True)
    parser.add_argument("--control-judgments", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260828)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    conf = unit_pairs(read_jsonl(args.conflict_composites), read_jsonl(args.conflict_probes), read_jsonl(args.conflict_judgments))
    ctrl = unit_pairs(read_jsonl(args.control_composites), read_jsonl(args.control_probes), read_jsonl(args.control_judgments))
    comparisons = {
        "K2_all_conflict_vs_K2_C0": (["K2_H1", "K2_H2"], "K2_C0"),
        "K2_H1_vs_K2_C0": (["K2_H1"], "K2_C0"),
        "K2_H2_vs_K2_C0": (["K2_H2"], "K2_C0"),
        "K3_all_conflict_vs_K3_C0": (["K3_H1", "K3_H2", "K3_H3"], "K3_C0"),
        "K3_H1_vs_K3_C0": (["K3_H1"], "K3_C0"),
        "K3_H2_vs_K3_C0": (["K3_H2"], "K3_C0"),
        "K3_H3_vs_K3_C0": (["K3_H3"], "K3_C0"),
        "K2_H2_vs_K2_H1": (["K2_H2"], "K2_H1"),
        "K3_H3_vs_K3_H1": (["K3_H3"], "K3_H1"),
    }
    report: dict[str, Any] = {"label": args.label, "comparisons": {}}
    lines = [f"### {args.label}", "", "| comparison | gap conflict | gap control | excess (worst) | CI95 | excess original | excess reverse | excess interleaved |", "|---|---:|---:|---:|---|---:|---:|---:|"]
    for name, (conf_cells, ctrl_cell) in comparisons.items():
        a = {b: u for c in conf_cells for b, u in conf.get(c, {}).items()}
        k = dict(conf.get(ctrl_cell, {})) if ctrl_cell in conf else dict(ctrl.get(ctrl_cell, {}))
        if not a or not k:
            continue
        row = {}
        for key in ("worst",) + ORDERS:
            point, ci = bootstrap_diff(a, k, key, rng)
            row[key] = {"excess": point, "ci95": ci, "gap_conflict": round(gap([u for b in a for u in a[b]], key), 4), "gap_control": round(gap([u for b in k for u in k[b]], key), 4)}
        report["comparisons"][name] = row
        w = row["worst"]
        lines.append(f"| {name} | {w['gap_conflict']:+.3f} | {w['gap_control']:+.3f} | {w['excess']:+.3f} | {w['ci95'][0]}–{w['ci95'][1]} | " + " | ".join(f"{row[o]['excess']:+.3f}" for o in ORDERS) + " |")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    slug = args.label
    (args.out_dir / f"{slug}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / f"{slug}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
