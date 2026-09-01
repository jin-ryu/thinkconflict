"""Materialize the audited semantic judgments for Pilot 2 core conditions."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


CORE_CONDITIONS = {"direct", "generic_cot", "oracle_unit_policies"}

FAILURES = {
    ("direct", "4cbe1c3d-78c2-df45-ba61-72ebc35b4d40:S50:Q_002+Q_004"): ("wrong_condition_application", "The response rejected the gold stress-relief activity and imported a different preference."),
    ("direct", "5c2a85a4-05a5-5a54-5f50-8029bff79f8f:S44:Q_003+Q_007"): ("wrong_preference_selection", "It used the tropical-getaway alternative instead of selecting the budget-hostel condition."),
    ("direct", "75b15745-6d32-726b-be79-d765808bbfe7:S34:Q_002+Q_003"): ("wrong_preference_selection", "It chose a dark crime movie instead of the friends-setting Hollywood-blockbuster preference."),
    ("direct", "c2efaebe-0dd4-c0dc-23a5-7d713b14c99f:S51:Q_002+Q_007"): ("condition_over_preservation", "It returned both herbal and chrysanthemum tea instead of selecting the virtual-book-club preference."),
    ("direct", "d65aae82-db00-00c3-3714-6eb500f83f5b:S45:Q_004+Q_005"): ("stale_state", "It treated the prior Free status as current and recommended hiking now despite the Busy update."),
    ("generic_cot", "2e62aacf-70e2-3d5a-b6bd-6f9ad776893d:S29:Q_003+Q_008"): ("wrong_preference_selection", "It selected business books rather than the professional-development Philosophy Text preference."),
    ("generic_cot", "c2efaebe-0dd4-c0dc-23a5-7d713b14c99f:S51:Q_002+Q_007"): ("wrong_preference_selection", "It selected chrysanthemum tea rather than Herbal Tea for the virtual book club."),
    ("generic_cot", "f398d596-a91e-2afd-605f-be545475deca:S48:Q_002+Q_003"): ("cross_unit_contamination", "It selected cycling and cargo pants instead of the workout and breathable-tank preference."),
    ("generic_cot", "4f76dbf9-4a2f-5790-c6e0-7278de3b8ad8:S29:Q_005+Q_006"): ("wrong_preference_selection", "It selected Luxury Resort instead of Five-star Hotel for the friends-travel condition."),
    ("generic_cot", "575f4af8-5ca4-716c-dfed-0f495c945e0b:S47:Q_002+Q_003"): ("cross_unit_contamination", "It replaced the gold sashimi dinner with unrelated food memories."),
    ("oracle_unit_policies", "575f4af8-5ca4-716c-dfed-0f495c945e0b:S47:Q_002+Q_003"): ("cross_unit_contamination", "Even with oracle policies, it ignored the unit evidence for sashimi and imported unrelated food memories."),
}


def load_jsonl(path: Path) -> list[dict]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--lexical", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    args = parser.parse_args()

    lexical = {row["run_id"]: row for row in load_jsonl(args.lexical)}
    outputs = [row for row in load_jsonl(args.outputs) if row["baseline_condition"] in CORE_CONDITIONS]
    judgments = []
    for row in outputs:
        key = (row["baseline_condition"], row["instance_id"])
        failure = FAILURES.get(key)
        automatic = lexical[row["run_id"]]["automatic_all_unit_success"]
        judgments.append({
            "run_id": row["run_id"],
            "instance_id": row["instance_id"],
            "H": row["H"],
            "baseline_condition": row["baseline_condition"],
            "semantic_all_unit_success": failure is None,
            "error_type": failure[0] if failure else None,
            "rationale": failure[1] if failure else "Both gold units are resolved and composed in the final answer.",
            "review_route": "Codex semantic review" if (row["baseline_condition"] == "direct" or not automatic) else "high-confidence lexical pass",
            "judge": {
                "name": "OpenAI Codex interactive agent",
                "model_family": "GPT-5-based Codex",
                "deployment_checkpoint": "not exposed by the interface",
                "protocol": "pilot2-semantic-core-v1",
                "intended_use": "exploratory pilot",
            },
        })

    args.judgments.parent.mkdir(parents=True, exist_ok=True)
    with args.judgments.open("w") as handle:
        for row in judgments:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    buckets = defaultdict(lambda: {"n": 0, "success": 0})
    for row in judgments:
        key = f"H{row['H']}::{row['baseline_condition']}"
        buckets[key]["n"] += 1
        buckets[key]["success"] += int(row["semantic_all_unit_success"])
    metrics = {
        key: {**value, "rate": round(value["success"] / value["n"], 4)}
        for key, value in sorted(buckets.items())
    }
    metrics["descriptive_deltas_h2_minus_h1"] = {
        condition: round(
            metrics[f"H2::{condition}"]["rate"] - metrics[f"H1::{condition}"]["rate"], 4
        )
        for condition in sorted(CORE_CONDITIONS)
    }
    metrics["caveat"] = "Descriptive feasibility-set statistics; not a matched causal estimate. High-confidence lexical passes outside Direct were not all independently re-read by Codex."
    args.metrics.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
