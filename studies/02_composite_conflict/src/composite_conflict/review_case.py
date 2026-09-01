"""Print one Pilot-1 case, its evidence, and the LLM draft for human review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .schema import read_jsonl


def _by_id(path: str | Path) -> dict[str, dict]:
    return {record["instance_id"]: record for record in read_jsonl(path)}


def _clip(value: str, limit: int) -> str:
    value = " ".join((value or "").split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def render_case(view: dict, draft: dict, preview_chars: int = 1200) -> str:
    lines = [
        f"INSTANCE: {view['instance_id']} ({view.get('dataset', '')})",
        f"QUESTION: {view.get('question', '')}",
        "",
        "ANSWER CANDIDATES",
    ]
    candidates = view.get("answer_candidates", [])
    if not candidates:
        lines.append("  (none supplied; infer claims from documents)")
    for index, candidate in enumerate(candidates, start=1):
        lines.append(
            f"  A{index} docs={candidate.get('doc_ids', [])}: "
            f"{candidate.get('answer', '')}"
        )

    lines.extend(["", "DOCUMENTS"])
    for document in view.get("documents", []):
        header = f"  DOC {document['doc_id']}"
        if document.get("title"):
            header += f" | {document['title']}"
        if document.get("date"):
            header += f" | {document['date']}"
        if document.get("url"):
            header += f" | {document['url']}"
        lines.extend([header, "    " + _clip(document.get("content_preview", ""), preview_chars)])

    lines.extend(
        [
            "",
            "LLM DRAFT",
            json.dumps(draft, ensure_ascii=False, indent=2),
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", default="data/pilot1_search/calibration_view.jsonl")
    parser.add_argument("--drafts", default="data/pilot1_search/llm_drafts_calibration.jsonl")
    parser.add_argument("--instance-id")
    parser.add_argument("--list", action="store_true", dest="list_instances")
    parser.add_argument("--preview-chars", type=int, default=1200)
    args = parser.parse_args()

    views = _by_id(args.view)
    drafts = _by_id(args.drafts)
    if args.list_instances:
        for instance_id in views:
            marker = "draft" if instance_id in drafts else "missing-draft"
            print(f"{instance_id}\t{marker}")
        return
    if not args.instance_id:
        parser.error("provide --instance-id or --list")
    if args.instance_id not in views:
        parser.error(f"unknown instance ID: {args.instance_id}")
    if args.instance_id not in drafts:
        parser.error(f"missing draft for: {args.instance_id}")
    print(render_case(views[args.instance_id], drafts[args.instance_id], args.preview_chars))


if __name__ == "__main__":
    main()
