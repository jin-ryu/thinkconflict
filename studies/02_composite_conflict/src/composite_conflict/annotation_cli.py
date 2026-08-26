"""Finalize derived K/H fields and validate Pilot-1 annotation JSONL files."""
from __future__ import annotations

import argparse
from pathlib import Path

from .schema import (
    document_ids,
    finalize_annotation,
    read_jsonl,
    validate_annotation,
    write_jsonl,
)


def _index(records: list[dict], label: str) -> dict[str, dict]:
    indexed = {record["instance_id"]: record for record in records}
    if len(indexed) != len(records):
        raise ValueError(f"{label}: duplicate instance_id")
    return indexed


def finalize_file(source: Path, output: Path) -> None:
    records = [finalize_annotation(record) for record in read_jsonl(source)]
    write_jsonl(records, output)
    print(f"finalized {len(records)} annotations -> {output}")


def validate_file(view_path: Path, annotation_path: Path, require_complete: bool) -> int:
    views = _index(list(read_jsonl(view_path)), str(view_path))
    annotations = _index(list(read_jsonl(annotation_path)), str(annotation_path))
    errors = []
    missing = set(views) - set(annotations)
    extra = set(annotations) - set(views)
    if missing:
        errors.append(f"missing annotations: {sorted(missing)}")
    if extra:
        errors.append(f"unknown annotations: {sorted(extra)}")
    for instance_id in sorted(set(views) & set(annotations)):
        for error in validate_annotation(
            annotations[instance_id],
            valid_doc_ids=document_ids(views[instance_id]),
            require_complete=require_complete,
        ):
            errors.append(f"{instance_id}: {error}")
    for error in errors:
        print(f"ERROR {error}")
    if errors:
        print(f"validation failed: {len(errors)} errors")
        return 1
    print(f"validation passed: {len(annotations)} annotations")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    finalize_parser = subparsers.add_parser("finalize", help="derive K/H and write a new file")
    finalize_parser.add_argument("--annotations", required=True, type=Path)
    finalize_parser.add_argument("--out", required=True, type=Path)

    validate_parser = subparsers.add_parser("validate", help="validate against an annotation view")
    validate_parser.add_argument("--view", required=True, type=Path)
    validate_parser.add_argument("--annotations", required=True, type=Path)
    validate_parser.add_argument("--require-complete", action="store_true")

    args = parser.parse_args()
    if args.command == "finalize":
        finalize_file(args.annotations, args.out)
        return
    raise SystemExit(validate_file(args.view, args.annotations, args.require_complete))


if __name__ == "__main__":
    main()
