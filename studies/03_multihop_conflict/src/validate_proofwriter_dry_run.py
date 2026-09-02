"""Independently replay ProofWriter dry-run logic and paired controls."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from proofwriter_logic import closure, contradictions, opposite, parse_atom, parse_rule

STUDY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = STUDY_ROOT / "data/pilot_a/generated/proofwriter_natlang_dry_run.jsonl"
DEFAULT_OUTPUT = STUDY_ROOT / "data/pilot_a/proofwriter_natlang_symbolic_validation.json"
DEFAULT_REPORT = STUDY_ROOT / "data/pilot_a/proofwriter_natlang_symbolic_validation_report.md"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def canonical_content(instance: dict[str, Any], source_sentence_ids: set[str] | None = None):
    facts, rules = [], []
    for item in instance["oracle"]["C2_canonical_items"]:
        if item["item_id"] == "terminal":
            continue
        if source_sentence_ids is not None and item["source_sentence_id"] not in source_sentence_ids:
            continue
        if item["kind"] == "fact":
            facts.append(parse_atom(item["representation"]))
        elif item["kind"] == "rule":
            rules.append(parse_rule(item["representation"]))
        else:
            raise ValueError(f"Unknown item kind: {item['kind']}")
    return facts, rules


def validate(instances: list[dict[str, Any]]) -> dict[str, Any]:
    errors = []
    counts = Counter()
    by_base = defaultdict(dict)
    for instance in instances:
        instance_id = instance["instance_id"]
        label = instance["label"]
        counts[label] += 1
        base_id = instance_id.rsplit("-", 1)[0]
        by_base[base_id][label] = instance

        target = parse_atom(instance["gold_certificate"]["derived_target_representation"])
        terminal = parse_atom(instance["gold_certificate"]["terminal_representation"])
        facts, rules = canonical_content(instance)
        derived = closure(facts, rules)
        if target not in derived:
            errors.append(f"{instance_id}: target not independently derived")
        if contradictions(derived):
            errors.append(f"{instance_id}: source theory already inconsistent")

        with_terminal = closure(facts + [terminal], rules)
        has_conflict = bool(contradictions(with_terminal))
        if has_conflict != instance["conflict"]:
            errors.append(f"{instance_id}: replayed conflict={has_conflict}")
        if instance["conflict"] and terminal != opposite(target):
            errors.append(f"{instance_id}: terminal is not target opposite")
        if not instance["conflict"] and (terminal == target or terminal == opposite(target)):
            errors.append(f"{instance_id}: control terminal overlaps target")

        for document_id in ("D1", "D2"):
            document = next(doc for doc in instance["documents"] if doc["document_id"] == document_id)
            source_ids = {sentence["source_sentence_id"] for sentence in document["sentences"]}
            doc_facts, doc_rules = canonical_content(instance, source_ids)
            inventory = instance["construction_audit"]["document_item_inventory"][document_id]
            if not inventory["facts"] or not inventory["rules"]:
                errors.append(f"{instance_id}:{document_id}: raw facts/rules not mixed")
            if target in closure(doc_facts, doc_rules):
                errors.append(f"{instance_id}:{document_id}: target derivable from one document")

    paired_equal = 0
    for base_id, pair in by_base.items():
        if set(pair) == {"conflict", "no_conflict"}:
            conflict_docs = pair["conflict"]["documents"][:2]
            control_docs = pair["no_conflict"]["documents"][:2]
            if conflict_docs != control_docs:
                errors.append(f"{base_id}: paired D1/D2 differ")
            else:
                paired_equal += 1

    return {
        "validation_version": "proofwriter-natlang-symbolic-v1",
        "checked_at": "2026-09-01",
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "instance_count": len(instances),
        "counts": dict(counts),
        "paired_source_identical_count": paired_equal,
        "checks": [
            "target independently derived by forward chaining",
            "source theory consistent before terminal",
            "conflict label equals post-terminal logical consistency",
            "D1 and D2 each mix facts and rules",
            "target not derivable from D1 or D2 alone",
            "paired conflict/control share identical D1 and D2",
        ],
    }


def render(result: dict[str, Any]) -> str:
    lines = [
        "# ProofWriter NatLang independent symbolic validation",
        "",
        "작성일: 2026-09-01  ",
        f"상태: **{result['status']}** / 모델 미사용",
        "",
        f"- instances: {result['instance_count']}",
        f"- errors: {result['error_count']}",
        f"- identical paired source sets: {result['paired_source_identical_count']}",
        "",
        "## 독립 재검사 항목",
        "",
    ]
    lines.extend(f"- {item}" for item in result["checks"])
    if result["errors"]:
        lines.extend(["", "## 오류", ""])
        lines.extend(f"- {error}" for error in result["errors"])
    lines.extend([
        "",
        "공식 proof 문자열을 정답이라고 다시 복사하지 않고, canonical fact/rule을 "
        "별도 forward-chaining evaluator로 실행해 target과 terminal consistency를 재계산했다.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    result = validate(load_jsonl(args.input))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(render(result), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "error_count", "instance_count", "paired_source_identical_count")}, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
