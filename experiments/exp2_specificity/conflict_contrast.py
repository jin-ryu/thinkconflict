"""실험 2(a) — 충돌 고유성 대조 + 혼합효과 회귀 (계획서 §3.3.3(a), RQ3).

두 대조는 통제 강도가 다르므로 분리 산출·교차 확인한다:
    RAMDocs (within-item, 매칭 대조)
        같은 문항에서 misinfo 문서 ↔ noise 문서만 교체해 문서 수를 고정한 채
        충돌 유무의 순효과를 격리한다. 매칭 통제의 무게는 여기가 담당.
    DRAGged (between-item, 회귀 보정)
        사실 충돌군(temporal+misinfo)과 비충돌 대조군(complementary+none)은
        서로 다른 문항이므로 충돌 성분이 질의 차이와 교락된다. 문서 수·문서 길이·
        질의 유형을 공변량으로 하는 혼합효과 로지스틱 회귀로 보정하고
        "충돌" 항의 유의성을 검정한다. 생태적 타당성은 여기가 담당.

이중 트랙(사전등록 §1.8): 정확도·AIR 비교는 채점 가능 사실 충돌에 한정하고,
자기일관성 비교는 명시적 상충 전체로 넓혀 검정력을 보완한다.

usage:
    python -m experiments.exp2_specificity.conflict_contrast \
        --labels results/labels/qwen_standard_dragged.jsonl \
        --data data/processed/dragged.jsonl --design between
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

from diagnosis.metrics import MIN_COMPARABLE_N, stage_metrics
from preprocessing.schema import read_jsonl

CONFLICT_TYPES = {"temporal", "misinfo"}      # 충돌 조건 (사실 충돌 — 채점 가능)
CONTROL_TYPES = {"complementary", "none"}     # 비충돌 대조 조건


def load_labels(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def attach_item_features(labels: list[dict], data_path: Path) -> pd.DataFrame:
    """라벨 레코드에 문항 특징(충돌 여부·문서 수·문서 길이)을 결합한다."""
    items = {it.question_id: it for it in read_jsonl(data_path)}
    rows = []
    for r in labels:
        it = items.get(r["question_id"])
        if it is None:
            continue
        if it.conflict_type not in CONFLICT_TYPES | CONTROL_TYPES:
            continue  # opinion은 채점 불가 — 자기일관성 트랙에서만 사용
        rows.append({
            "question_id": r["question_id"],
            "seed": r.get("seed"),
            "conflict": int(it.conflict_type in CONFLICT_TYPES),
            "n_docs": len(it.chunks),
            "doc_len": sum(len(c.text.split()) for c in it.chunks) / len(it.chunks),
            "correct": int(r["fa"] == "correct"),
            "abstain": int(r["fa"] == "abstain"),
            "air": int(r["l1"] == "detected" and r.get("l2") == "correct"
                       and r["fa"] == "wrong"),
            "air_eligible": int(r["l1"] == "detected" and r.get("l2") == "correct"
                                and r["fa"] != "abstain"),
            "path": r.get("path"),
        })
    return pd.DataFrame(rows)


def _subset(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    """결과변수별 유효 분모. 기권은 오답과 분리해 정확도 분모에서 뺀다(§1.3),
    AIR은 존재 조건(L1=detected ∧ L2=correct ∧ 비기권) 위에서만 정의된다(§1.7)."""
    if outcome == "abstain":
        return df
    if outcome == "air":
        return df[df.air_eligible == 1]
    return df[df.abstain == 0]


COVARIATES = ("n_docs", "doc_len")  # 난이도 보정 공변량 (§3.3.3(a))


def _finite(x: float) -> float | None:
    """JSON은 Infinity/NaN을 표현하지 못한다 — 비유한값은 null로 내보낸다."""
    return float(x) if np.isfinite(x) else None


def _live_covariates(d: pd.DataFrame) -> tuple[list[str], dict[str, str]]:
    """식별 불가능한 공변량을 떨어뜨린다:
    - 분산 0: 절편과 공선 (DRAGged는 전 문항 top-10이라 n_docs가 상수인 것이 정상)
    - conflict와 완전 상관: 충돌 효과와 분리 불가 — 보정 대상이 아니라 교락 그 자체
    """
    live, dropped = [], {}
    for c in COVARIATES:
        if d[c].nunique() <= 1:
            dropped[c] = "constant"
            continue
        r = abs(d[c].corr(d.conflict))
        if pd.notna(r) and r > 0.99:
            dropped[c] = f"collinear_with_conflict (|r|={r:.3f})"
            continue
        live.append(c)
    return live, dropped


def between_item_regression(df: pd.DataFrame, outcome: str = "correct") -> dict:
    """혼합효과 로지스틱 회귀: outcome ~ conflict + n_docs + doc_len, 문항 랜덤절편.

    결과변수가 이진(정답/오답)이므로 **선형** 혼합모형(mixedlm)은 쓸 수 없다.
    문항당 시드가 반복되어 관측이 문항 내에서 상관되므로, 문항을 랜덤절편으로 둔
    이항 혼합 GLM을 주 모형으로 적합하고(BinomialBayesMixedGLM — 변분 베이즈라
    p값이 없어 사후평균±표준편차를 보고), 유의성 검정은 문항을 군집으로 한
    클러스터 로버스트 로지스틱 GEE의 Wald 검정으로 병행한다.

    'conflict' 항의 계수가 난이도(문서 수·길이)를 보정한 뒤의 충돌 순효과다.
    """
    d = _subset(df, outcome)
    n_items = d.question_id.nunique()
    if len(d) < MIN_COMPARABLE_N:
        return {"outcome": outcome, "n_obs": len(d), "n_items": n_items,
                "comparable": False,
                "note": f"유효 N={len(d)} < {MIN_COMPARABLE_N} — 사전등록 §2.1에 따라 "
                        "비교 주장을 세우지 않는다 (점추정·CI만 보고)"}
    if d[outcome].nunique() < 2 or d.conflict.nunique() < 2:
        return {"outcome": outcome, "n_obs": len(d), "n_items": n_items,
                "comparable": False, "note": "결과변수 또는 충돌 조건에 변이가 없어 적합 불가"}

    live, dropped = _live_covariates(d)
    formula = " + ".join([f"{outcome} ~ conflict", *live])
    report: dict = {"outcome": outcome, "n_obs": len(d), "n_items": n_items,
                    "comparable": True, "formula": formula,
                    "dropped_covariates": dropped}  # 상수라 보정 불가 — 보고에 명시

    # (주) 문항 랜덤절편 이항 혼합 GLM
    try:
        fit = BinomialBayesMixedGLM.from_formula(
            formula, {"item": "0 + C(question_id)"}, d).fit_vb(verbose=False)
        i = list(fit.model.exog_names).index("conflict")
        report["mixed_logistic"] = {
            "conflict_coef": _finite(fit.fe_mean[i]),
            "conflict_sd": _finite(fit.fe_sd[i]),
            "conflict_odds_ratio": _finite(np.exp(fit.fe_mean[i])),
        }
    except Exception as e:  # noqa: BLE001 — 소표본 비수렴은 GEE로 폴백 보고
        report["mixed_logistic"] = {"error": f"{type(e).__name__}: {e}"}

    # (병행) 문항 클러스터 로버스트 로지스틱 GEE — Wald p값
    try:
        gee = smf.gee(formula, "question_id", d, family=sm.families.Binomial(),
                      cov_struct=sm.cov_struct.Exchangeable()).fit()
        se = _finite(gee.bse["conflict"])
        report["gee_logistic"] = {
            "conflict_coef": _finite(gee.params["conflict"]),
            "conflict_se": se,
            "conflict_p": _finite(gee.pvalues["conflict"]),
            "conflict_odds_ratio": _finite(np.exp(gee.params["conflict"])),
            "ci95_odds_ratio": [_finite(np.exp(v)) for v in gee.conf_int().loc["conflict"]],
        }
        if se is None or se > 1e3:  # 설계행렬 특이·완전분리 — p값을 신뢰할 수 없다
            report["gee_logistic"]["warning"] = (
                "표준오차가 발산했다 (완전분리 또는 잔여 공선성). Wald p값을 근거로 "
                "쓰지 말고 혼합 GLM 사후분포와 문항 부트스트랩 CI로 판단할 것.")
    except Exception as e:  # noqa: BLE001
        report["gee_logistic"] = {"error": f"{type(e).__name__}: {e}"}
    return report


def within_item_contrast(df: pd.DataFrame) -> dict:
    """RAMDocs 매칭 대조: 같은 문항의 misinfo 포함(conflict=1) vs 노이즈만(conflict=0).

    ramdocs_a는 gold 단위 분해 시 question_id를 'ramdocs-NNNN-aK'로 부여하므로,
    원본 문항(source_row) 기준으로 짝을 찾는다."""
    df = df.copy()
    df["source"] = df.question_id.str.rsplit("-a", n=1).str[0]
    paired = df.groupby("source").filter(lambda g: g.conflict.nunique() == 2)
    if paired.empty:
        return {"error": "매칭 쌍 없음 — ramdocs_a 전처리(A/B 분리) 확인"}
    agg = paired.groupby("conflict")[["correct", "air", "abstain"]].mean()
    n_pairs = paired.source.nunique()
    return {
        "n_pairs": n_pairs,
        "comparable": n_pairs >= MIN_COMPARABLE_N,
        "delta_accuracy": float(agg.loc[1, "correct"] - agg.loc[0, "correct"]),
        "delta_air": float(agg.loc[1, "air"] - agg.loc[0, "air"]),
        "delta_abstain": float(agg.loc[1, "abstain"] - agg.loc[0, "abstain"]),
        "by_condition": agg.to_dict(),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True, type=Path)
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--design", choices=["between", "within"], required=True,
                    help="between=DRAGged 회귀 보정, within=RAMDocs 매칭 대조")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    labels = load_labels(args.labels)
    df = attach_item_features(labels, args.data)
    if df.empty:
        raise SystemExit("대조 가능한 문항 없음 — conflict_type 매핑 확인")

    if args.design == "within":
        report = within_item_contrast(df)
    else:
        report = {o: between_item_regression(df, o) for o in ("correct", "air", "abstain")}
    print(json.dumps(report, ensure_ascii=False, indent=2, default=float))

    # 조건별 단계 지표도 병기 (분모 N·CI — 사전등록 §1.7)
    by_qid = df.drop_duplicates("question_id").set_index("question_id").conflict
    for cond, name in ((1, "충돌군"), (0, "비충돌 대조군")):
        recs = [r for r in labels if by_qid.get(r["question_id"]) == cond]
        if recs:
            print(f"\n-- {name} 단계 지표 --")
            for m in stage_metrics(recs).values():
                print(f"  {m}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
