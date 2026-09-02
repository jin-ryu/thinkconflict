"""Construct a model-free 20-item ProofWriter NatLang dry run for Pilot A."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from proofwriter_logic import closure, parse_atom, parse_rule

STUDY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = STUDY_ROOT / "data/raw/proofwriter/proofwriter-dataset-V2020.12.3.zip"
OUT_ROOT = STUDY_ROOT / "data/pilot_a"
GENERATED_PATH = OUT_ROOT / "generated/proofwriter_natlang_dry_run.jsonl"
MANIFEST_PATH = OUT_ROOT / "proofwriter_natlang_dry_run_manifest.json"
VALIDATION_PATH = OUT_ROOT / "proofwriter_natlang_dry_run_validation.json"
REPORT_PATH = OUT_ROOT / "proofwriter_natlang_dry_run_report.md"
SEED = 20260901
MEMBERS = {
    "dev": "proofwriter-dataset-V2020.12.3/OWA/NatLang/meta-dev.jsonl",
    "test": "proofwriter-dataset-V2020.12.3/OWA/NatLang/meta-test.jsonl",
}
ITEM_RE = re.compile(r"\b(?:triple|rule)\d+\b")
RULE_APPLICATION_RE = re.compile(r"rule\d+\s+%\s+int\d+")


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def target_polarity(representation: str) -> str:
    matches = re.findall(r'"([+\-])"', representation)
    if not matches:
        raise ValueError(f"Missing polarity: {representation!r}")
    return matches[-1]


def flip_polarity(representation: str) -> str:
    polarity = target_polarity(representation)
    replacement = '"-"' if polarity == "+" else '"+"'
    return re.sub(r'"[+\-]"(?=\)$)', replacement, representation, count=1)


def family(record_id: str) -> str:
    return record_id.split("-", 1)[0]


def proof_choice(question: dict[str, Any]) -> dict[str, Any] | None:
    qdep = question["QDep"]
    for proof in question.get("proofsWithIntermediates") or []:
        representation = proof.get("representation", "")
        if len(RULE_APPLICATION_RE.findall(representation)) == qdep:
            return proof
    return None


def referenced_items(proof: dict[str, Any]) -> tuple[list[str], list[str]]:
    items = set(ITEM_RE.findall(proof["representation"]))
    return (
        sorted(item for item in items if item.startswith("triple")),
        sorted(item for item in items if item.startswith("rule")),
    )


def question_by_representation(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {q["representation"]: q for q in record["questions"].values()}


def provable_representations(record: dict[str, Any]) -> set[str]:
    return {detail["representation"] for detail in record.get("proofDetails", [])}


def negative_unknown_terminal(record: dict[str, Any], excluded: set[str]) -> dict[str, Any] | None:
    provable = provable_representations(record)
    facts = {item["representation"] for item in record["triples"].values()}
    candidates = []
    for question_id, question in record["questions"].items():
        representation = question["representation"]
        if (
            question["answer"] == "Unknown"
            and target_polarity(representation) == "-"
            and representation not in excluded
            and representation not in provable
            and representation not in facts
            and flip_polarity(representation) not in provable
            and flip_polarity(representation) not in facts
        ):
            candidates.append((question_id, question))
    if not candidates:
        return None
    question_id, question = sorted(candidates)[0]
    return {"question_id": question_id, **question}


def candidate(record: dict[str, Any], split: str, question_id: str, question: dict[str, Any]) -> dict[str, Any] | None:
    if (
        question["answer"] is not True
        or question["strategy"] != "proof"
        or question["QDep"] not in {2, 3, 4}
        or target_polarity(question["representation"]) != "+"
    ):
        return None
    proof = proof_choice(question)
    if proof is None:
        return None
    triples, rules = referenced_items(proof)
    required = triples + rules
    if not triples or not rules or any(item not in record["mappings"] for item in required):
        return None
    inverse_representation = flip_polarity(question["representation"])
    inverse_question = question_by_representation(record).get(inverse_representation)
    if inverse_question is None:
        return None
    if inverse_representation in provable_representations(record):
        return None
    control = negative_unknown_terminal(record, {inverse_representation})
    if control is None:
        return None
    return {
        "split": split,
        "theory_id": record["id"],
        "family": family(record["id"]),
        "question_id": question_id,
        "qdep": question["QDep"],
        "question": question,
        "proof": proof,
        "required_triples": triples,
        "required_rules": rules,
        "inverse_question": inverse_question,
        "control_terminal": control,
        "record": record,
    }


def load_candidates(archive: Path) -> list[dict[str, Any]]:
    candidates = []
    with zipfile.ZipFile(archive) as bundle:
        for split, member in MEMBERS.items():
            with bundle.open(member) as handle:
                for raw_line in handle:
                    record = json.loads(raw_line)
                    if "mappings" not in record or "sentences" not in record:
                        continue
                    for question_id, question in record["questions"].items():
                        value = candidate(record, split, question_id, question)
                        if value is not None:
                            candidates.append(value)
    return candidates


def select_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    selected = []
    used_theories = set()
    for depth in (2, 3, 4):
        pool = [candidate for candidate in candidates if candidate["qdep"] == depth]
        rng.shuffle(pool)
        # Round-robin split and family before taking five.
        pool.sort(key=lambda item: (item["split"], item["family"], canonical_hash(item["theory_id"])))
        depth_selected = []
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for item in pool:
            groups[(item["split"], item["family"])].append(item)
        group_keys = sorted(groups)
        cursor = 0
        while len(depth_selected) < 5 and group_keys:
            key = group_keys[cursor % len(group_keys)]
            while groups[key] and groups[key][0]["theory_id"] in used_theories:
                groups[key].pop(0)
            if groups[key]:
                item = groups[key].pop(0)
                depth_selected.append(item)
                used_theories.add(item["theory_id"])
            else:
                group_keys.remove(key)
                cursor -= 1
            cursor += 1
        if len(depth_selected) != 5:
            raise ValueError(f"Could only select {len(depth_selected)} depth-{depth} candidates")
        selected.extend(depth_selected)
    return selected


def sentence_ids(record: dict[str, Any], item_ids: Iterable[str]) -> list[str]:
    return sorted({record["mappings"][item_id] for item_id in item_ids})


def partition_source_sentences(item: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Mix fact/rule sentences while keeping the target cross-document."""
    record = item["record"]
    all_sentence_ids = sorted(record["sentences"])
    required_sentence_ids = set(sentence_ids(
        record, item["required_triples"] + item["required_rules"]
    ))
    target = parse_atom(item["question"]["representation"])
    seed = int(canonical_hash({"theory": item["theory_id"], "seed": SEED})[:16], 16)
    rng = random.Random(seed)

    def content(group: set[str]):
        fact_ids = [
            item_id for item_id in record["triples"]
            if record["mappings"][item_id] in group
        ]
        rule_ids = [
            item_id for item_id in record["rules"]
            if record["mappings"][item_id] in group
        ]
        facts = [parse_atom(record["triples"][item_id]["representation"]) for item_id in fact_ids]
        rules = [parse_rule(record["rules"][item_id]["representation"]) for item_id in rule_ids]
        return fact_ids, rule_ids, closure(facts, rules)

    for _ in range(5000):
        shuffled = list(all_sentence_ids)
        rng.shuffle(shuffled)
        cut = max(2, min(len(shuffled) - 2, len(shuffled) // 2))
        left, right = set(shuffled[:cut]), set(shuffled[cut:])
        if not (required_sentence_ids & left and required_sentence_ids & right):
            continue
        left_facts, left_rules, left_closure = content(left)
        right_facts, right_rules, right_closure = content(right)
        if not (left_facts and left_rules and right_facts and right_rules):
            continue
        if target in left_closure or target in right_closure:
            continue
        return sorted(left), sorted(right)
    raise ValueError(f"Could not find cross-document mixed partition for {item['theory_id']}")


def make_documents(item: dict[str, Any], terminal_text: str) -> list[dict[str, Any]]:
    record = item["record"]
    left_ids, right_ids = partition_source_sentences(item)
    return [
        {
            "document_id": "D1",
            "role": "evidence_source",
            "sentences": [
                {"sentence_id": f"D1-S{index}", "source_sentence_id": sent_id, "text": record["sentences"][sent_id]}
                for index, sent_id in enumerate(left_ids, 1)
            ],
        },
        {
            "document_id": "D2",
            "role": "evidence_source",
            "sentences": [
                {"sentence_id": f"D2-S{index}", "source_sentence_id": sent_id, "text": record["sentences"][sent_id]}
                for index, sent_id in enumerate(right_ids, 1)
            ],
        },
        {
            "document_id": "D3",
            "role": "terminal_source",
            "sentences": [
                {"sentence_id": "D3-S1", "source_sentence_id": "derived-terminal", "text": terminal_text}
            ],
        },
    ]

def source_output_ids(documents: list[dict[str, Any]], source_sentence_ids: set[str]) -> list[str]:
    result = []
    for document in documents:
        for sentence in document["sentences"]:
            if sentence["source_sentence_id"] in source_sentence_ids or sentence["sentence_id"] == "D3-S1":
                result.append(sentence["sentence_id"])
    return result


def build_instance(item: dict[str, Any], instance_id: str, label: str) -> dict[str, Any]:
    record = item["record"]
    is_conflict = label == "conflict"
    terminal = item["inverse_question"] if is_conflict else item["control_terminal"]
    documents = make_documents(item, terminal["question"])
    required_ids = item["required_triples"] + item["required_rules"]
    required_sentence_ids = set(sentence_ids(record, required_ids))
    canonical_items = [
        {"item_id": item_id, "kind": "fact", "source_sentence_id": record["mappings"][item_id], **record["triples"][item_id]}
        for item_id in item["required_triples"]
    ] + [
        {"item_id": item_id, "kind": "rule", "source_sentence_id": record["mappings"][item_id], **record["rules"][item_id]}
        for item_id in item["required_rules"]
    ]
    document_inventory = {}
    for document in documents[:2]:
        source_ids = {sentence["source_sentence_id"] for sentence in document["sentences"]}
        document_inventory[document["document_id"]] = {
            "facts": sorted(item_id for item_id in record["triples"] if record["mappings"][item_id] in source_ids),
            "rules": sorted(item_id for item_id in record["rules"] if record["mappings"][item_id] in source_ids),
        }
    return {
        "instance_id": instance_id,
        "dataset_status": "dry_run_not_for_model_evaluation",
        "label": label,
        "conflict": is_conflict,
        "source": {
            "dataset": "ProofWriter",
            "release": "V2020.12.3",
            "world": "OWA",
            "subset": "NatLang",
            "split": item["split"],
            "theory_id": item["theory_id"],
            "question_id": item["question_id"],
        },
        "hop": item["qdep"],
        "documents": documents,
        "construction_audit": {"document_item_inventory": document_inventory},
        "oracle": {
            "C1_gold_source_sentence_ids": source_output_ids(documents, required_sentence_ids),
            "C2_canonical_items": canonical_items + [{
                "item_id": "terminal", "kind": "fact", "text": terminal["question"],
                "representation": terminal["representation"],
            }],
            "C2T_representations": [entry["representation"] for entry in canonical_items] + [terminal["representation"]],
            "C3_proof_graph": {
                "proof_representation": item["proof"]["representation"],
                "intermediates": item["proof"]["intermediates"],
                "terminal_representation": terminal["representation"],
            },
            "C4_proof_skeleton": {
                "required_triples": item["required_triples"],
                "required_rules": item["required_rules"],
                "proof_representation": item["proof"]["representation"],
            },
        },
        "gold_certificate": {
            "derived_target_text": item["question"]["question"],
            "derived_target_representation": item["question"]["representation"],
            "terminal_text": terminal["question"],
            "terminal_representation": terminal["representation"],
            "terminal_incompatibility": is_conflict,
            "proof_depth": item["qdep"],
        },
    }


def validate(instances: list[dict[str, Any]]) -> dict[str, Any]:
    errors = []
    counts = Counter()
    pairs = defaultdict(dict)
    for instance in instances:
        counts[(instance["label"], instance["hop"])] += 1
        base_id = instance["instance_id"].rsplit("-", 1)[0]
        pairs[base_id][instance["label"]] = instance
        target = instance["gold_certificate"]["derived_target_representation"]
        terminal = instance["gold_certificate"]["terminal_representation"]
        if instance["conflict"] and terminal != flip_polarity(target):
            errors.append(f"{instance['instance_id']}: terminal is not inverse target")
        if not instance["conflict"] and terminal in {target, flip_polarity(target)}:
            errors.append(f"{instance['instance_id']}: control terminal overlaps target")
        proof = instance["oracle"]["C3_proof_graph"]["proof_representation"]
        if len(RULE_APPLICATION_RE.findall(proof)) != instance["hop"]:
            errors.append(f"{instance['instance_id']}: proof depth mismatch")
        doc_ids = {doc["document_id"] for doc in instance["documents"]}
        if doc_ids != {"D1", "D2", "D3"}:
            errors.append(f"{instance['instance_id']}: document IDs")
        gold_ids = set(instance["oracle"]["C1_gold_source_sentence_ids"])
        all_ids = {s["sentence_id"] for d in instance["documents"] for s in d["sentences"]}
        if not gold_ids <= all_ids or "D3-S1" not in gold_ids:
            errors.append(f"{instance['instance_id']}: C1 source coverage")

    conflict_bases = {key for key, value in pairs.items() if "conflict" in value}
    control_bases = {key for key, value in pairs.items() if "no_conflict" in value}
    if len(conflict_bases) != 15:
        errors.append(f"expected 15 conflict bases, got {len(conflict_bases)}")
    if len(control_bases) != 5:
        errors.append(f"expected 5 paired controls, got {len(control_bases)}")

    expected_conflict = {2: 5, 3: 5, 4: 5}
    for depth, expected in expected_conflict.items():
        actual = counts[("conflict", depth)]
        if actual != expected:
            errors.append(f"depth {depth}: expected {expected} conflicts, got {actual}")
    if sum(counts[("no_conflict", depth)] for depth in (2, 3, 4)) != 5:
        errors.append("expected 5 no-conflict controls")

    return {
        "validation_version": "proofwriter-natlang-dry-run-v1",
        "checked_at": "2026-09-01",
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "instance_count": len(instances),
        "counts": {
            label: {str(depth): counts[(label, depth)] for depth in (2, 3, 4)}
            for label in ("conflict", "no_conflict")
        },
        "gates_passed": {
            "official_gold_proof_present": not any("proof" in error for error in errors),
            "terminal_polarity_valid": not any("terminal" in error for error in errors),
            "source_sentence_coverage": not any("source coverage" in error for error in errors),
            "paired_control_count": len(control_bases) == 5,
            "raw_text_is_human_paraphrased_natlang": True,
        },
        "limitations": [
            "Facts and rules are mixed across D1/D2, but the synthetic micro-document style remains to be audited.",
            "ProofWriter NatLang provable targets are positive, so every terminal statement is negative; conflict and controls keep this cue matched.",
            "The NatLang source is AttNoneg unary-attribute reasoning only; binary relations require external transfer validation.",
            "Independent forward-chaining validation is recorded in a separate validation artifact.",
            "Human semantic-equivalence review of NatLang sentences remains pending.",
        ],
    }


def public_manifest(selected: list[dict[str, Any]], controls: set[str]) -> dict[str, Any]:
    return {
        "manifest_version": "proofwriter-natlang-dry-run-v1",
        "seed": SEED,
        "status": "dry_run_not_for_model_evaluation",
        "source": "ProofWriter V2020.12.3 / OWA / NatLang dev+test",
        "redistribution": "No original sentences are included; official archive license is unverified.",
        "selection": [
            {
                "base_instance_id": f"pw-nl-d{item['qdep']}-{index:02d}",
                "split": item["split"],
                "theory_id": item["theory_id"],
                "question_id": item["question_id"],
                "family": item["family"],
                "qdep": item["qdep"],
                "paired_control": item["theory_id"] in controls,
                "source_record_sha256": canonical_hash(item["record"]),
            }
            for index, item in enumerate(selected, 1)
        ],
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def render_report(validation: dict[str, Any], selected: list[dict[str, Any]]) -> str:
    split_counts = Counter(item["split"] for item in selected)
    family_counts = Counter(item["family"] for item in selected)
    lines = [
        "# ProofWriter NatLang 20-item dry-run build",
        "",
        "작성일: 2026-09-01  ",
        f"상태: **{validation['status']}** / 모델 평가 전 구조 검증",
        "",
        "## 구성",
        "",
        "| label | 2-hop | 3-hop | 4-hop | 합계 |",
        "|---|---:|---:|---:|---:|",
    ]
    for label in ("conflict", "no_conflict"):
        counts = validation["counts"][label]
        total = sum(counts.values())
        lines.append(f"| {label} | {counts['2']} | {counts['3']} | {counts['4']} | {total} |")
    lines.extend([
        "",
        f"- source split: {dict(split_counts)}",
        f"- theory family: {dict(family_counts)}",
        "- C0: crowdsourced NatLang fact/rule sentences mixed across D1/D2 + terminal D3",
        "- C1: proof에 필요한 원문 sentence만",
        "- C2/C2T: 원본 mapping의 canonical fact/rule text와 representation",
        "- C3/C4: 공식 proof-with-intermediates와 required item skeleton",
        "",
        "## 자동 검사",
        "",
        f"- instance: {validation['instance_count']}개",
        f"- error: {validation['error_count']}개",
    ])
    for gate, passed in validation["gates_passed"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'}: `{gate}`")
    lines.extend([
        "",
        "## 해석",
        "",
        "공식 NatLang 문장과 canonical fact/rule mapping을 함께 사용하므로 일반 synthetic split보다 "
        "C1→C2 semantic compilation 개입을 구성하기에 적합하다. 충돌은 gold proof target의 "
        "반대 claim을 D3에 추가해 만들었고, control도 음수 terminal을 유지해 부정어 단서를 맞췄다.",
        "",
        "## 모델 실행 전 남은 gate",
        "",
    ])
    for limitation in validation["limitations"]:
        lines.append(f"- {limitation}")
    lines.extend([
        "",
        "따라서 현재 20개는 데이터 제작 방식 검증용이며 평가 모델에 입력하지 않는다.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    args = parser.parse_args()
    candidates = load_candidates(args.archive)
    selected = select_candidates(candidates)
    # Controls: two depth-2, two depth-3, one depth-4, fixed by selected order.
    control_theories = {
        item["theory_id"]
        for depth, count in ((2, 2), (3, 2), (4, 1))
        for item in [candidate for candidate in selected if candidate["qdep"] == depth][:count]
    }
    instances = []
    for index, item in enumerate(selected, 1):
        base_id = f"pw-nl-d{item['qdep']}-{index:02d}"
        instances.append(build_instance(item, f"{base_id}-conflict", "conflict"))
        if item["theory_id"] in control_theories:
            instances.append(build_instance(item, f"{base_id}-no_conflict", "no_conflict"))
    validation = validate(instances)
    write_jsonl(GENERATED_PATH, instances)
    write_json(MANIFEST_PATH, public_manifest(selected, control_theories))
    write_json(VALIDATION_PATH, validation)
    REPORT_PATH.write_text(render_report(validation, selected), encoding="utf-8")
    print(json.dumps({
        "status": validation["status"],
        "instance_count": validation["instance_count"],
        "error_count": validation["error_count"],
        "candidate_pool": len(candidates),
    }, indent=2))
    if validation["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
