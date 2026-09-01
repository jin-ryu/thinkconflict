"""Prepare matching covariates and K=1 probes for Pilot 2B."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DOMAINS = {
    "work": r"\b(?:work|career|job|employment|business|conference|research|coding|rehearsal)\w*",
    "health": r"\b(?:health|stress|fatigue|unwell|recovery|exercise|workout)\w*",
    "social": r"\b(?:social|friend|relationship|marital|dating|single|group)\w*",
    "family": r"\b(?:child|children|childcare|baby|family|parent)\w*",
    "travel": r"\b(?:residence|relocation|city|travel|trip|hotel|hostel|resort|camping)\w*",
    "media": r"\b(?:read|book|journal|movie|film|game|music|watch|entertainment)\w*",
    "food_drink": r"\b(?:food|meal|dinner|breakfast|snack|drink|tea|coffee|juice|soup)\w*",
    "clothing": r"\b(?:clothing|outfit|shirt|tank|suit|dress|shoes)\w*",
    "schedule": r"\b(?:schedule|routine|week|weekend|morning|evening|break|plan|time)\w*",
}


def load(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def word_count(value: Any) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", json.dumps(value, ensure_ascii=False)))


def domain_set(text: str) -> list[str]:
    return sorted(name for name, pattern in DOMAINS.items() if re.search(pattern, text, re.I))


def review_questions(paths: list[Path]) -> dict[tuple[str, str], str]:
    result = {}
    for path in paths:
        for row in load(path):
            for uid, question in zip(row["question_uids"], row["questions"]):
                result[(row["pair_id"], uid.rsplit(":", 1)[-1])] = question
    return result


def covariates(instance: dict[str, Any]) -> dict[str, Any]:
    context = instance["memory_context"]
    answers = [unit["gold_atomic_answer"] for unit in instance["gold_units"]]
    text = " ".join([instance["query"], *answers])
    return {
        "instance_id": instance["instance_id"],
        "condition": instance["condition"],
        "H": instance["H"],
        "policies": instance["policies"],
        "domains": domain_set(text),
        "query_words": word_count(instance["query"]),
        "query_chars": len(instance["query"]),
        "answer_words": sum(word_count(answer) for answer in answers),
        "context_records": len(context),
        "context_words": word_count(context),
        "relevant_evidence": sum(len(unit["evidence_ids"]) for unit in instance["gold_units"]),
        "distractor_records": sum(record.get("source") == "other_person_statement" for record in context),
        "explicit_policy_cue": bool(re.search(r"\b(?:latest|current|changed|now|when|condition|according|matches)\b", instance["query"], re.I)),
    }


def single_probes(instance: dict[str, Any], questions: dict[tuple[str, str], str]) -> list[dict[str, Any]]:
    probes = []
    by_id = {record["memory_id"]: record for record in instance["memory_context"]}
    for unit in instance["gold_units"]:
        unit_id = unit["unit_id"]
        probe_id = f"{instance['instance_id']}::single::{unit_id}"
        probes.append({
            "instance_id": probe_id,
            "parent_instance_id": instance["instance_id"],
            "persona_id": instance["persona_id"],
            "persona_name": instance["persona_name"],
            "target_date": instance["target_date"],
            "condition": "single_unit",
            "K": 1,
            "H": 1,
            "policies": [unit["policy"]],
            "query": questions[(instance["instance_id"], unit_id)],
            "memory_context": [by_id[memory_id] for memory_id in unit["evidence_ids"]],
            "gold_units": [unit],
            "construction": {
                "source": "Pilot 2 frozen instance",
                "parent_instance_id": instance["instance_id"],
                "purpose": "single-unit difficulty probe",
            },
        })
    return probes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances", nargs="+", type=Path, required=True)
    parser.add_argument("--reviews", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    instances = [row for path in args.instances for row in load(path)]
    questions = review_questions(args.reviews)
    covariate_rows = [covariates(instance) for instance in instances]
    probes = [probe for instance in instances for probe in single_probes(instance, questions)]
    dump(args.output_dir / "matching_covariates.jsonl", covariate_rows)
    dump(args.output_dir / "single_unit_probes.jsonl", probes)
    print(json.dumps({"instances": len(instances), "covariates": len(covariate_rows), "single_unit_probes": len(probes)}, indent=2))


if __name__ == "__main__":
    main()
