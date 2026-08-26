"""Pre-register the blind 20% Human-B audit before LLM/Human-A labels exist."""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from .schema import blank_annotation, read_jsonl, write_jsonl

STUDY_ROOT = Path(__file__).resolve().parents[2]
PILOT_ROOT = STUDY_ROOT / "data" / "pilot1"
AUDIT_SEED_OFFSET = 1


def _sample(records: list[dict], fraction: float, rng: random.Random) -> list[dict]:
    count = math.ceil(len(records) * fraction)
    return rng.sample(records, count)


def prepare(fraction: float = 0.20) -> dict:
    if not 0 < fraction < 1:
        raise ValueError("fraction must be between 0 and 1")
    manifest_path = PILOT_ROOT / "sample_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    seed = int(manifest["seed"]) + AUDIT_SEED_OFFSET
    rng = random.Random(seed)

    calibration_ids = {
        record["instance_id"] for record in read_jsonl(PILOT_ROOT / "calibration_view.jsonl")
    }
    sources = {
        "confrag": list(read_jsonl(PILOT_ROOT / "confrag_prevalence_view.jsonl")),
        "natconfqa": list(read_jsonl(PILOT_ROOT / "natconfqa_strict_wh_mix_view.jsonl")),
        "qacc": list(read_jsonl(PILOT_ROOT / "qacc_control_view.jsonl")),
    }
    eligible = {
        dataset: [record for record in records if record["instance_id"] not in calibration_ids]
        for dataset, records in sources.items()
    }
    selected_by_dataset = {
        dataset: _sample(records, fraction, rng) for dataset, records in eligible.items()
    }
    selected = [
        record
        for dataset in ("confrag", "natconfqa", "qacc")
        for record in selected_by_dataset[dataset]
    ]
    write_jsonl(selected, PILOT_ROOT / "human_B_random_audit_view.jsonl")
    audit_annotation_path = PILOT_ROOT / "human_B_random_audit.jsonl"
    if not audit_annotation_path.exists():
        write_jsonl(
            [blank_annotation(record["instance_id"], "B") for record in selected],
            audit_annotation_path,
        )

    manifest["human_b_random_audit"] = {
        "seed": seed,
        "fraction": fraction,
        "calibration_ids_excluded": True,
        "eligible_counts": {dataset: len(records) for dataset, records in eligible.items()},
        "selected_counts": {
            dataset: len(records) for dataset, records in selected_by_dataset.items()
        },
        "instance_ids": [record["instance_id"] for record in selected],
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest["human_b_random_audit"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fraction", type=float, default=0.20)
    args = parser.parse_args()
    print(json.dumps(prepare(args.fraction), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
