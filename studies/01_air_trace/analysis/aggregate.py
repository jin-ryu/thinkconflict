"""집계·표 생성 (계획서 Phase 3-3, §4 보고 계층).

results/labels/*.jsonl 전체를 읽어 데이터셋별로 **분리 보고**하는 집계 표를 만든다
(풀링 금지 — 사전등록 §2.3). 모든 셀에 분모 N과 CI를 병기하고, N<20 셀에는
비교 금지 표시를 붙인다.

산출물은 results/aggregate/*.json — 생성 즉시 커밋한다 (사전등록 §5).

usage: python -m analysis.aggregate --labels-dir results/labels --out-dir results/aggregate
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from diagnosis.metrics import (MIN_COMPARABLE_N, majority_path_by_item,
                               path_decomposition, stage_metrics, transition_matrix)


def load_all(labels_dir: Path) -> list[dict]:
    records = []
    for p in sorted(labels_dir.glob("*.jsonl")):
        with open(p, encoding="utf-8") as f:
            records += [json.loads(l) for l in f if l.strip()]
    return records


def cell_key(r: dict) -> tuple[str, str, str, str]:
    """레짐(thinking on/off)은 반드시 셀을 가른다 — 비-thinking 대조군(§3.3.3(b))이
    본 실험 셀에 합쳐지면 정확도·전환 행렬이 오염된다."""
    regime = "think" if r.get("thinking", True) else "nothink"
    return (r["dataset"], r["model"], r["env"], regime)


def aggregate(records: list[dict]) -> dict:
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        cells[cell_key(r)].append(r)

    out = {}
    for (dataset, model, env, regime), recs in sorted(cells.items()):
        behav = [r for r in recs if r.get("l2") is not None]
        unstable = [q for q, v in majority_path_by_item(recs).items() if v["unstable"]]
        cell = {
            "n_records": len(recs),
            "n_scorable": len(behav),
            "transition_matrix": {f"{l1}|{l2}|{fa}": n for (l1, l2, fa), n
                                  in sorted(transition_matrix(recs).items())},
            "unstable_items": len(unstable),
        }
        if behav:
            cell["stage_metrics"] = {k: asdict(m) for k, m in stage_metrics(behav).items()}
            cell["path_decomposition"] = {k: asdict(m) for k, m
                                          in path_decomposition(behav).items()}
            cell["underpowered"] = [
                k for k, m in stage_metrics(behav).items() if m.n_denom < MIN_COMPARABLE_N]
        out[f"{dataset}/{model}/{env}/{regime}"] = cell
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels-dir", default="results/labels", type=Path)
    ap.add_argument("--out-dir", default="results/aggregate", type=Path)
    args = ap.parse_args()

    records = load_all(args.labels_dir)
    if not records:
        raise SystemExit(f"{args.labels_dir}에 라벨 파일 없음 — diagnosis.run_labeling 먼저 실행")
    report = aggregate(records)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / "transition_matrices.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print(f"{len(report)}개 셀 집계 → {out_path}  (생성 즉시 커밋 — 사전등록 §5)")
    for name, cell in report.items():
        under = cell.get("underpowered", [])
        flag = f"  ⚠ N<20: {', '.join(under)}" if under else ""
        print(f"  {name}: N={cell['n_records']} 불안정={cell['unstable_items']}{flag}")


if __name__ == "__main__":
    main()
