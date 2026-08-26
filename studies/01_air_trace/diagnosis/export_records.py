"""라벨 JSONL → 문항×환경 평면 표 + 셀별 집계 (파일럿 인수인계 §6 산출물 규격).

논문 쪽은 `records.csv` 한 장으로 AIR·4경로·전환 행렬·LGR·HR·Flip을 전부 다시 계산한다.
그래서 **집계하지 않고 원자료를 그대로 펼친다**. `summary_air.json`은 교차 확인용이며,
지표 정의는 diagnosis/metrics.py·experiments/exp1_mitigation/transition.py를 그대로 호출한다
(여기서 새로 정의하지 않는다).

usage:
    python -m diagnosis.export_records \
        --labels results/labels/qwen_*.jsonl --data data/pilot/*.jsonl \
        --judge gptoss --date 2026-08-21 --out-dir results
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from diagnosis.metrics import MIN_COMPARABLE_N, PATHS, path_decomposition, stage_metrics
from experiments.exp1_mitigation.transition import flow_matrix, gain_decomposition
from preprocessing.schema import Item, read_jsonl
from serving.client import DECODING, MODELS

COLUMNS = ["item_id", "dataset", "env", "seed", "L1", "L2", "FA", "path",
           "is_correct", "n_docs", "conflict_type",
           "l2_source",          # 규격 외 추가: L2가 규칙/판정자 중 어느 쪽 판정인지 (민감도 분석용)
           "type_recognition"]   # 규격 외 추가: 유형 인지 (PPT 15·17p 'RQ1 유형 인지율'의 원자료)
                                 #   correct_type | surface_only | '' (L1 미탐지 또는 유형 단서 정의 없음)


def env_name(rec: dict) -> str:
    """환경 이름. 라벨 레코드의 env는 프롬프트 환경이고 thinking은 별도 플래그라
    규격의 `standard_nothink`는 둘을 합쳐 만든다."""
    return rec["env"] + ("" if rec.get("thinking", True) else "_nothink")


def to_row(rec: dict, item: Item) -> dict:
    # L2는 L1=detected일 때만 판정된다(labeler) — 미탐지 건은 빈칸이지 'unresolved'가 아니다.
    # FA·path 빈칸 규약은 규격 그대로 (오답·기권은 path 공란).
    return {
        "item_id": rec["question_id"], "dataset": rec["dataset"], "env": env_name(rec),
        "seed": rec["seed"], "L1": rec["l1"], "L2": rec.get("l2") or "",
        "FA": rec.get("fa") or "", "path": rec.get("path") or "",
        "is_correct": int(rec.get("fa") == "correct"),
        "n_docs": len(item.chunks), "conflict_type": item.conflict_type,
        "l2_source": (rec.get("provenance") or {}).get("l2", "") if rec.get("l2") else "",
        "type_recognition": rec.get("type_recognition") or "",
    }


def _val(metric) -> float | None:
    """N<20 셀은 비율을 null로 — 개수만 남긴다 (사전등록 §2.1, 규격 §6.2)."""
    if metric.value is None or not metric.comparable:
        return None
    return round(metric.value, 4)


items_ct: dict[str, str] = {}   # question_id → conflict_type (main()에서 채움)


def cell_summary(dataset: str, env: str, recs: list[dict]) -> dict:
    behav = [r for r in recs if r.get("fa") is not None]   # 채점 성립 문항만 (행동 트랙)
    m = stage_metrics(behav) if behav else None
    p = path_decomposition(behav) if behav else None
    return {
        "dataset": dataset, "env": env,
        "n_items": len({r["question_id"] for r in recs}), "n_records": len(recs),
        "L1": dict(Counter(r["l1"] for r in behav)),
        "L2": dict(Counter(r["l2"] for r in behav if r.get("l2"))),
        "FA": dict(Counter(r["fa"] for r in behav)),
        "paths": {k: sum(1 for r in behav if r.get("path") == k) for k in PATHS},
        "metrics": {"loss_l1": _val(m["Loss_L1"]), "loss_l2": _val(m["Loss_L2"]),
                    "AIR": _val(m["AIR"]), "accuracy": _val(m["accuracy"]),
                    "abstain_rate": _val(m["abstain_rate"])} if m else {},
        "air_denominator": m["AIR"].n_denom if m else 0,
        "denominators": {"loss_l2": m["Loss_L2"].n_denom,
                         "paths": p["legitimate"].n_denom} if m else {},
        "ci95": {"AIR": list(m["AIR"].ci95) if m and m["AIR"].ci95 else None},
        # PPT 17p RQ1 지표: 유형 인지율 = 유형 적중 충돌문항 / 전체 충돌문항 (L1 미탐지는 미적중)
        "type_recognition": dict(Counter(r.get("type_recognition") or "none" for r in behav)),
        "type_recognition_rate": (round(sum(1 for r in behav if r.get("type_recognition") == "correct_type")
                                        / len(behav), 4) if len(behav) >= MIN_COMPARABLE_N else None),
        # 충돌 유형별 분해 (PPT 11p 5유형 축) — 개수는 항상, 비율은 N≥20일 때만
        "by_conflict_type": {ct: _type_cell([r for r in behav if items_ct.get(r["question_id"]) == ct])
                             for ct in sorted({items_ct.get(r["question_id"]) for r in behav})},
    }


def _type_cell(recs: list[dict]) -> dict:
    if not recs:
        return {}
    m = stage_metrics(recs)
    return {"n": len(recs), "FA": dict(Counter(r["fa"] for r in recs)),
            "L1_detected": sum(1 for r in recs if r["l1"] == "detected"),
            "paths": {k: sum(1 for r in recs if r.get("path") == k) for k in PATHS},
            "accuracy": _val(m["accuracy"]), "AIR": _val(m["AIR"]), "air_denominator": m["AIR"].n_denom}


def transition_summary(dataset: str, before: list[dict], after: list[dict],
                       before_env: str, after_env: str) -> dict:
    fm = flow_matrix(before, after)
    gd = gain_decomposition(fm["flows"])
    for k in ("LGR", "hidden_regression", "flip_rate"):
        if gd[k]["n_denom"] < MIN_COMPARABLE_N:
            gd[k]["value"] = None          # 규격 §6.2와 동일 규약
    return {"dataset": dataset, "before": before_env, "after": after_env,
            "n_paired": fm["n_paired"], "n_unstable": len(fm["unstable"]),
            "flows": {f"{s}->{t}": n for (s, t), n in sorted(fm["flows"].items())},
            **gd}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", nargs="+", required=True, type=Path)
    ap.add_argument("--data", nargs="+", required=True, type=Path,
                    help="생성에 쓴 표본 JSONL — n_docs·conflict_type의 출처")
    ap.add_argument("--out-dir", type=Path, default=Path("results"))
    ap.add_argument("--judge", default="rule_based", help="rule_based | gptoss | none")
    ap.add_argument("--date", required=True)
    args = ap.parse_args()

    items = {it.question_id: it for p in args.data for it in read_jsonl(p)}
    items_ct.update({q: it.conflict_type for q, it in items.items()})
    recs: list[dict] = []
    for p in args.labels:
        with open(p, encoding="utf-8") as f:
            recs.extend(json.loads(l) for l in f if l.strip())
    missing = {r["question_id"] for r in recs} - set(items)
    if missing:
        raise SystemExit(f"표본 JSONL에 없는 문항 {len(missing)}건: {sorted(missing)[:5]} … --data 확인")

    # ── records.csv ──
    rows = [to_row(r, items[r["question_id"]]) for r in recs]
    rows.sort(key=lambda r: (r["dataset"], r["item_id"], r["env"], r["seed"]))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with open(args.out_dir / "records.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    # ── 환경 간 item_id 일치 점검 (주 목표의 전제) ──
    by_cell: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in recs:
        by_cell[(r["dataset"], env_name(r))].append(r)
    for ds in sorted({d for d, _ in by_cell}):
        envs = {e: {r["question_id"] for r in v} for (d, e), v in by_cell.items() if d == ds}
        base = envs.get("standard")
        for e, ids in envs.items():
            if base is not None and ids != base:
                print(f"⚠ {ds}: standard와 {e}의 item_id 집합 불일치 "
                      f"(공통 {len(ids & base)}, standard만 {len(base - ids)}, {e}만 {len(ids - base)})")

    # ── summary_air.json ──
    seeds = sorted({r["seed"] for r in recs})
    cells = [cell_summary(d, e, v) for (d, e), v in sorted(by_cell.items())]
    transitions = []
    for ds in sorted({d for d, _ in by_cell}):
        if (ds, "standard") in by_cell:
            for after_env in ("reflection", "standard_nothink"):
                if (ds, after_env) in by_cell:
                    transitions.append(transition_summary(
                        ds, by_cell[(ds, "standard")], by_cell[(ds, after_env)],
                        "standard", after_env))
    summary = {
        "run": {"model": MODELS["qwen"][1], "thinking": True,
                "note": "env 'standard_nothink' = thinking off (같은 가중치, 하드 토글)",
                "seeds": seeds, **DECODING, "judge": args.judge, "date": args.date,
                "min_comparable_n": MIN_COMPARABLE_N},
        "cells": cells,
        "transitions": transitions,
    }
    with open(args.out_dir / "summary_air.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"records.csv: {len(rows)}행 / 셀 {len(cells)}개 / 전환 {len(transitions)}개 → {args.out_dir}")
    for c in cells:
        print(f"  {c['dataset']:10s} {c['env']:17s} n={c['n_items']:3d}  "
              f"AIR={c['metrics'].get('AIR')} (N={c['air_denominator']})  "
              f"paths={c['paths']}")


if __name__ == "__main__":
    main()
