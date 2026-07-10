"""RAMDocs 전처리: 라벨 승계 + A/B 분리 (계획서 Phase 1-1, §3.1.2).

RAMDocs는 문서별 `type`(correct/misinfo/noise)과 gold/wrong answers가 원본에
라벨돼 있어 골드 매핑이 불필요하다 — 라벨을 그대로 승계만 한다(가장 기계적).

A/B 분리:
    ramdocs_b.jsonl — 원본 결합형(모호성+오정보+노이즈 공존). 향후 과제용 보관.
    ramdocs_a.jsonl — 분해형(충돌 1요인). 본 실험용. 원본은 '복수 정답(모호성)'과
        '오정보 충돌' 두 요인이 결합돼 있어 전환 행렬 해석이 흐려지므로,
        gold answer 단위로 분해해 각 하위 문항이 오정보 충돌 1요인만 갖게 한다:
        하위 문항 i = {정답 a_i 지지 문서(correct) + misinfo 문서(conflicting) + noise 문서}.
        오정보가 없는 문항(노이즈만)은 conflict_type="none"으로 유지 — RQ3의
        within-item(misinfo↔noise) 대조에서 비충돌 조건을 담당한다.

usage: python -m preprocessing.ramdocs_prep [--raw-dir data/raw/ramdocs] [--out-dir data/processed]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from preprocessing.schema import Chunk, Item, write_jsonl

TYPE_TO_LABEL = {"correct": "correct", "misinfo": "conflicting", "noise": "noise"}


def load_raw(raw_dir: Path) -> list[dict]:
    """HF 스냅샷에서 test set을 찾아 로드한다 (json/jsonl 자동 탐색)."""
    candidates = sorted(list(raw_dir.rglob("*.jsonl")) + list(raw_dir.rglob("*.json")))
    candidates = [p for p in candidates if ".cache" not in p.parts]
    if not candidates:
        raise FileNotFoundError(f"{raw_dir}에 원본 파일 없음 — data/raw/download.sh 먼저 실행")
    path = candidates[0]
    rows = []
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    if path.suffix == ".jsonl" or "\n{" in text:
        rows = [json.loads(l) for l in text.splitlines() if l.strip()]
    else:
        data = json.loads(text)
        rows = data if isinstance(data, list) else data.get("data", [])
    print(f"원본 로드: {path} (N={len(rows)})")
    return rows


def to_chunks(docs: list[dict]) -> list[Chunk]:
    return [
        Chunk(doc_id=i, text=d["text"], label=TYPE_TO_LABEL[d["type"]],
              supported_answer=d.get("answer"))
        for i, d in enumerate(docs)
    ]


def conflict_type_of(row: dict) -> str:
    has_misinfo = any(d["type"] == "misinfo" for d in row["documents"])
    multi_gold = len(row.get("gold_answers", [])) > 1
    if has_misinfo:
        return "misinfo"
    return "ambiguous" if multi_gold else "none"


def build_b(rows: list[dict]) -> list[Item]:
    """원본 결합형: 문항 구조 그대로, any-gold 정답 집합 승계."""
    items = []
    for i, row in enumerate(rows):
        items.append(Item(
            question_id=f"ramdocs-{i:04d}",
            dataset="ramdocs_b",
            question=row["question"],
            conflict_type=conflict_type_of(row),
            correct_answers=list(row.get("gold_answers", [])),
            wrong_answers=list(row.get("wrong_answers", [])),
            chunks=to_chunks(row["documents"]),
            behavior_track=bool(row.get("gold_answers")),
            self_consistency_track=True,
            meta={"source_row": i},
        ))
    return items


def build_a(rows: list[dict]) -> list[Item]:
    """분해형: gold answer 단위로 분해해 충돌 요인을 오정보 하나로 고정."""
    items = []
    for i, row in enumerate(rows):
        docs = row["documents"]
        misinfo = [d for d in docs if d["type"] == "misinfo"]
        noise = [d for d in docs if d["type"] == "noise"]
        golds = list(row.get("gold_answers", []))
        for j, gold in enumerate(golds or [None]):
            support = [d for d in docs if d["type"] == "correct"
                       and (gold is None or d.get("answer") == gold)]
            if gold is not None and not support:
                continue  # 지지 문서 없는 gold는 하위 문항 성립 불가 (건수는 집계에 반영)
            sub = support + misinfo + noise
            items.append(Item(
                question_id=f"ramdocs-{i:04d}-a{j}",
                dataset="ramdocs_a",
                question=row["question"],
                conflict_type="misinfo" if misinfo else "none",
                correct_answers=[gold] if gold else [],
                wrong_answers=list(row.get("wrong_answers", [])),
                chunks=to_chunks(sub),
                behavior_track=gold is not None,
                self_consistency_track=True,
                meta={"source_row": i, "gold_index": j,
                      "original_gold_answers": golds},
            ))
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/raw/ramdocs", type=Path)
    ap.add_argument("--out-dir", default="data/processed", type=Path)
    args = ap.parse_args()
    rows = load_raw(args.raw_dir)
    a, b = build_a(rows), build_b(rows)
    write_jsonl(a, args.out_dir / "ramdocs_a.jsonl")
    write_jsonl(b, args.out_dir / "ramdocs_b.jsonl")
    n_conf = sum(1 for it in a if it.conflict_type == "misinfo")
    print(f"ramdocs_a: N={len(a)} (오정보 충돌 {n_conf} / 비충돌 {len(a) - n_conf})")
    print(f"ramdocs_b: N={len(b)}")


if __name__ == "__main__":
    main()
