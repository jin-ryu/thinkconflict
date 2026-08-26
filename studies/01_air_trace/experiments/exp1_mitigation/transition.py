"""문항 짝지은 경로 이동 집계 — 흐름 행렬 + 이득 분해 (계획서 §3.3.2 문항별 흐름 분석).

baseline과 완화 환경의 라벨 레코드를 question_id로 짝지어 before→after 흐름 행렬을
만들고, 이득 분해 3지표를 산출한다 (§3.2.2(3)):
    LGR          — 새로 정답이 된 문항 중 정상 경로(legitimate) 비율
    숨은 퇴행율   — 정상 경로 정답이 오답·기권·AIR로 무너진 비율 (퇴행-기권 하위 항목 분리)
    flip률(churn) — 정답↔오답이 서로 뒤집힌 문항 비율

사전등록 반영: 문항별 시드 다수결 경로 위에서 정의, 불안정 플래그 문항 분리 집계 (§2.5),
LGR 분모 < 20이면 pooled LGR로 대체 보고 (§2.6 — 호출부에서 기법 합산 재호출).

usage:
    python -m experiments.exp1_mitigation.transition \
        --before results/labels/qwen_standard_dragged.jsonl \
        --after  results/labels/qwen_reflection_dragged.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from diagnosis.metrics import MIN_COMPARABLE_N, majority_path_by_item

CORRECT_STATES = {"legitimate", "shortcut", "discordant_hit", "blind_hit"}


def load_labels(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def flow_matrix(before: list[dict], after: list[dict]) -> dict:
    """시드 다수결 상태(경로 4종 + wrong + abstain)로 문항을 짝지은 이동 행렬."""
    b = majority_path_by_item(before)
    a = majority_path_by_item(after)
    common = sorted(set(b) & set(a))
    flows: Counter = Counter()
    unstable = []
    for qid in common:
        if b[qid]["unstable"] or a[qid]["unstable"]:
            unstable.append(qid)  # 불안정 플래그 — 분리 집계 (§2.5)
            continue
        flows[(b[qid]["state"], a[qid]["state"])] += 1
    return {"flows": flows, "n_paired": len(common), "unstable": unstable}


def gain_decomposition(flows: Counter) -> dict:
    newly_correct = {(s, t): n for (s, t), n in flows.items()
                     if s not in CORRECT_STATES and t in CORRECT_STATES}
    n_new = sum(newly_correct.values())
    n_new_legit = sum(n for (_, t), n in newly_correct.items() if t == "legitimate")

    was_legit = {(s, t): n for (s, t), n in flows.items() if s == "legitimate"}
    n_legit_before = sum(was_legit.values())
    regressed = {t: n for (_, t), n in was_legit.items() if t not in CORRECT_STATES}
    n_regressed = sum(regressed.values())

    n_flip = sum(n for (s, t), n in flows.items()
                 if (s in CORRECT_STATES) != (t in CORRECT_STATES))
    n_total = sum(flows.values())

    return {
        "LGR": {"value": n_new_legit / n_new if n_new else None,
                "n_denom": n_new,
                "pooled_required": n_new < MIN_COMPARABLE_N},  # §2.6
        "hidden_regression": {"value": n_regressed / n_legit_before if n_legit_before else None,
                              "n_denom": n_legit_before,
                              "to_abstain": regressed.get("abstain", 0)},  # 퇴행-기권 하위 항목
        "flip_rate": {"value": n_flip / n_total if n_total else None, "n_denom": n_total},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True, type=Path)
    ap.add_argument("--after", required=True, type=Path)
    ap.add_argument("--out", type=Path, help="집계 JSON 저장 (생성 즉시 커밋 대상 — 사전등록 §5)")
    args = ap.parse_args()
    fm = flow_matrix(load_labels(args.before), load_labels(args.after))
    gd = gain_decomposition(fm["flows"])
    report = {
        "before": str(args.before), "after": str(args.after),
        "n_paired": fm["n_paired"], "n_unstable": len(fm["unstable"]),
        "flows": {f"{s}->{t}": n for (s, t), n in sorted(fm["flows"].items())},
        "gain_decomposition": gd,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
