"""Stage J-1: unit-level atomic-to-composite gap and independence null.

Joins Stage G atomic-probe judgments with composite judgments for the same
gold unit, and asks whether a unit that is solved alone is still solved when
it is embedded in a composite query.

Primary statistic: for each (base, unit) the atomic verdict versus the
worst-order composite verdict (correct in all three orders), tested with an
exact McNemar test. Order variants are repeated measures of the same base,
so the pooled per-order table is reported as descriptive only.

Independence null (2608.12426 style): if unit failures inside a composite were
independent and had the same rate as atomic failures, all-unit success would
equal the fraction of bases whose atomic probes are all correct. The observed
all-unit success is compared against that ceiling.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

ORDERS = ("original", "reverse", "interleaved")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (round(centre - half, 4), round(centre + half, 4))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact binomial test on the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2**n
    return round(min(1.0, 2 * tail), 6)


def rate(successes: int, n: int) -> dict[str, Any]:
    return {
        "n": n,
        "success": successes,
        "rate": round(successes / n, 4) if n else None,
        "wilson95": wilson(successes, n),
    }


def unit_judgments(rows: list[dict[str, Any]]) -> dict[str, dict[str, bool]]:
    """instance_id -> {unit_id: correct}."""
    out: dict[str, dict[str, bool]] = {}
    for row in rows:
        judgment = row.get("judgment") or {}
        units = {
            item["unit_id"]: bool(item.get("correct"))
            for item in judgment.get("unit_results", [])
        }
        out[row["instance_id"]] = units
    return out


def paired_table(pairs: list[tuple[bool, bool]]) -> dict[str, Any]:
    """pairs of (atomic_correct, composite_correct)."""
    a = sum(1 for x, y in pairs if x and y)
    b = sum(1 for x, y in pairs if x and not y)
    c = sum(1 for x, y in pairs if not x and y)
    d = sum(1 for x, y in pairs if not x and not y)
    n = len(pairs)
    atomic = a + b
    composite = a + c
    return {
        "n": n,
        "both_correct": a,
        "atomic_only": b,
        "composite_only": c,
        "both_wrong": d,
        "atomic_accuracy": rate(atomic, n),
        "in_composite_accuracy": rate(composite, n),
        "gap": round((atomic - composite) / n, 4) if n else None,
        "mcnemar_exact_p": mcnemar_exact(b, c),
        "retained_given_atomic_correct": rate(a, atomic),
    }


def bootstrap_gap(
    by_base: dict[str, list[tuple[bool, bool]]], seed: int, draws: int = 2000
) -> dict[str, Any]:
    """Cluster bootstrap over bases for the worst-order unit-level gap."""
    bases = sorted(by_base)
    if not bases:
        return {"draws": 0}
    rng = random.Random(seed)
    gaps = []
    for _ in range(draws):
        sample = [by_base[rng.choice(bases)] for _ in bases]
        flat = [pair for group in sample for pair in group]
        atomic = sum(1 for x, _ in flat if x)
        comp = sum(1 for _, y in flat if y)
        gaps.append((atomic - comp) / len(flat))
    gaps.sort()
    return {
        "draws": draws,
        "gap_ci95": (round(gaps[int(0.025 * draws)], 4), round(gaps[int(0.975 * draws) - 1], 4)),
    }


def analyse(
    composites: list[dict[str, Any]],
    probes: list[dict[str, Any]],
    judgments: list[dict[str, Any]],
    seed: int,
) -> dict[str, Any]:
    verdicts = unit_judgments(judgments)
    probe_by_id = {row["instance_id"]: row for row in probes}
    bases: dict[str, dict[str, Any]] = {}
    for row in composites:
        base = bases.setdefault(
            row["base_instance_id"],
            {
                "cell": row.get("cell") or f"K{row['K']}_H{row['H']}",
                "condition": row["condition"],
                "units": {u["unit_id"]: u["policy"] for u in row["gold_units"]},
                "composite": {},
            },
        )
        base["composite"][row["order_variant"]] = verdicts.get(row["instance_id"], {})

    atomic_by_base_unit: dict[tuple[str, str], bool] = {}
    for probe in probes:
        unit_id = probe["gold_units"][0]["unit_id"]
        verdict = verdicts.get(probe["instance_id"], {})
        atomic_by_base_unit[(probe["base_instance_id"], unit_id)] = verdict.get(unit_id, False)
    missing = [key for key in atomic_by_base_unit if key[0] not in bases]
    assert not missing, f"probes without composite base: {missing[:3]}"

    groups: dict[str, dict[str, list[tuple[bool, bool]]]] = defaultdict(lambda: defaultdict(list))
    groups_pooled: dict[str, dict[str, list[tuple[bool, bool]]]] = defaultdict(lambda: defaultdict(list))
    by_base_worst: dict[str, dict[str, list[tuple[bool, bool]]]] = defaultdict(lambda: defaultdict(list))
    policy_groups: dict[str, dict[str, list[tuple[bool, bool]]]] = defaultdict(lambda: defaultdict(list))
    null_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for base_id, base in bases.items():
        cell = base["cell"]
        het = {"heterogeneous": "heterogeneous", "homogeneous": "homogeneous"}.get(base["condition"], base["condition"])
        all_atomic = True
        for unit_id, policy in base["units"].items():
            atomic = atomic_by_base_unit.get((base_id, unit_id), False)
            all_atomic &= atomic
            per_order = [base["composite"].get(order, {}).get(unit_id, False) for order in ORDERS]
            worst = all(per_order)
            pair = (atomic, worst)
            for key in ("ALL", cell, cell.split("_")[0], het):
                groups[key]["worst"].append(pair)
                for order, value in zip(ORDERS, per_order):
                    groups_pooled[key][order].append((atomic, value))
            by_base_worst["ALL"][base_id].append(pair)
            by_base_worst[cell][base_id].append(pair)
            policy_groups[policy][het].append(pair)
            policy_groups[policy]["ALL"].append(pair)
        per_order_all = [
            all(base["composite"].get(order, {}).get(u, False) for u in base["units"])
            for order in ORDERS
        ]
        null_rows[cell].append({"all_atomic": all_atomic, "per_order": per_order_all})
        null_rows["ALL"].append({"all_atomic": all_atomic, "per_order": per_order_all})

    def null_block(rows: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(rows)
        all_atomic = sum(1 for r in rows if r["all_atomic"])
        observed_worst = sum(1 for r in rows if all(r["per_order"]))
        observed_best = sum(1 for r in rows if any(r["per_order"]))
        observed_pooled = sum(sum(r["per_order"]) for r in rows)
        eligible = [r for r in rows if r["all_atomic"]]
        return {
            "bases": n,
            "independence_ceiling_all_atomic_correct": rate(all_atomic, n),
            "observed_all_unit_success_worst_order": rate(observed_worst, n),
            "observed_all_unit_success_best_order": rate(observed_best, n),
            "observed_all_unit_success_pooled_orders": rate(observed_pooled, 3 * n),
            "shortfall_worst_vs_ceiling": round((all_atomic - observed_worst) / n, 4) if n else None,
            "given_all_atomic_correct": {
                "bases": len(eligible),
                "composite_success_all_orders": rate(sum(1 for r in eligible if all(r["per_order"])), len(eligible)),
                "composite_success_pooled_orders": rate(sum(sum(r["per_order"]) for r in eligible), 3 * len(eligible)),
            },
        }

    report: dict[str, Any] = {"unit_level": {}, "independence_null": {}, "by_policy": {}}
    for key in sorted(groups):
        block = {"worst_order": paired_table(groups[key]["worst"])}
        block["per_order_descriptive"] = {
            order: paired_table(groups_pooled[key][order]) for order in ORDERS
        }
        if key in by_base_worst:
            block["worst_order"]["cluster_bootstrap"] = bootstrap_gap(by_base_worst[key], seed)
        report["unit_level"][key] = block
    for key in sorted(null_rows):
        report["independence_null"][key] = null_block(null_rows[key])
    for policy in sorted(policy_groups):
        report["by_policy"][policy] = {
            subset: paired_table(pairs) for subset, pairs in sorted(policy_groups[policy].items())
        }
    return report


def markdown(report: dict[str, Any], label: str) -> str:
    lines = [f"### {label}", "", "Unit-level (worst-order composite vs atomic)", "",
             "| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |",
             "|---|---:|---:|---:|---:|---:|---:|---|"]
    fixed = ["ALL", "K2", "K3", "homogeneous", "heterogeneous", "no_conflict"]
    order = [k for k in fixed if k in report["unit_level"]] + sorted(
        k for k in report["unit_level"] if k not in fixed
    )
    for key in order:
        w = report["unit_level"][key]["worst_order"]
        ci = w.get("cluster_bootstrap", {}).get("gap_ci95", ("", ""))
        lines.append(
            f"| {key} | {w['n']} | {w['atomic_accuracy']['rate']:.3f} | {w['in_composite_accuracy']['rate']:.3f} | "
            f"{w['gap']:+.3f} | {w['retained_given_atomic_correct']['rate']:.3f} | {w['mcnemar_exact_p']:.2g} | {ci[0]}–{ci[1]} |"
        )
    lines += ["", "Independence null (base level)", "",
              "| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for key in ["ALL"] + sorted(k for k in report["independence_null"] if k != "ALL"):
        b = report["independence_null"][key]
        g = b["given_all_atomic_correct"]
        lines.append(
            f"| {key} | {b['bases']} | {b['independence_ceiling_all_atomic_correct']['rate']:.3f} | "
            f"{b['observed_all_unit_success_worst_order']['rate']:.3f} | {b['observed_all_unit_success_best_order']['rate']:.3f} | "
            f"{b['shortfall_worst_vs_ceiling']:+.3f} | {g['composite_success_all_orders']['success']}/{g['bases']} |"
        )
    lines += ["", "By unit policy (worst-order), homogeneous vs heterogeneous partner", "",
              "| policy | subset | n | atomic | in-composite | gap | retained | p |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for policy, subsets in report["by_policy"].items():
        for subset in ("ALL", "homogeneous", "heterogeneous", "no_conflict"):
            t = subsets.get(subset)
            if not t:
                continue
            lines.append(
                f"| {policy} | {subset} | {t['n']} | {t['atomic_accuracy']['rate']:.3f} | {t['in_composite_accuracy']['rate']:.3f} | "
                f"{t['gap']:+.3f} | {t['retained_given_atomic_correct']['rate']:.3f} | {t['mcnemar_exact_p']:.2g} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--composites", type=Path, required=True)
    parser.add_argument("--probes", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260828)
    args = parser.parse_args()

    report = analyse(
        read_jsonl(args.composites), read_jsonl(args.probes), read_jsonl(args.judgments), args.seed
    )
    report["label"] = args.label
    args.out_dir.mkdir(parents=True, exist_ok=True)
    slug = args.label.replace("/", "_").replace(" ", "_")
    (args.out_dir / f"{slug}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / f"{slug}.md").write_text(markdown(report, args.label), encoding="utf-8")
    print(markdown(report, args.label))


if __name__ == "__main__":
    main()
