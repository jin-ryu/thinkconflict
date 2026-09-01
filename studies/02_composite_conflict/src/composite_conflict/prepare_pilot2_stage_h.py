"""Freeze an outcome-blind, cell-balanced Stage H intervention screen."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def score(seed: int, base_id: str) -> str:
    return hashlib.sha256(f"{seed}:{base_id}".encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--per-cell", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--orders", nargs="+", choices=("original", "reverse", "interleaved"))
    args = parser.parse_args()

    rows = load_jsonl(args.inputs)
    if args.orders:
        rows = [row for row in rows if row["order_variant"] in set(args.orders)]
    bases_by_cell: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        bases_by_cell[f"K{row['K']}_H{row['H']}"] .add(row["base_instance_id"])

    selected: set[str] = set()
    selected_by_cell: dict[str, list[str]] = {}
    for cell, base_ids in sorted(bases_by_cell.items()):
        ranked = sorted(base_ids, key=lambda base_id: (score(args.seed, base_id), base_id))
        if len(ranked) < args.per_cell:
            raise ValueError(f"{cell}: need {args.per_cell}, have {len(ranked)}")
        chosen = ranked[: args.per_cell]
        selected.update(chosen)
        selected_by_cell[cell] = chosen

    output = [row for row in rows if row["base_instance_id"] in selected]
    output.sort(key=lambda row: row["instance_id"])
    base_counts = Counter(row["base_instance_id"] for row in output)
    expected_orders = len(args.orders) if args.orders else 3
    if set(base_counts.values()) != {expected_orders}:
        raise ValueError(f"every selected base must have exactly {expected_orders} order variants")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        for row in output:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "protocol": "stage-h-outcome-blind-screen-v1",
        "source": str(args.inputs),
        "seed": args.seed,
        "included_orders": args.orders or ["original", "reverse", "interleaved"],
        "selection_key": "sha256(seed:base_instance_id); no model outcome used",
        "per_cell": args.per_cell,
        "base_instances": len(selected),
        "order_trials": len(output),
        "selected_by_cell": selected_by_cell,
        "cell_order_counts": dict(sorted(Counter(f"K{r['K']}_H{r['H']}" for r in output).items())),
        "order_counts": dict(sorted(Counter(r["order_variant"] for r in output).items())),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: manifest[key] for key in ("base_instances", "order_trials", "cell_order_counts", "order_counts")}, indent=2))


if __name__ == "__main__":
    main()
