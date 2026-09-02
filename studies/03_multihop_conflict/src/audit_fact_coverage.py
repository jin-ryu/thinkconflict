"""Score whether MAGIC triplet facts are verbalized in their assigned contexts.

The NLI scores are triage signals only. They must not be copied into gold decisions
without source-level review.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

STUDY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = STUDY_ROOT / "data" / "pilot_a" / "generated" / "audit_candidates.jsonl"
DEFAULT_OUTPUT = STUDY_ROOT / "data" / "pilot_a" / "generated" / "nli_fact_coverage.jsonl"
DEFAULT_MODEL = Path("/home/infidea/backup-data/.model-cache/deberta-v3-base-mnli-fever-anli")
PRESCREEN_PATH = STUDY_ROOT / "data" / "pilot_a" / "assistant_prescreen.jsonl"


def load_prepare_module():
    path = Path(__file__).with_name("prepare_pilot_a_data.py")
    spec = importlib.util.spec_from_file_location("prepare_pilot_a_data", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def fact_hypothesis(triplet: str, prepare) -> str:
    subject, relation, obj = prepare.parse_triplet(triplet)
    return f"{subject} {relation} {obj}."


def model_fingerprint(model_dir: Path) -> str:
    digest = hashlib.sha256()
    for name in ("config.json", "tokenizer_config.json"):
        path = model_dir / name
        digest.update(path.read_bytes())
    return digest.hexdigest()


def score_pairs(pairs: list[tuple[str, str]], model_dir: Path, batch_size: int) -> list[float]:
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir, local_files_only=True)
    model.eval()
    entailment_id = next(
        index for index, label in model.config.id2label.items() if label.lower() == "entailment"
    )
    scores = []
    with torch.inference_mode():
        for start in range(0, len(pairs), batch_size):
            batch = pairs[start : start + batch_size]
            encoded = tokenizer(
                [premise for premise, _ in batch],
                [hypothesis for _, hypothesis in batch],
                padding=True,
                truncation="only_first",
                max_length=512,
                return_tensors="pt",
            )
            probabilities = model(**encoded).logits.softmax(dim=-1)[:, entailment_id]
            scores.extend(float(value) for value in probabilities)
    return scores


def audit(input_path: Path, output_path: Path, model_dir: Path, batch_size: int, only_prescreen: bool) -> dict:
    prepare = load_prepare_module()
    records = read_jsonl(input_path)
    if only_prescreen:
        selected_ids = {row["instance_id"] for row in read_jsonl(PRESCREEN_PATH)}
        records = [row for row in records if row["instance_id"] in selected_ids]

    pair_metadata = []
    pairs = []
    for record in records:
        for source_field, context_field in (
            ("original_triplet", "context1"),
            ("perturb_triplet", "context2"),
        ):
            for fact_index, triplet in enumerate(prepare.triplet_list(record[source_field])):
                hypothesis = fact_hypothesis(triplet, prepare)
                pair_metadata.append(
                    {
                        "instance_id": record["instance_id"],
                        "selection_role": record["selection_role"],
                        "source_field": source_field,
                        "context_field": context_field,
                        "fact_index": fact_index,
                        "triplet": triplet,
                        "hypothesis": hypothesis,
                    }
                )
                pairs.append((record[context_field], hypothesis))

    scores = score_pairs(pairs, model_dir, batch_size)
    by_instance = {}
    for metadata, score in zip(pair_metadata, scores, strict=True):
        instance = by_instance.setdefault(
            metadata["instance_id"],
            {
                "instance_id": metadata["instance_id"],
                "selection_role": metadata["selection_role"],
                "model": "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli",
                "model_fingerprint": model_fingerprint(model_dir),
                "gold": False,
                "facts": [],
            },
        )
        metadata["entailment_probability"] = round(score, 6)
        instance["facts"].append(metadata)

    rows = []
    for instance in by_instance.values():
        probabilities = [fact["entailment_probability"] for fact in instance["facts"]]
        instance["min_entailment_probability"] = min(probabilities)
        instance["facts_below_0_50"] = sum(value < 0.50 for value in probabilities)
        instance["facts_below_0_80"] = sum(value < 0.80 for value in probabilities)
        rows.append(instance)
    rows.sort(key=lambda row: row["instance_id"])
    write_jsonl(output_path, rows)
    return {
        "instances": len(rows),
        "facts": len(pair_metadata),
        "below_0_50": sum(row["facts_below_0_50"] for row in rows),
        "output": str(output_path),
        "warning": "NLI is a triage signal, not a gold label.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--only-prescreen", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            audit(args.input, args.output, args.model, args.batch_size, args.only_prescreen),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
