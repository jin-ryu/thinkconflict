"""Stage I-1: count-matched no-conflict control cells K2_C0 and K3_C0.

Each unit is a dynamic profile attribute observed exactly once before its first
update (or never updated), so a single dated record fully determines the gold
answer. Record counts are padded to the Stage G conflict-cell medians with
other-person distractor records (same attribute, different owner) and unrelated
single-record user facts, so that the control differs from the conflict cells
only in the absence of conflicting claims.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from composite_conflict.prepare_pilot2_stage_g import (
    combined_query,
    read_jsonl,
    write_jsonl,
)

QUESTION_TEMPLATES = {
    "Residence": "Where does the user live?",
    "Career_Status": "What is the user's career situation (employment status, employer, title, industry)?",
    "Marital_Status": "What is the user's marital status?",
    "Work_Status": "What is the user's current work state?",
    "Health_Status": "How are the user's physical and mental health?",
    "Children_Status": "Does the user have children, and if so who are they?",
}
# Gold is restricted to the fields the question asks for; the memory record keeps every field.
GOLD_FIELDS = {
    "Career_Status": ("Employment_Status", "Company_Name", "Job_Title", "Industry"),
    "Marital_Status": ("Status",),
    "Work_Status": ("Current_State",),
    "Health_Status": ("Physical_Health", "Mental_Health"),
}
TARGET_RECORDS = {2: 5, 3: 8}  # Stage G medians for K=2 and K=3 conflict cells
CELLS = {"K2_C0": 2, "K3_C0": 3}


def compact(value: Any) -> str:
    if isinstance(value, dict):
        return "; ".join(f"{k}: {compact(v)}" for k, v in value.items())
    return str(value)


def gold_answer(attr: str, value: Any) -> str:
    if attr in GOLD_FIELDS and isinstance(value, dict):
        return compact({k: value[k] for k in GOLD_FIELDS[attr] if k in value})
    if attr == "Children_Status" and isinstance(value, dict):
        names = [child.get("Name") for key, child in value.items() if key.startswith("Child") and isinstance(child, dict)]
        status = value.get("Status")
        return f"Status: {status}" + (f"; Children: {', '.join(n for n in names if n)}" if names else "")
    return compact(value)


def control_units(person: dict[str, Any]) -> list[dict[str, Any]]:
    """Attributes revealed once and not updated until at least one session later."""
    sessions = person["Full_Session_Chain"]
    revealed: dict[str, tuple[int, str, Any]] = {}
    first_update: dict[str, int] = {}
    for session in sessions:
        for attr, value in (session.get("Revealed_Attributes") or {}).items():
            revealed.setdefault(attr, (session["Session_ID"], session["Date"], value))
        for item in session.get("Updated_Attributes") or []:
            first_update.setdefault(item["Attribute"], session["Session_ID"])
    by_id = {s["Session_ID"]: s for s in sessions}
    units = []
    for attr, (sid, date, value) in revealed.items():
        if attr not in QUESTION_TEMPLATES:
            continue
        update_sid = first_update.get(attr)
        if update_sid is not None and update_sid <= sid + 1:
            continue
        target_sid = (update_sid - 1) if update_sid is not None else sessions[-1]["Session_ID"]
        target_date = by_id[target_sid]["Date"]
        record = {
            "memory_id": f"{person['ID']}:S{sid}:{attr}:revealed",
            "observed_at": date,
            "source": "user_statement",
            "claim": {"attribute": attr, "value": value},
        }
        units.append({
            "question_uid": f"{person['ID']}:S{sid}:C0_{attr}",
            "question": QUESTION_TEMPLATES[attr],
            "target_date": target_date,
            "session_id": sid,
            "attribute": attr,
            "memory_context": [record],
            "gold_unit": {
                "unit_id": f"{person['ID']}:S{sid}:C0_{attr}",
                "policy": "LOOKUP",
                "target_attribute": attr,
                "gold_atomic_answer": gold_answer(attr, value),
                "evidence_ids": [record["memory_id"]],
                "atomic_question": QUESTION_TEMPLATES[attr],
                "unit_target_date": target_date,
            },
        })
    return units


def other_person_records(person: dict[str, Any], before: str) -> list[dict[str, Any]]:
    rows = []
    for session in person["Full_Session_Chain"]:
        if session["Date"] > before:
            continue
        for index, item in enumerate(session.get("Others_Dynamic_Information") or [], start=1):
            rows.append({
                "memory_id": f"{person['ID']}:S{session['Session_ID']}:ODI:{item.get('Attribute')}:{index}",
                "observed_at": session["Date"],
                "source": "other_person_statement",
                "claim": {
                    "about": item.get("Relationship_To_User", "other person"),
                    "attribute": item.get("Attribute"),
                    "value": item.get("Value"),
                },
            })
    return rows


def build_base(
    cell: str,
    index: int,
    person: dict[str, Any],
    units: list[dict[str, Any]],
    spare_units: list[dict[str, Any]],
    rng: random.Random,
) -> dict[str, Any]:
    k = len(units)
    target = TARGET_RECORDS[k]
    base_date = max(u["target_date"] for u in units)
    unit_attrs = {u["attribute"] for u in units}
    records = [r for u in units for r in u["memory_context"]]
    fillers: list[dict[str, Any]] = []

    others = other_person_records(person, base_date)
    same_attr = [r for r in others if r["claim"]["attribute"] in unit_attrs]
    rng.shuffle(same_attr)
    used_attr: set[str] = set()
    for record in same_attr:  # at most one owner-distractor per unit attribute
        if record["claim"]["attribute"] in used_attr:
            continue
        fillers.append(record)
        used_attr.add(record["claim"]["attribute"])
        if len(records) + len(fillers) >= target:
            break
    spare = [u for u in spare_units if u["attribute"] not in unit_attrs]
    rng.shuffle(spare)
    for unit in spare:
        if len(records) + len(fillers) >= target:
            break
        fillers.extend(unit["memory_context"])
    other_attr = [r for r in others if r["claim"]["attribute"] not in unit_attrs and r not in fillers]
    rng.shuffle(other_attr)
    for record in other_attr:
        if len(records) + len(fillers) >= target:
            break
        fillers.append(record)

    base_id = f"stagei:{cell.lower()}:{index:03d}:{person['ID'][:8]}"
    return {
        "base_instance_id": base_id,
        "persona_id": person["ID"],
        "persona_name": person["Fixed_Profile"].get("Name"),
        "target_date": base_date,
        "condition": "no_conflict",
        "cell": cell,
        "K": k,
        "H": 0,
        "policies": ["LOOKUP"] * k,
        "policy_multiset": "+".join(["LOOKUP"] * k),
        "query": combined_query(units),
        "gold_units": [dict(u["gold_unit"]) for u in units],
        "_units": units,
        "_fillers": fillers,
        "construction": {
            "source": "MemConflict Data/Step4_4.jsonl",
            "layer": "no_conflict_control",
            "filler_policy": "owner distractors for unit attributes first, then unrelated single-record user facts, then other-person records",
            "target_record_count": target,
        },
    }


def ordered(units: list[dict[str, Any]], fillers: list[dict[str, Any]], variant: str, rng: random.Random) -> list[dict[str, Any]]:
    unit_records = [r for u in units for r in u["memory_context"]]
    if variant == "original":
        rows = unit_records + fillers
    elif variant == "reverse":
        rows = list(reversed(unit_records + fillers))
    elif variant == "interleaved":
        rows = []
        for i in range(max(len(unit_records), len(fillers))):
            if i < len(unit_records):
                rows.append(unit_records[i])
            if i < len(fillers):
                rows.append(fillers[i])
    else:
        raise ValueError(variant)
    return rows


def expand(base: dict[str, Any], rng: random.Random) -> list[dict[str, Any]]:
    rows = []
    for variant in ("original", "reverse", "interleaved"):
        row = {k: v for k, v in base.items() if not k.startswith("_")}
        row["instance_id"] = f"{base['base_instance_id']}:{variant}"
        row["order_variant"] = variant
        row["memory_context"] = ordered(base["_units"], base["_fillers"], variant, rng)
        rows.append(row)
    return rows


def probes(base: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for i, unit in enumerate(base["_units"], start=1):
        rows.append({
            "instance_id": f"{base['base_instance_id']}:atomic:{i}",
            "base_instance_id": base["base_instance_id"],
            "parent_cell": base["cell"],
            "persona_id": base["persona_id"],
            "persona_name": base["persona_name"],
            "target_date": unit["target_date"],
            "condition": "atomic_control",
            "cell": "K1_C0",
            "K": 1,
            "H": 0,
            "policies": ["LOOKUP"],
            "policy_multiset": "LOOKUP",
            "query": combined_query([unit]),
            "memory_context": list(unit["memory_context"]),
            "gold_units": [dict(unit["gold_unit"])],
            "construction": {"layer": "paired_atomic_control", "parent_base_instance_id": base["base_instance_id"]},
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--per-cell", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260828)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    people = read_jsonl(args.raw)
    pools = {p["ID"]: control_units(p) for p in people}
    people_by_id = {p["ID"]: p for p in people}
    personas = sorted(pools)
    rng.shuffle(personas)
    bases = []
    for cell, k in CELLS.items():
        count = 0
        cursor = 0
        while count < args.per_cell:
            pid = personas[cursor % len(personas)]
            cursor += 1
            pool = pools[pid]
            if len(pool) < k:
                continue
            units = rng.sample(pool, k)
            spare = [u for u in pool if u not in units]
            bases.append(build_base(cell, count + 1, people_by_id[pid], units, spare, rng))
            count += 1
            if cursor > 10 * len(personas):
                raise RuntimeError("could not fill cells")

    composites = [row for b in bases for row in expand(b, rng)]
    atomic = [row for b in bases for row in probes(b)]

    errors = []
    record_counts = Counter()
    for row in composites:
        ids = [r["memory_id"] for r in row["memory_context"]]
        if len(ids) != len(set(ids)):
            errors.append(f"{row['instance_id']}: duplicate memory ids")
        attrs = [u["target_attribute"] for u in row["gold_units"]]
        if len(attrs) != len(set(attrs)):
            errors.append(f"{row['instance_id']}: duplicate unit attribute")
        for unit in row["gold_units"]:
            if not set(unit["evidence_ids"]).issubset(ids):
                errors.append(f"{row['instance_id']}: missing evidence")
        user_attr_records = Counter(
            r["claim"]["attribute"] for r in row["memory_context"] if r["source"] == "user_statement"
        )
        if any(user_attr_records[a] != 1 for a in attrs):
            errors.append(f"{row['instance_id']}: unit attribute has conflicting user records")
        if row["order_variant"] == "original":
            record_counts[(row["cell"], len(row["memory_context"]))] += 1
    report = {
        "valid": not errors,
        "errors": errors,
        "bases": len(bases),
        "composite_order_variants": len(composites),
        "atomic_probes": len(atomic),
        "record_count_distribution": {f"{c}:{n}": v for (c, n), v in sorted(record_counts.items())},
        "pool_sizes": {pid[:8]: len(units) for pid, units in sorted(pools.items())},
        "attribute_usage": dict(Counter(u["target_attribute"] for b in bases for u in b["gold_units"])),
        "seed": args.seed,
    }
    if errors:
        raise ValueError(json.dumps(report, ensure_ascii=False, indent=2))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "composite_order_variants.jsonl", composites)
    write_jsonl(args.out_dir / "atomic_probes.jsonl", atomic)
    (args.out_dir / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
