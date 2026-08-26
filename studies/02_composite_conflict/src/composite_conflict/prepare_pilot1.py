"""Create deterministic Pilot-1 manifests and label-hidden annotation views."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from .schema import blank_annotation, write_jsonl

STUDY_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = STUDY_ROOT.parents[1]
RAW_ROOT = STUDY_ROOT / "data" / "raw"
PILOT_ROOT = STUDY_ROOT / "data" / "pilot1"
AIR_QACC_ROOT = REPO_ROOT / "studies" / "01_air_trace" / "data" / "3_processed" / "qacc"
SEED = 20260826
PREVIEW_CHARS = 2400


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_revision(path: Path) -> str:
    head = (path / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        ref = path / ".git" / head[5:]
        if ref.exists():
            return ref.read_text(encoding="utf-8").strip()
        packed = (path / ".git" / "packed-refs").read_text(encoding="utf-8")
        for line in packed.splitlines():
            if line.endswith(" " + head[5:]):
                return line.split()[0]
    return head


def load_confrag() -> list[dict]:
    path = RAW_ROOT / "confrag" / "ConfRAGsuggested.jsonl"
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def confrag_view(record: dict) -> dict:
    documents = []
    for website in record.get("websites", []):
        content = website.get("content") or ""
        documents.append(
            {
                "doc_id": str(website.get("index")),
                "url": website.get("website"),
                "provided_answer": website.get("answer"),
                "provided_reasons": website.get("reason", []),
                "trust_score": website.get("trust_score"),
                "content_preview": content[:PREVIEW_CHARS],
                "content_chars": len(content),
            }
        )
    return {
        "instance_id": f"confrag-{record['id']}",
        "dataset": "confrag",
        "source_id": str(record["id"]),
        "question": record["question"],
        "source": record.get("from"),
        "documents": documents,
        "answer_candidates": [
            {
                "answer": answer.get("answer"),
                "doc_ids": [str(value) for value in answer.get("index", [])],
                "reasons": answer.get("reason", []),
            }
            for answer in record.get("answers", [])
        ],
        "raw_locator": "data/raw/confrag/ConfRAGsuggested.jsonl",
        "source_labels_hidden": ["contradicts"],
    }


def load_natconfqa() -> list[dict]:
    path = RAW_ROOT / "natconfqa" / "data" / "v1.0" / "ContraQA.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)["ContraQA"]


def _strict_wh_mix(record: dict) -> bool:
    if record.get("answer_type") != "Conflict" or not record.get("question_type", "").startswith("wh-"):
        return False
    answer_count = len(record.get("answers", []))
    pair_count = answer_count * (answer_count - 1) // 2
    conflict_count = len(record.get("conflicting_answer_pairs", []))
    return 0 < conflict_count < pair_count


def natconfqa_view(record: dict) -> dict:
    evidences = record.get("evidences", [])

    def answer_doc_ids(answer: dict) -> list[str]:
        """Map NatConfQA evidence indices to paragraph/document IDs.

        ``answers[*].evidence_ids`` indexes the ``evidences`` array; it is not
        a paragraph ID. Exposing those indices as doc IDs can therefore point
        outside the view's document set and attach an answer to the wrong text.
        """
        paragraph_ids = {
            evidences[evidence_id]["paragraph_id"]
            for evidence_id in answer.get("evidence_ids", [])
            if 0 <= evidence_id < len(evidences)
        }
        return [str(value) for value in sorted(paragraph_ids)]
    documents = []
    for index, paragraph in enumerate(record.get("paragraphs", [])):
        documents.append(
            {
                "doc_id": str(index),
                "content_preview": paragraph[:PREVIEW_CHARS],
                "content_chars": len(paragraph),
            }
        )
    return {
        "instance_id": f"natconfqa-{record['question_id']}",
        "dataset": "natconfqa",
        "source_id": record["question_id"],
        "question": record["question"],
        "source": record.get("topic_id"),
        "documents": documents,
        "answer_candidates": [
            {
                "answer_id": str(index),
                "answer": answer.get("answer"),
                "source_evidence_ids": answer.get("evidence_ids", []),
                "doc_ids": answer_doc_ids(answer),
            }
            for index, answer in enumerate(record.get("answers", []))
        ],
        "raw_locator": "data/raw/natconfqa/data/v1.0/ContraQA.json",
        "source_labels_hidden": ["answer_type", "conflicting_answer_pairs", "evidence.label"],
    }


def load_qacc() -> list[dict]:
    records = []
    for path in sorted(AIR_QACC_ROOT.glob("qacc_*.jsonl")):
        if "conflicting_opinions" in path.name:
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    record = json.loads(line)
                    record["_source_file"] = path.name
                    records.append(record)
    unique = {record["question_id"]: record for record in records}
    return list(unique.values())


def qacc_view(record: dict) -> dict:
    documents = []
    for chunk in record.get("chunks", []):
        documents.append(
            {
                "doc_id": str(chunk["doc_id"]),
                "url": chunk.get("url"),
                "title": chunk.get("title"),
                "date": chunk.get("date"),
                "content_preview": (chunk.get("text") or "")[:PREVIEW_CHARS],
                "content_chars": len(chunk.get("text") or ""),
            }
        )
    return {
        "instance_id": record["question_id"],
        "dataset": "qacc",
        "source_id": record["question_id"],
        "question": record["question"],
        "source": record.get("_source_file"),
        "documents": documents,
        "answer_candidates": [],
        "raw_locator": f"../01_air_trace/data/3_processed/qacc/{record.get('_source_file')}",
        "source_labels_hidden": ["correct_answers", "chunk.label", "chunk.supported_answer"],
    }


def _sample(records: list[dict], count: int, rng: random.Random) -> list[dict]:
    if len(records) < count:
        raise ValueError(f"cannot sample {count} from {len(records)} records")
    return rng.sample(records, count)


def _write_annotation_templates(views: list[dict]) -> None:
    for annotator in ("A", "B"):
        path = PILOT_ROOT / f"calibration_annotations_{annotator}.jsonl"
        if path.exists():
            continue
        write_jsonl(
            [blank_annotation(view["instance_id"], annotator) for view in views],
            path,
        )


def prepare() -> dict:
    rng = random.Random(SEED)
    confrag = load_confrag()
    natconfqa = load_natconfqa()
    qacc = load_qacc()

    confrag_true = [record for record in confrag if record.get("contradicts")]
    confrag_false = [record for record in confrag if not record.get("contradicts")]
    calibration_confrag = _sample(confrag_true, 8, rng) + _sample(confrag_false, 4, rng)
    calibration_confrag_ids = {record["id"] for record in calibration_confrag}
    prevalence_confrag = _sample(
        [record for record in confrag if record["id"] not in calibration_confrag_ids], 120, rng
    )

    nat_conflict_wh = [
        record
        for record in natconfqa
        if record.get("answer_type") == "Conflict"
        and record.get("question_type", "").startswith("wh-")
    ]
    nat_strict_mix = [record for record in nat_conflict_wh if _strict_wh_mix(record)]
    nat_calibration_pool = sorted(
        nat_conflict_wh,
        key=lambda record: (len(record.get("answers", [])), record["question_id"]),
        reverse=True,
    )
    calibration_nat = nat_calibration_pool[:4]

    qacc_by_source: dict[str, list[dict]] = {}
    for record in qacc:
        qacc_by_source.setdefault(record["_source_file"], []).append(record)
    calibration_qacc = []
    for source in sorted(qacc_by_source):
        calibration_qacc.extend(_sample(qacc_by_source[source], min(2, len(qacc_by_source[source])), rng))
    calibration_qacc = calibration_qacc[:4]
    calibration_qacc_ids = {record["question_id"] for record in calibration_qacc}
    control_qacc = _sample(
        [record for record in qacc if record["question_id"] not in calibration_qacc_ids], 60, rng
    )

    calibration_views = (
        [confrag_view(record) for record in calibration_confrag]
        + [natconfqa_view(record) for record in calibration_nat]
        + [qacc_view(record) for record in calibration_qacc]
    )
    prevalence_views = [confrag_view(record) for record in prevalence_confrag]
    nat_views = [natconfqa_view(record) for record in nat_strict_mix]
    qacc_views = [qacc_view(record) for record in control_qacc]

    PILOT_ROOT.mkdir(parents=True, exist_ok=True)
    write_jsonl(calibration_views, PILOT_ROOT / "calibration_view.jsonl")
    write_jsonl(prevalence_views, PILOT_ROOT / "confrag_prevalence_view.jsonl")
    write_jsonl(nat_views, PILOT_ROOT / "natconfqa_strict_wh_mix_view.jsonl")
    write_jsonl(qacc_views, PILOT_ROOT / "qacc_control_view.jsonl")
    _write_annotation_templates(calibration_views)

    selections = []
    for role, views in (
        ("calibration", calibration_views),
        ("confrag_prevalence", prevalence_views),
        ("natconfqa_strict_wh_mix", nat_views),
        ("qacc_control", qacc_views),
    ):
        selections.extend({"instance_id": view["instance_id"], "role": role} for view in views)
    manifest = {
        "manifest_version": "pilot1-sampling-v1",
        "seed": SEED,
        "source_counts": {
            "confrag_suggested": len(confrag),
            "natconfqa_all": len(natconfqa),
            "natconfqa_conflict_wh": len(nat_conflict_wh),
            "natconfqa_strict_wh_mix": len(nat_strict_mix),
            "qacc_factual": len(qacc),
        },
        "selection_counts": dict(Counter(item["role"] for item in selections)),
        "selections": selections,
        "notes": [
            "Calibration is coverage-oriented and excluded from ConfRAG/QACC prevalence samples.",
            "NatConfQA strict WH-mix means at least one conflicting and one non-conflicting answer pair.",
            "Source conflict labels are omitted from all annotation views.",
        ],
    }
    (PILOT_ROOT / "sample_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    source_manifest = {
        "snapshot_version": "pilot1-sources-v1",
        "sources": {
            "confrag": {
                "url": "https://huggingface.co/datasets/OracleY/ConfRAG",
                "revision": _git_revision(RAW_ROOT / "confrag"),
                "file": "ConfRAGsuggested.jsonl",
                "sha256": _sha256(RAW_ROOT / "confrag" / "ConfRAGsuggested.jsonl"),
                "records": len(confrag),
                "license": "CC BY 4.0",
            },
            "natconfqa": {
                "url": "https://github.com/EN555/ContraQA",
                "revision": _git_revision(RAW_ROOT / "natconfqa"),
                "file": "data/v1.0/ContraQA.json",
                "sha256": _sha256(RAW_ROOT / "natconfqa" / "data" / "v1.0" / "ContraQA.json"),
                "records": len(natconfqa),
                "license": "repository contains no explicit license file; verify before redistribution",
            },
            "qacc": {
                "source": "studies/01_air_trace/data/3_processed/qacc",
                "records": len(qacc),
                "license": "CC BY-SA 3.0; see AIR raw licenses",
            },
        },
    }
    (STUDY_ROOT / "data" / "source_snapshots.json").write_text(
        json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    manifest = prepare()
    print(json.dumps({"source_counts": manifest["source_counts"], "selection_counts": manifest["selection_counts"]}, indent=2))


if __name__ == "__main__":
    main()
