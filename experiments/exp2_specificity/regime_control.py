"""실험 2(b) — 사고 채널 귀속: thinking on/off 하드 토글 대조 (계획서 §3.3.3(b), RQ3).

"관측된 취약성이 사고 채널 고유의 것인가, 기저 모델에서 물려받은 것인가"를 통제한다.
AIR·Shortcut은 분리된 사고 결론을 전제하므로 비-thinking에서는 **정의되지 않으며**,
두 레짐에서 공통 비교 가능한 것은 **정확도와 완화 기법의 EM 이득**뿐이다.

레짐 통제 수단 (§3.3.3(b) 모델별 실행 가능성):
    qwen   — 동일 가중치 하드 토글 (주력). client.py --no-thinking
    olmo   — matched-sibling(Olmo-3.1-32B-Instruct) 병행 (보강; 순수 토글 아님)
    gptoss — reasoning effort 최저↔최고 근사 (보조 — 귀속 주장의 근거로 쓰지 않음)

go/no-go 게이트 (사전등록 §3.4): `<think>` 전면 마스킹 시 답 분포가 유의하게
달라지지 않으면 사고 채널이 답과 무관한 장식이므로 진단 자체를 중단·재설계한다.
`--gate` 모드가 이 판정을 수행한다.

usage:
    python -m experiments.exp2_specificity.regime_control --gate \
        --thinking results/labels/qwen_standard_dragged.jsonl \
        --masked   results/labels/qwen_standard_dragged_nothink.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from diagnosis.metrics import MIN_COMPARABLE_N

# 사고 채널이 없으면 정의되지 않는 지표 (부재를 결과로 오독하지 않도록 명시)
UNDEFINED_WITHOUT_THINKING = ("AIR", "Loss_L1", "Loss_L2", "shortcut", "discordant_hit")
GATE_ALPHA = 0.05


def load_labels(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def item_accuracy(records: list[dict]) -> dict[str, float]:
    """문항별 정확도(시드 평균). 기권은 오답과 분리해 분모에서 제외한다(§1.3)."""
    acc: dict[str, list[int]] = {}
    for r in records:
        if r["fa"] == "abstain":
            continue
        acc.setdefault(r["question_id"], []).append(int(r["fa"] == "correct"))
    return {q: sum(v) / len(v) for q, v in acc.items() if v}


def paired_permutation_test(a: dict[str, float], b: dict[str, float],
                            n_perm: int = 10000, seed: int = 0) -> dict:
    """짝지은 문항의 정확도 차이에 대한 부호 뒤집기 순열 검정.

    귀무가설: 사고 채널 on/off가 답 분포를 바꾸지 않는다 (= 사고는 장식).
    문항 부트스트랩과 같은 취지로 **문항 단위**로 짝지어 문항 분산을 반영한다(§2.3)."""
    common = sorted(set(a) & set(b))
    diffs = [a[q] - b[q] for q in common]
    n = len(diffs)
    if n == 0:
        return {"error": "짝지은 문항 없음"}
    observed = sum(diffs) / n
    rng = random.Random(seed)
    extreme = sum(
        1 for _ in range(n_perm)
        if abs(sum(d if rng.random() < 0.5 else -d for d in diffs) / n) >= abs(observed)
    )
    return {"n_paired_items": n, "mean_diff": observed,
            "p_value": (extreme + 1) / (n_perm + 1),
            "comparable": n >= MIN_COMPARABLE_N}


def run_gate(thinking_path: Path, masked_path: Path) -> dict:
    """go/no-go: 전면 마스킹 시 답 분포 불변이면 진단 성립 불가 → 중단·재설계."""
    res = paired_permutation_test(item_accuracy(load_labels(thinking_path)),
                                  item_accuracy(load_labels(masked_path)))
    if "error" in res:
        return res
    passed = res["p_value"] < GATE_ALPHA
    res.update({
        "gate": "go" if passed else "NO-GO",
        "verdict": ("사고 채널이 답 분포를 유의하게 바꾼다 — 사고-답변 진단 성립."
                    if passed else
                    "마스킹해도 답 분포 불변 — 사고 채널이 답과 무관한 장식일 수 있다. "
                    "사전등록 §3.4에 따라 진단을 중단하고 재설계한다."),
        "undefined_without_thinking": list(UNDEFINED_WITHOUT_THINKING),
    })
    return res


def attribution(thinking_path: Path, masked_path: Path) -> dict:
    """귀속 판정: (i) 사고 채널이 정확도를 순증시키는가,
    (ii) 그럼에도 비-thinking에 없던 새 실패 양식(AIR·Shortcut)을 만드는가."""
    think, masked = load_labels(thinking_path), load_labels(masked_path)
    think_correct = [r for r in think if r["fa"] == "correct"]
    fragile = sum(1 for r in think_correct
                  if r.get("path") in ("shortcut", "discordant_hit", "blind_hit"))
    return {
        "accuracy_gain": paired_permutation_test(item_accuracy(think),
                                                 item_accuracy(masked)),
        "thinking_only_failure_modes": {
            "n_correct": len(think_correct),
            "n_fragile_path": fragile,
            "fragile_share": fragile / len(think_correct) if think_correct else None,
            "note": "비-thinking에서는 이 경로 라벨 자체가 정의되지 않는다 (분모 부재).",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--thinking", required=True, type=Path)
    ap.add_argument("--masked", required=True, type=Path,
                    help="--no-thinking(또는 matched sibling) 생성의 라벨 파일")
    ap.add_argument("--gate", action="store_true", help="go/no-go 마스킹 게이트만 수행")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    report = (run_gate(args.thinking, args.masked) if args.gate
              else attribution(args.thinking, args.masked))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    if args.gate and report.get("gate") == "NO-GO":
        raise SystemExit(1)  # 파이프라인이 다음 Phase로 진행하지 못하게 막는다


if __name__ == "__main__":
    main()
