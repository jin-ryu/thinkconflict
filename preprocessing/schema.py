"""공통 스키마 정의 + 검증 (계획서 §3.1, Phase 0-4).

세 데이터셋(DRAGged·QACC·RAMDocs)을 하나의 스키마로 정규화한다. 데이터셋은
분리 보고가 원칙이므로 스키마는 공유하되 `dataset` 필드로 항상 구분한다.

문서(chunk) 라벨:
    correct     — 정답을 지지하는 유효 문서
    conflict    — 정답과 상충하는 문서 (구버전·오정보·반대 관점)
    noise       — 질문과 무관하거나 어느 답도 지지하지 않는 문서
    unknown     — 미확정 (골드 매핑 전 초안 상태에서만 허용)

트랙(사전등록 §1.8 이중 트랙):
    behavior         — 정답 채점(정확도·AIR) 트랙 투입 가능 (scorable)
    self_consistency — 트레이스 입장↔답변 자기일관성 트랙 (정답 불요)
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterator

DATASETS = ("dragged", "qacc", "ramdocs_a", "ramdocs_b")
CONFLICT_TYPES = ("temporal", "misinfo", "opinion", "complementary", "none", "ambiguous")
CHUNK_LABELS = ("correct", "conflict", "noise", "unknown")


@dataclass
class Chunk:
    doc_id: int
    text: str
    label: str = "unknown"
    date: str | None = None            # ISO-8601 권장; 최신성 해소 규칙의 근거
    url: str | None = None             # 권위 대조의 근거 (RAMDocs는 None)
    title: str | None = None
    supported_answer: str | None = None  # 이 문서가 지지하는 답 (QACC 귀속 주석 / RAMDocs answer)


@dataclass
class Item:
    question_id: str                   # "{dataset}-{원본 인덱스:04d}" — 환경 간 짝짓기 키
    dataset: str
    question: str
    conflict_type: str
    correct_answers: list[str]         # any-gold: 이 중 하나면 correct (사전등록 §1.5)
    # 문서에 실린 '틀린 답'들. 채점(FA 라벨)에는 쓰이지 않는다 — 오답은 어차피 wrong이다.
    # 용도는 부가 관측 하나뿐: 모델이 오정보 문서의 답을 그대로 삼켰는지(adopted_wrong_answer)와
    # 엉뚱한 답을 지어냈는지를 가른다. 원본이 주는 데이터셋에서만 채워진다:
    # RAMDocs(gold/wrong 내장) · QACC(다른 후보 답) · DRAGged는 원본에 없어 빈 리스트.
    wrong_answers: list[str] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    behavior_track: bool = False       # 채점 가능 (사실 충돌 + 골드 매핑 확정)
    self_consistency_track: bool = False
    exclusion_flag: str | None = None  # 예: "no_match", "date_tie" — L2 의존 지표 제외 사유
    meta: dict = field(default_factory=dict)  # 원본 필드 보존 (source_row, mapping_provenance 등)


# ── 직렬화 ────────────────────────────────────────────────────────────────────

def item_to_dict(item: Item) -> dict:
    return asdict(item)


def item_from_dict(d: dict) -> Item:
    d = dict(d)
    d["chunks"] = [Chunk(**c) for c in d.get("chunks", [])]
    return Item(**d)


def write_jsonl(items: list[Item], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(item_to_dict(it), ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> Iterator[Item]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield item_from_dict(json.loads(line))


# ── 검증 ──────────────────────────────────────────────────────────────────────

def validate_item(item: Item) -> list[str]:
    """스키마 위반 목록을 반환한다 (빈 리스트 = 통과)."""
    errs = []
    if item.dataset not in DATASETS:
        errs.append(f"dataset '{item.dataset}' not in {DATASETS}")
    if item.conflict_type not in CONFLICT_TYPES:
        errs.append(f"conflict_type '{item.conflict_type}' not in {CONFLICT_TYPES}")
    if not item.question.strip():
        errs.append("question is empty")
    if not item.question_id.startswith(item.dataset.split("_")[0]):
        errs.append(f"question_id '{item.question_id}' does not carry dataset prefix")
    if not item.chunks:
        errs.append("chunks is empty")
    for c in item.chunks:
        if c.label not in CHUNK_LABELS:
            errs.append(f"chunk {c.doc_id}: label '{c.label}' not in {CHUNK_LABELS}")
        if not c.text.strip():
            errs.append(f"chunk {c.doc_id}: text is empty")
    if item.behavior_track:
        if not item.correct_answers:
            errs.append("behavior_track requires correct_answers (any-gold set)")
        if any(c.label == "unknown" for c in item.chunks):
            errs.append("behavior_track requires finalized chunk labels (no 'unknown')")
        if item.exclusion_flag:
            errs.append(f"behavior_track item carries exclusion_flag '{item.exclusion_flag}'")
    return errs


def assert_reviewed(path: str | Path) -> None:
    """실험 입력이 검토 완료본인지 확인한다.

    `data/review/`의 초안(CSV·draft)은 라벨이 미확정일 수 있으므로 실험에 쓰면 안 된다.
    실험 스크립트는 반드시 `data/processed/`의 최종 JSONL만 읽는다 — 이 불변식을
    코드로 강제해, 검토가 끝나기 전에 돌려 놓고 결과를 믿는 사고를 막는다."""
    p = Path(path)
    if "review" in p.parts or ".draft." in p.name:
        raise SystemExit(
            f"검토 전 초안을 실험 입력으로 쓸 수 없다: {p}\n"
            "  → data/processed/ 의 최종 JSONL을 쓸 것 "
            "(`python -m preprocessing.<ds>_prep build`로 생성)")


def passes_valid_conflict_gate(item: Item) -> bool:
    """유효 충돌 게이트 (사전등록 §3.1): 정답 지지 문서와 충돌 문서가 공존해야
    채점 트랙 투입 가능. 라벨 미확정(unknown) 문항은 통과할 수 없다."""
    labels = {c.label for c in item.chunks}
    return "correct" in labels and "conflict" in labels


# ── 표준 렌더링 (계획서 §3.1: 셔플링 + [Document i] 포맷, 메타데이터 유지) ──────

def render_documents(item: Item, *, shuffle_seed: int) -> tuple[str, list[int]]:
    """문서를 무작위 셔플해 표준 포맷으로 렌더링한다 (위치 편향 통제).

    반환: (렌더링 텍스트, 렌더링 순서의 원본 doc_id 리스트).
    doc_id 순서를 함께 반환·기록해야 트레이스의 '[Document k]' 인용을
    원본 문서 라벨로 되짚을 수 있다 (diagnosis/labeler.py에서 사용).
    """
    order = list(range(len(item.chunks)))
    random.Random(shuffle_seed).shuffle(order)
    blocks = []
    for pos, idx in enumerate(order, start=1):
        c = item.chunks[idx]
        header = f"[Document {pos}]"
        attrs = [a for a in (f"Date: {c.date}" if c.date else None,
                             f"URL: {c.url}" if c.url else None,
                             f"Title: {c.title}" if c.title else None) if a]
        if attrs:
            header += " (" + " | ".join(attrs) + ")"
        blocks.append(f"{header}\n{c.text}")
    return "\n\n".join(blocks), [item.chunks[i].doc_id for i in order]


# ── CLI: 산출물 검증 + 게이트 통과율 보고 (Phase 1-4) ─────────────────────────

CONFLICT_CONDITIONS = ("temporal", "misinfo")  # 유효 충돌 게이트 적용 대상


def main() -> None:
    ap = argparse.ArgumentParser(description="공통 스키마 JSONL 검증 + 유효 충돌 게이트 통과율")
    ap.add_argument("paths", nargs="+", help="data/processed/*.jsonl")
    args = ap.parse_args()
    for path in args.paths:
        items = list(read_jsonl(path))
        n_err = sum(1 for it in items if validate_item(it))
        behav = [it for it in items if it.behavior_track]
        # 게이트는 충돌 문항에만 적용된다 — 비충돌 대조군은 정의상 충돌 문서가 없다
        conflict = [it for it in behav if it.conflict_type in CONFLICT_CONDITIONS]
        control = [it for it in behav if it.conflict_type not in CONFLICT_CONDITIONS]
        gate = sum(1 for it in conflict if passes_valid_conflict_gate(it))
        msg = (f"{path}: N={len(items)}  스키마 위반={n_err}  "
               f"behavior_track={len(behav)} (충돌 {len(conflict)} / 대조군 {len(control)})")
        if conflict:
            msg += f"  유효충돌게이트 {gate}/{len(conflict)} ({gate / len(conflict):.1%})"
        print(msg)
        for it in items:
            for e in validate_item(it):
                print(f"  [{it.question_id}] {e}")


if __name__ == "__main__":
    main()
