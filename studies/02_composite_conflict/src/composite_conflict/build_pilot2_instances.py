"""Build compact, source-grounded Pilot 2 instances from MemConflict reviews."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


QUESTION_TO_ATTRIBUTE = (
    (re.compile(r"work status", re.I), "Work_Status"),
    (re.compile(r"residence|moved|move from|new city", re.I), "Residence"),
    (re.compile(r"health", re.I), "Health_Status"),
    (re.compile(r"social status|social life", re.I), "Social_Status"),
    (re.compile(r"marital|relationship situation|relationship status", re.I), "Marital_Status"),
    (re.compile(r"child|children|childcare|family has grown", re.I), "Children_Status"),
    (re.compile(r"career|company|job title|industry|employment|job situation", re.I), "Career_Status"),
)

STOP = {
    "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "when", "does",
    "user", "prefer", "prefers", "preference", "under", "what", "condition", "they",
}


def load_jsonl(path: Path) -> list[dict]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z][a-z-]+", text.lower()) if token not in STOP and len(token) > 2}


def dynamic_attribute(question: str) -> str:
    for pattern, attribute in QUESTION_TO_ATTRIBUTE:
        if pattern.search(question):
            return attribute
    raise ValueError(f"Cannot map dynamic question to attribute: {question}")


def find_prior_date(person: dict, target_session: dict, attribute: str) -> str:
    prior = []
    for session in person["Full_Session_Chain"]:
        if session["Session_ID"] >= target_session["Session_ID"]:
            continue
        if any(update.get("Attribute") == attribute for update in session.get("Updated_Attributes", [])):
            prior.append(session)
    return prior[-1]["Date"] if prior else f"before {target_session['Date']}"


def dynamic_evidence(person: dict, session: dict, question: dict) -> tuple[list[dict], dict]:
    attribute = dynamic_attribute(question["question"])
    updates = [item for item in session.get("Updated_Attributes", []) if item.get("Attribute") == attribute]
    if len(updates) != 1:
        raise ValueError(f"Expected one {attribute} update in {question['question_uid']}, found {len(updates)}")
    update = updates[0]
    records = [
        {
            "memory_id": f"{question['persona_id']}:S{session['Session_ID']}:{attribute}:prior",
            "observed_at": find_prior_date(person, session, attribute),
            "source": "user_profile_history",
            "claim": {"attribute": attribute, "value": update["Before"]},
        },
        {
            "memory_id": f"{question['persona_id']}:S{session['Session_ID']}:{attribute}:update",
            "observed_at": session["Date"],
            "source": "user_update",
            "claim": {"attribute": attribute, "value": update["After"]},
        },
    ]
    unit = {
        "unit_id": question["question_id"],
        "policy": "SUPERSEDE",
        "target_attribute": attribute,
        "gold_atomic_answer": question["answer"],
        "evidence_ids": [record["memory_id"] for record in records],
    }
    return records, unit


def conditional_evidence(person: dict, session: dict, question: dict) -> tuple[list[dict], dict]:
    query_tokens = tokens(question["question"] + " " + question["answer"])
    groups: dict[str, list[tuple[dict, dict]]] = {}
    for source_session in person["Full_Session_Chain"]:
        if source_session["Session_ID"] > session["Session_ID"]:
            continue
        for item in source_session.get("Conditional_Conflict_Information", []):
            groups.setdefault(item["Conflict_ID"], []).append((source_session, item))

    def group_score(entries: list[tuple[dict, dict]]) -> float:
        text = " ".join(
            " ".join(str(item.get(key, "")) for key in ("Preference_Type", "Item", "Condition", "Preference_Key", "Preference_Description"))
            for _, item in entries
        )
        entry_tokens = tokens(text)
        return len(query_tokens & entry_tokens) / max(len(query_tokens), 1)

    conflict_id, entries = max(groups.items(), key=lambda pair: group_score(pair[1]))
    if group_score(entries) == 0:
        raise ValueError(f"No conditional evidence overlap for {question['question_uid']}")

    records = []
    for source_session, item in entries:
        role = item.get("Role", "unknown")
        if role == "Distractor":
            claim = {
                "about": item.get("Relationship_To_User", "other person"),
                "item": item.get("Preference_Key"),
                "condition": item.get("Preference_Description"),
            }
            source = "other_person_statement"
        else:
            claim = {
                "preference_type": item.get("Preference_Type"),
                "item": item.get("Item"),
                "condition": item.get("Condition"),
            }
            source = "user_preference_statement"
        records.append({
            "memory_id": f"{question['persona_id']}:S{source_session['Session_ID']}:{conflict_id}:{len(records)+1}",
            "observed_at": source_session["Date"],
            "source": source,
            "claim": claim,
        })

    unit = {
        "unit_id": question["question_id"],
        "policy": "CONDITION",
        "target_attribute": conflict_id,
        "gold_atomic_answer": question["answer"],
        "evidence_ids": [record["memory_id"] for record in records],
    }
    return records, unit


def static_evidence(person: dict, session: dict, question: dict) -> tuple[list[dict], dict]:
    """Recover the canonical/contradictory source pair for a static question."""
    point_b = [
        item
        for item in session.get("Static_Conflict_Information", [])
        if item.get("Role") == "Point_B"
    ]
    if not point_b:
        raise ValueError(f"No static Point_B for {question['question_uid']}")

    query_tokens = tokens(question["question"] + " " + question["answer"])

    def item_score(item: dict) -> int:
        text = " ".join(str(item.get(key, "")) for key in ("Target_Field_Path", "Value"))
        return len(query_tokens & tokens(text))

    target = max(point_b, key=item_score)
    conflict_id = target["Conflict_ID"]
    entries: list[tuple[dict, dict]] = []
    for source_session in person["Full_Session_Chain"]:
        if source_session["Session_ID"] > session["Session_ID"]:
            continue
        for item in source_session.get("Static_Conflict_Information", []):
            if item.get("Conflict_ID") == conflict_id:
                entries.append((source_session, item))

    roles = {item.get("Role") for _, item in entries}
    if not {"Point_A", "Point_B"}.issubset(roles):
        raise ValueError(f"Incomplete static pair for {question['question_uid']}: {roles}")

    records = []
    gold_evidence_ids = []
    for source_session, item in entries:
        role = item.get("Role", "unknown")
        memory_id = (
            f"{question['persona_id']}:S{source_session['Session_ID']}:"
            f"{conflict_id}:{len(records)+1}"
        )
        source = {
            "Point_A": "verified_profile_record",
            "Point_B": "unverified_conflicting_statement",
            "Distractor": "other_person_statement",
        }.get(role, "memory_statement")
        claim = {
            "attribute": item.get("Target_Field_Path"),
            "value": item.get("Value"),
        }
        if role == "Distractor":
            claim["about"] = item.get("Relationship_To_User", "other person")
        records.append({
            "memory_id": memory_id,
            "observed_at": source_session["Date"],
            "source": source,
            "claim": claim,
        })
        if role in {"Point_A", "Point_B"}:
            gold_evidence_ids.append(memory_id)

    unit = {
        "unit_id": question["question_id"],
        "policy": "VERIFY_PREFER",
        "target_attribute": target.get("Target_Field_Path", conflict_id),
        "gold_atomic_answer": question["answer"],
        "evidence_ids": gold_evidence_ids,
    }
    return records, unit


def build_instance(review: dict, people: dict[str, dict]) -> dict:
    person = people[review["persona_id"]]
    session = next(item for item in person["Full_Session_Chain"] if item["Session_ID"] == review["session_id"])
    question_by_id = {item["question_id"]: item for item in session["Session_Questions"]}
    memory_context = []
    units = []
    conditional_ids = set()
    for question_uid, policy in zip(review["question_uids"], review["policies"]):
        question_id = question_uid.rsplit(":", 1)[-1]
        raw_question = dict(question_by_id[question_id])
        raw_question.update({
            "question_uid": question_uid,
            "question_id": question_id,
            "persona_id": review["persona_id"],
        })
        if policy == "SUPERSEDE":
            records, unit = dynamic_evidence(person, session, raw_question)
        elif policy == "CONDITION":
            records, unit = conditional_evidence(person, session, raw_question)
            if unit["target_attribute"] in conditional_ids:
                raise ValueError(f"Two conditional questions mapped to one unit in {review['pair_id']}")
            conditional_ids.add(unit["target_attribute"])
        elif policy == "VERIFY_PREFER":
            records, unit = static_evidence(person, session, raw_question)
        else:
            raise ValueError(f"Unsupported policy in compact pilot: {policy}")
        memory_context.extend(records)
        units.append(unit)

    unique_context = {record["memory_id"]: record for record in memory_context}
    return {
        "instance_id": review["pair_id"],
        "persona_id": review["persona_id"],
        "persona_name": review["persona_name"],
        "target_date": review["date"],
        "condition": review["condition"],
        "K": 2,
        "H": len(set(review["policies"])),
        "policies": review["policies"],
        "query": review["codex_review"]["combined_query"],
        "memory_context": list(unique_context.values()),
        "gold_units": units,
        "construction": {
            "source": "MemConflict Data/Step4_4.jsonl",
            "source_pair_id": review["pair_id"],
            "review_protocol": review["judge"]["protocol"],
            "retrieval_setting": "oracle relevant evidence; includes same-conflict distractors",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("reviews", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    people = {person["ID"]: person for person in load_jsonl(args.raw)}
    reviews = [row for row in load_jsonl(args.reviews) if row["codex_review"]["codex_valid"]]
    instances = [build_instance(review, people) for review in reviews]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        for instance in instances:
            handle.write(json.dumps(instance, ensure_ascii=False) + "\n")
    print(json.dumps({
        "instances": len(instances),
        "H_distribution": {str(value): sum(row["H"] == value for row in instances) for value in sorted({row["H"] for row in instances})},
        "mean_context_records": round(sum(len(row["memory_context"]) for row in instances) / len(instances), 2),
    }, indent=2))


if __name__ == "__main__":
    main()
