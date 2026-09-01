"""Build the source-grounded K/H factorial set for Pilot 2 Stage G."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from composite_conflict.build_pilot2_instances import (
    conditional_evidence,
    dynamic_evidence,
    static_evidence,
)


POLICY_BY_TYPE = {
    "dynamic_conflict": "SUPERSEDE",
    "static_conflict": "VERIFY_PREFER",
    "conditional_conflict": "CONDITION",
}
POLICIES = ("SUPERSEDE", "VERIFY_PREFER", "CONDITION")
CELL_PATTERNS = {
    "K2_H1": (
        ("SUPERSEDE", "SUPERSEDE"),
        ("VERIFY_PREFER", "VERIFY_PREFER"),
        ("CONDITION", "CONDITION"),
    ),
    "K2_H2": (
        ("SUPERSEDE", "VERIFY_PREFER"),
        ("SUPERSEDE", "CONDITION"),
        ("VERIFY_PREFER", "CONDITION"),
    ),
    "K3_H1": (
        ("SUPERSEDE",) * 3,
        ("VERIFY_PREFER",) * 3,
        ("CONDITION",) * 3,
    ),
    "K3_H2": (
        ("SUPERSEDE", "SUPERSEDE", "VERIFY_PREFER"),
        ("SUPERSEDE", "VERIFY_PREFER", "VERIFY_PREFER"),
        ("SUPERSEDE", "SUPERSEDE", "CONDITION"),
        ("SUPERSEDE", "CONDITION", "CONDITION"),
        ("VERIFY_PREFER", "VERIFY_PREFER", "CONDITION"),
        ("VERIFY_PREFER", "CONDITION", "CONDITION"),
    ),
    "K3_H3": (POLICIES,),
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_atomic_candidates(
    people: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, list[dict[str, Any]]]], list[dict[str, str]]]:
    by_persona: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    errors: list[dict[str, str]] = []
    builders = {
        "SUPERSEDE": dynamic_evidence,
        "VERIFY_PREFER": static_evidence,
        "CONDITION": conditional_evidence,
    }

    for person in people:
        persona_id = person["ID"]
        seen: set[tuple[str, str]] = set()
        for session in person["Full_Session_Chain"]:
            for question in session.get("Session_Questions", []):
                policy = POLICY_BY_TYPE.get(question.get("conflict_type"))
                if not policy:
                    continue
                enriched = dict(question)
                enriched.update({
                    "question_uid": (
                        f"{persona_id}:S{session['Session_ID']}:{question['question_id']}"
                    ),
                    "persona_id": persona_id,
                })
                try:
                    records, unit = builders[policy](person, session, enriched)
                except (KeyError, ValueError) as exc:
                    errors.append({
                        "question_uid": enriched["question_uid"],
                        "policy": policy,
                        "error": str(exc),
                    })
                    continue

                key = (policy, str(unit["target_attribute"]))
                if key in seen:
                    continue
                seen.add(key)
                unit["unit_id"] = enriched["question_uid"]
                unit["atomic_question"] = question["question"]
                unit["unit_target_date"] = session["Date"]
                by_persona[persona_id][policy].append({
                    "question_uid": enriched["question_uid"],
                    "question": question["question"],
                    "target_date": session["Date"],
                    "session_id": session["Session_ID"],
                    "memory_context": records,
                    "gold_unit": unit,
                })

    return by_persona, errors


def required_counts(pattern: tuple[str, ...]) -> Counter[str]:
    return Counter(pattern)


def eligible_personas(
    by_persona: dict[str, dict[str, list[dict[str, Any]]]],
    pattern: tuple[str, ...],
) -> list[str]:
    required = required_counts(pattern)
    return sorted(
        persona
        for persona, pools in by_persona.items()
        if all(len(pools.get(policy, [])) >= count for policy, count in required.items())
    )


def select_units(
    pools: dict[str, list[dict[str, Any]]],
    pattern: tuple[str, ...],
    rng: random.Random,
) -> list[dict[str, Any]]:
    selected_by_policy: dict[str, list[dict[str, Any]]] = {}
    for policy, count in required_counts(pattern).items():
        selected_by_policy[policy] = rng.sample(pools[policy], count)

    offsets: Counter[str] = Counter()
    selected = []
    for policy in pattern:
        selected.append(selected_by_policy[policy][offsets[policy]])
        offsets[policy] += 1
    return selected


def combined_query(units: list[dict[str, Any]]) -> str:
    lines = [
        "Using only the dated memory records, prepare one concise profile response "
        "that answers every item below. Interpret each item using the records "
        "available by its stated date."
    ]
    for index, unit in enumerate(units, start=1):
        lines.append(f"{index}. As of {unit['target_date']}: {unit['question']}")
    return "\n".join(lines)


def ordered_context(
    units: list[dict[str, Any]], variant: str
) -> list[dict[str, Any]]:
    def temporal_key(record: dict[str, Any]) -> tuple[str, int, str]:
        observed = str(record["observed_at"])
        if observed.startswith("before "):
            return observed.removeprefix("before "), 0, record["memory_id"]
        return observed, 1, record["memory_id"]

    groups = [
        sorted(unit["memory_context"], key=temporal_key)
        for unit in units
    ]
    if variant == "original":
        return [record for group in groups for record in group]
    if variant == "reverse":
        return list(reversed([record for group in groups for record in group]))
    if variant == "interleaved":
        result = []
        for index in range(max(len(group) for group in groups)):
            result.extend(group[index] for group in groups if index < len(group))
        return result
    raise ValueError(f"Unknown order variant: {variant}")


def build_base(
    cell: str,
    cell_index: int,
    persona: dict[str, Any],
    pattern: tuple[str, ...],
    units: list[dict[str, Any]],
) -> dict[str, Any]:
    base_id = f"stageg:{cell.lower()}:{cell_index:03d}:{persona['ID'][:8]}"
    gold_units = [dict(unit["gold_unit"]) for unit in units]
    return {
        "base_instance_id": base_id,
        "persona_id": persona["ID"],
        "persona_name": persona["Fixed_Profile"].get("Name"),
        "target_date": max(unit["target_date"] for unit in units),
        "condition": "homogeneous" if len(set(pattern)) == 1 else "heterogeneous",
        "K": len(pattern),
        "H": len(set(pattern)),
        "policies": list(pattern),
        "policy_multiset": "+".join(sorted(pattern)),
        "query": combined_query(units),
        "gold_units": gold_units,
        "_selected_units": units,
        "construction": {
            "source": "MemConflict Data/Step4_4.jsonl",
            "layer": "controlled_cross_session_composition",
            "source_grounding": (
                "all atomic facts, dates, conflicts, answers, and evidence are unchanged; "
                "only the compound query and evidence order are constructed"
            ),
        },
    }


def expand_orders(base: dict[str, Any]) -> list[dict[str, Any]]:
    units = base["_selected_units"]
    rows = []
    for variant in ("original", "reverse", "interleaved"):
        row = {key: value for key, value in base.items() if key != "_selected_units"}
        row["instance_id"] = f"{base['base_instance_id']}:{variant}"
        row["order_variant"] = variant
        row["memory_context"] = ordered_context(units, variant)
        rows.append(row)
    return rows


def atomic_probes(base: dict[str, Any]) -> list[dict[str, Any]]:
    probes = []
    for index, unit in enumerate(base["_selected_units"], start=1):
        gold = dict(unit["gold_unit"])
        probes.append({
            "instance_id": f"{base['base_instance_id']}:atomic:{index}",
            "base_instance_id": base["base_instance_id"],
            "parent_cell": f"K{base['K']}_H{base['H']}",
            "persona_id": base["persona_id"],
            "persona_name": base["persona_name"],
            "target_date": unit["target_date"],
            "condition": "atomic_control",
            "K": 1,
            "H": 1,
            "policies": [gold["policy"]],
            "policy_multiset": gold["policy"],
            "query": combined_query([unit]),
            "memory_context": ordered_context([unit], "original"),
            "gold_units": [gold],
            "construction": {
                "source": "MemConflict Data/Step4_4.jsonl",
                "layer": "paired_atomic_control",
                "parent_base_instance_id": base["base_instance_id"],
            },
        })
    return probes


def validate(
    composites: list[dict[str, Any]], probes: list[dict[str, Any]], per_cell: int
) -> dict[str, Any]:
    errors = []
    cell_counts = Counter(f"K{row['K']}_H{row['H']}" for row in composites)
    order_counts = Counter(row["order_variant"] for row in composites)
    base_counts = Counter(row["base_instance_id"] for row in composites)
    expected_cells = {"K2_H1", "K2_H2", "K3_H1", "K3_H2", "K3_H3"}

    for row in composites:
        if row["H"] != len(set(row["policies"])):
            errors.append(f"{row['instance_id']}: H mismatch")
        if row["K"] != len(row["gold_units"]):
            errors.append(f"{row['instance_id']}: K mismatch")
        memory_ids = {record["memory_id"] for record in row["memory_context"]}
        if len(memory_ids) != len(row["memory_context"]):
            errors.append(f"{row['instance_id']}: duplicate memory ids")
        for unit in row["gold_units"]:
            if not set(unit["evidence_ids"]).issubset(memory_ids):
                errors.append(f"{row['instance_id']}: missing gold evidence")

    if set(cell_counts) != expected_cells:
        errors.append(f"cell mismatch: {dict(cell_counts)}")
    for cell in expected_cells:
        if cell_counts[cell] != per_cell * 3:
            errors.append(f"{cell}: expected {per_cell * 3}, got {cell_counts[cell]}")
    if set(base_counts.values()) != {3}:
        errors.append("every base must have three order variants")
    if set(order_counts.values()) != {per_cell * len(expected_cells)}:
        errors.append(f"order imbalance: {dict(order_counts)}")

    return {
        "valid": not errors,
        "errors": errors,
        "base_composites": len(base_counts),
        "composite_order_variants": len(composites),
        "atomic_probes": len(probes),
        "cell_order_variant_counts": dict(sorted(cell_counts.items())),
        "order_counts": dict(sorted(order_counts.items())),
        "persona_count": len({row["persona_id"] for row in composites}),
        "policy_multisets": dict(sorted(Counter(row["policy_multiset"] for row in composites).items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--per-cell", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260827)
    args = parser.parse_args()

    people = read_jsonl(args.raw)
    people_by_id = {person["ID"]: person for person in people}
    candidates, extraction_errors = build_atomic_candidates(people)
    rng = random.Random(args.seed)
    bases = []

    for cell, patterns in CELL_PATTERNS.items():
        for index in range(args.per_cell):
            pattern = patterns[index % len(patterns)]
            personas = eligible_personas(candidates, pattern)
            if not personas:
                raise ValueError(f"No eligible persona for {cell} {pattern}")
            persona_id = personas[index % len(personas)]
            units = select_units(candidates[persona_id], pattern, rng)
            bases.append(
                build_base(
                    cell,
                    index + 1,
                    people_by_id[persona_id],
                    pattern,
                    units,
                )
            )

    composites = [row for base in bases for row in expand_orders(base)]
    probes = [row for base in bases for row in atomic_probes(base)]
    report = validate(composites, probes, args.per_cell)
    report.update({
        "seed": args.seed,
        "per_cell": args.per_cell,
        "candidate_counts": {
            persona: {policy: len(pools.get(policy, [])) for policy in POLICIES}
            for persona, pools in sorted(candidates.items())
        },
        "extraction_error_count": len(extraction_errors),
    })
    if not report["valid"]:
        raise ValueError(json.dumps(report, ensure_ascii=False, indent=2))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "composite_order_variants.jsonl", composites)
    write_jsonl(args.out_dir / "atomic_probes.jsonl", probes)
    write_jsonl(args.out_dir / "extraction_errors.jsonl", extraction_errors)
    (args.out_dir / "validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
