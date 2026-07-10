"""지표 산출기: AIR · Loss_L1 · Loss_L2 · 4경로 분해 · 전환 행렬 (계획서 §3.2.2).

사전등록 규칙을 코드로 강제한다:
- 조건부 지표는 결합확률·분모 N 병기 (§1.7) — Metric 객체가 항상 셋을 함께 담는다.
- 유효 분모 N < 20 셀은 comparable=False로 표시 — 비교 주장 금지 (§2.1).
- abstain은 AIR·오답률 분모에서 제외, 기권율 별도 (§1.3).
- 문항 부트스트랩 95% CI 병행 (§2.4) — 시드 반복은 문항 분산을 못 줄이므로.

입력 단위: 라벨 레코드 dict (labeler.StageLabels + question_id/seed 메타).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from collections import Counter, defaultdict

MIN_COMPARABLE_N = 20  # 사전등록 §2.1
PATHS = ("legitimate", "shortcut", "discordant_hit", "blind_hit")


@dataclass
class Metric:
    name: str
    value: float | None     # 조건부 비율
    joint: float | None     # 결합확률 (전체 대비)
    n_denom: int            # 유효 분모
    n_total: int            # 전체 표본
    ci95: tuple[float, float] | None = None

    @property
    def comparable(self) -> bool:
        return self.n_denom >= MIN_COMPARABLE_N

    def __str__(self) -> str:
        if self.value is None:
            return f"{self.name}: 정의 불가 (분모 N={self.n_denom})"
        s = f"{self.name}: {self.value:.3f} (결합 {self.joint:.3f}, N={self.n_denom}/{self.n_total})"
        if self.ci95:
            s += f" CI95=[{self.ci95[0]:.3f}, {self.ci95[1]:.3f}]"
        if not self.comparable:
            s += "  ⚠ N<20 — 비교 주장 금지"
        return s


def _ratio(name: str, hits: list[bool], denom_mask: list[bool],
           seed: int = 0, n_boot: int = 2000) -> Metric:
    """denom_mask 위에서 hits 비율 + 문항 부트스트랩 CI."""
    n_total = len(denom_mask)
    idx = [i for i, m in enumerate(denom_mask) if m]
    n = len(idx)
    if n == 0:
        return Metric(name, None, None, 0, n_total)
    vals = [hits[i] for i in idx]
    value = sum(vals) / n
    joint = sum(vals) / n_total
    rng = random.Random(seed)
    boots = sorted(sum(rng.choices(vals, k=n)) / n for _ in range(n_boot))
    ci = (boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot)])
    return Metric(name, value, joint, n, n_total, ci)


def stage_metrics(records: list[dict]) -> dict[str, Metric]:
    """단계별 손실 3지표 + 기권율. records는 behavior_track 라벨 레코드."""
    l1 = [r["l1"] == "detected" for r in records]
    l2c = [r.get("l2") == "correct" for r in records]
    fa = [r["fa"] for r in records]
    non_abstain = [f != "abstain" for f in fa]
    return {
        "Loss_L1": _ratio("Loss_L1(언어화된 인지 실패율)",
                          [not d for d in l1], [True] * len(records)),
        "Loss_L2": _ratio("Loss_L2(판정 오류율)",
                          [not c for c in l2c], l1),
        "AIR": _ratio("AIR(추론-답변 불일치율)",
                      [f == "wrong" for f in fa],
                      [a and b and c for a, b, c in zip(l1, l2c, non_abstain)]),
        "abstain_rate": _ratio("기권율(의무 병기)",
                               [f == "abstain" for f in fa], [True] * len(records)),
        "accuracy": _ratio("정확도(동치 판정)",
                           [f == "correct" for f in fa], non_abstain),
    }


def path_decomposition(records: list[dict]) -> dict[str, Metric]:
    """정답의 4경로 분해 (상호배타·전수, §1.6). 분모 = FA=correct."""
    correct = [r["fa"] == "correct" for r in records]
    out = {}
    for p in PATHS:
        out[p] = _ratio(f"경로 점유율:{p}",
                        [r.get("path") == p for r in records], correct)
    return out


def transition_matrix(records: list[dict]) -> dict[tuple[str, str, str], int]:
    """(L1, L2, FA) 전체 전환 행렬 — 모든 지표의 원천 셀 집계."""
    mat: Counter = Counter()
    for r in records:
        mat[(r["l1"], r.get("l2") or "-", r["fa"])] += 1
    return dict(mat)


def majority_path_by_item(records: list[dict]) -> dict[str, dict]:
    """문항별 시드 다수결 경로 + 불안정 플래그 (§2.5, §3.3.2 안정성 장치).

    상태 공간은 경로 4종 + wrong + abstain (기권은 명시적 상태 — §1.3).
    반환: {question_id: {state, mode_ratio, unstable, n_seeds}}
    """
    by_item: dict[str, list[str]] = defaultdict(list)
    for r in records:
        state = r.get("path") or r["fa"]  # 정답→경로, 오답/기권→fa 라벨
        by_item[r["question_id"]].append(state)
    out = {}
    for qid, states in by_item.items():
        mode, cnt = Counter(states).most_common(1)[0]
        ratio = cnt / len(states)
        out[qid] = {"state": mode, "mode_ratio": ratio,
                    "unstable": ratio <= 0.5, "n_seeds": len(states)}
    return out


def print_report(records: list[dict], title: str) -> None:
    print(f"== {title} (레코드 N={len(records)}) ==")
    for m in stage_metrics(records).values():
        print(f"  {m}")
    for m in path_decomposition(records).values():
        print(f"  {m}")
    unstable = sum(1 for v in majority_path_by_item(records).values() if v["unstable"])
    print(f"  불안정 플래그 문항: {unstable}")
