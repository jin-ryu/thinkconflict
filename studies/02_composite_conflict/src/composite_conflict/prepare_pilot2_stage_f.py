"""Freeze the Stage F H2 atomic probe set from the matched Pilot 2 inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h2-instances", type=Path, required=True)
    parser.add_argument("--all-probes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    h2_ids = {row["instance_id"] for row in load_jsonl(args.h2_instances)}
    probes = [
        row
        for row in load_jsonl(args.all_probes)
        if row.get("parent_instance_id") in h2_ids
    ]

    expected = 2 * len(h2_ids)
    if len(probes) != expected:
        raise ValueError(f"Expected {expected} H2 probes, found {len(probes)}")

    parent_counts: dict[str, int] = {}
    for probe in probes:
        parent = probe["parent_instance_id"]
        parent_counts[parent] = parent_counts.get(parent, 0) + 1
    malformed = {parent: count for parent, count in parent_counts.items() if count != 2}
    if malformed:
        raise ValueError(f"Each H2 parent must have two probes: {malformed}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        for row in probes:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps({"h2_parents": len(h2_ids), "atomic_probes": len(probes)}, indent=2))


if __name__ == "__main__":
    main()
