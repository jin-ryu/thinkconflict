"""Stage I-2: anchor-unit paired design.

For an anchor unit a with policy P, build two K=2 composites that share a:
  same-policy partner  a + b   (b.policy == P)
  diff-policy partner  a + c   (c.policy != P)
with b and c matched on record count (diff <= 1) and context length
(diff <= 10%). Anchors that Stage G atomic probes solved in at least two of
three generation models are preferred, so that anchor failures inside a
composite cannot be attributed to the anchor being unsolvable alone.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from composite_conflict.prepare_pilot2_stage_g import (
    POLICIES,
    build_atomic_candidates,
    combined_query,
    ordered_context,
    read_jsonl,
    write_jsonl,
)


def context_tokens(unit: dict[str, Any]) -> int:
    return len(json.dumps(unit["memory_context"], ensure_ascii=False)) // 4


def stage_g_atomic_ok(probes_path: Path, judgment_paths: list[Path]) -> dict[str, int]:
    probes = {row["instance_id"]: row["gold_units"][0]["unit_id"] for row in read_jsonl(probes_path)}
    ok: dict[str, int] = defaultdict(int)
    for path in judgment_paths:
        for row in read_jsonl(path):
            unit_id = probes.get(row["instance_id"])
            if unit_id is None:
                continue
            results = (row.get("judgment") or {}).get("unit_results") or []
            if results and results[0].get("correct"):
                ok[unit_id] += 1
    return dict(ok)


def matched_partners(
    anchor: dict[str, Any],
    same_pool: list[dict[str, Any]],
    diff_pools: dict[str, list[dict[str, Any]]],
    preferred_policy: str,
) -> tuple[dict[str, Any], dict[str, Any], str] | None:
    best = None
    for b in same_pool:
        if b is anchor or b["gold_unit"]["target_attribute"] == anchor["gold_unit"]["target_attribute"]:
            continue
        for policy in [preferred_policy] + [p for p in diff_pools if p != preferred_policy]:
            for c in diff_pools[policy]:
                rec_diff = abs(len(b["memory_context"]) - len(c["memory_context"]))
                if rec_diff > 1:
                    continue
                tb, tc = context_tokens(b), context_tokens(c)
                tok_diff = abs(tb - tc) / max(tb, tc)
                if tok_diff > 0.10:
                    continue
                score = (0 if policy == preferred_policy else 1, rec_diff, tok_diff)
                if best is None or score < best[0]:
                    best = (score, b, c, policy)
    if best is None:
        return None
    return best[1], best[2], best[3]


def base_row(pair_id: str, variant_tag: str, person: dict[str, Any], anchor: dict[str, Any], partner: dict[str, Any], anchor_policy: str) -> dict[str, Any]:
    units = [anchor, partner]
    policies = [anchor_policy, partner["gold_unit"]["policy"]]
    return {
        "base_instance_id": f"{pair_id}:{variant_tag}",
        "pair_id": pair_id,
        "persona_id": person["ID"],
        "persona_name": person["Fixed_Profile"].get("Name"),
        "target_date": max(u["target_date"] for u in units),
        "condition": f"anchor_{variant_tag}",
        "cell": "A_SAME" if variant_tag == "same" else "A_DIFF",
        "K": 2,
        "H": len(set(policies)),
        "policies": policies,
        "policy_multiset": "+".join(sorted(policies)),
        "anchor_unit_id": anchor["gold_unit"]["unit_id"],
        "partner_unit_id": partner["gold_unit"]["unit_id"],
        "partner_policy": partner["gold_unit"]["policy"],
        "query": combined_query(units),
        "gold_units": [dict(anchor["gold_unit"]), dict(partner["gold_unit"])],
        "_units": units,
        "construction": {
            "source": "MemConflict Data/Step4_4.jsonl",
            "layer": "anchor_unit_pair",
            "matching": "partner record count diff <= 1, context tokens diff <= 10%",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--stage-g-probes", type=Path, required=True)
    parser.add_argument("--stage-g-judgments", type=Path, nargs="+", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--per-policy", type=int, default=20)
    parser.add_argument("--max-per-persona", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260828)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    people = read_jsonl(args.raw)
    people_by_id = {p["ID"]: p for p in people}
    candidates, _ = build_atomic_candidates(people)
    atomic_ok = stage_g_atomic_ok(args.stage_g_probes, args.stage_g_judgments)

    bases: list[dict[str, Any]] = []
    per_persona = Counter()
    covariates = []
    skipped = Counter()
    for policy in POLICIES:
        others = [p for p in POLICIES if p != policy]
        anchors_pool = [
            (pid, unit)
            for pid, pools in candidates.items()
            for unit in pools.get(policy, [])
        ]
        # prefer anchors verified solvable alone in >=2 Stage G generation models
        def priority(item: tuple[str, dict[str, Any]]) -> tuple[int, float]:
            return (-min(atomic_ok.get(item[1]["gold_unit"]["unit_id"], 0), 2), rng.random())
        anchors_pool.sort(key=priority)
        count = 0
        for pid, anchor in anchors_pool:
            if count >= args.per_policy:
                break
            if per_persona[pid] >= args.max_per_persona:
                skipped["persona_cap"] += 1
                continue
            pools = candidates[pid]
            preferred = others[count % 2]
            match = matched_partners(anchor, pools.get(policy, []), {p: pools.get(p, []) for p in others}, preferred)
            if match is None:
                skipped["no_matched_partner"] += 1
                continue
            b, c, c_policy = match
            pair_id = f"stagei:anchor:{policy.lower()}:{count + 1:03d}:{pid[:8]}"
            person = people_by_id[pid]
            bases.append(base_row(pair_id, "same", person, anchor, b, policy))
            bases.append(base_row(pair_id, "diff", person, anchor, c, policy))
            covariates.append({
                "pair_id": pair_id,
                "anchor_policy": policy,
                "anchor_unit_id": anchor["gold_unit"]["unit_id"],
                "anchor_stage_g_atomic_ok_models": atomic_ok.get(anchor["gold_unit"]["unit_id"], None),
                "same_partner_records": len(b["memory_context"]),
                "diff_partner_records": len(c["memory_context"]),
                "same_partner_tokens": context_tokens(b),
                "diff_partner_tokens": context_tokens(c),
                "diff_partner_policy": c_policy,
            })
            per_persona[pid] += 1
            count += 1
        if count < args.per_policy:
            raise RuntimeError(f"only {count} anchors for {policy}; skipped={dict(skipped)}")

    composites = []
    for base in bases:
        for variant in ("original", "reverse", "interleaved"):
            row = {k: v for k, v in base.items() if not k.startswith("_")}
            row["instance_id"] = f"{base['base_instance_id']}:{variant}"
            row["order_variant"] = variant
            row["memory_context"] = ordered_context(base["_units"], variant)
            composites.append(row)

    probes: dict[str, dict[str, Any]] = {}
    for base in bases:
        for role, unit in zip(("anchor", "partner"), base["_units"]):
            uid = unit["gold_unit"]["unit_id"]
            if uid in probes:
                probes[uid]["base_instance_ids"].append(base["base_instance_id"])
                continue
            probes[uid] = {
                "instance_id": f"stagei:anchor:atomic:{uid}",
                "base_instance_id": base["pair_id"],
                "base_instance_ids": [base["base_instance_id"]],
                "unit_id": uid,
                "role": role,
                "parent_cell": "ANCHOR",
                "persona_id": base["persona_id"],
                "persona_name": base["persona_name"],
                "target_date": unit["target_date"],
                "condition": "atomic_control",
                "cell": "K1_A",
                "K": 1,
                "H": 1,
                "policies": [unit["gold_unit"]["policy"]],
                "policy_multiset": unit["gold_unit"]["policy"],
                "query": combined_query([unit]),
                "memory_context": ordered_context([unit], "original"),
                "gold_units": [dict(unit["gold_unit"])],
                "construction": {"layer": "paired_atomic_control"},
            }

    errors = []
    for row in composites:
        ids = {r["memory_id"] for r in row["memory_context"]}
        if len(ids) != len(row["memory_context"]):
            errors.append(f"{row['instance_id']}: duplicate memory ids")
        for unit in row["gold_units"]:
            if not set(unit["evidence_ids"]).issubset(ids):
                errors.append(f"{row['instance_id']}: missing evidence")
        expected_h = 1 if row["cell"] == "A_SAME" else 2
        if row["H"] != expected_h:
            errors.append(f"{row['instance_id']}: H mismatch")
    report = {
        "valid": not errors,
        "errors": errors,
        "pairs": len(covariates),
        "bases": len(bases),
        "composite_order_variants": len(composites),
        "atomic_probes": len(probes),
        "anchors_by_policy": dict(Counter(c["anchor_policy"] for c in covariates)),
        "diff_partner_policy": dict(Counter((c["anchor_policy"], c["diff_partner_policy"]) and f"{c['anchor_policy']}->{c['diff_partner_policy']}" for c in covariates)),
        "anchor_stage_g_ok_models": dict(Counter(str(c["anchor_stage_g_atomic_ok_models"]) for c in covariates)),
        "personas": len({b["persona_id"] for b in bases}),
        "skipped": dict(skipped),
        "seed": args.seed,
    }
    if errors:
        raise ValueError(json.dumps(report, ensure_ascii=False, indent=2))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "composite_order_variants.jsonl", composites)
    write_jsonl(args.out_dir / "atomic_probes.jsonl", list(probes.values()))
    write_jsonl(args.out_dir / "matching_covariates.jsonl", covariates)
    (args.out_dir / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
