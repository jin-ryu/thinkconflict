"""진단 파이프라인 회귀 테스트.

라벨러·채점기·지표는 본 연구의 측정 도구 자체다 — 여기 조용한 버그가 생기면
전환 행렬과 모든 지표가 무효가 되므로, 사전등록된 규칙을 실행 가능한 검사로 고정한다.

    pytest tests/
"""
from __future__ import annotations

import pytest

from diagnosis.grading import equivalent, grade
from diagnosis.labeler import label_generation
from diagnosis.metrics import (majority_path_by_item, path_decomposition,
                               stage_metrics)
from diagnosis.trace_parser import parse_harmony, parse_record, parse_think
from experiments.exp1_mitigation.envs import applicable
from experiments.exp1_mitigation.transition import flow_matrix, gain_decomposition
from experiments.exp3_causal.interventions import (analyze, make_filler,
                                                   resample_prefixes,
                                                   truncate_thinking)
from preprocessing.ramdocs_prep import build_a, build_b
from preprocessing.schema import (Chunk, Item, passes_valid_conflict_gate,
                                  render_documents, validate_item)

GOLD = "begins at sundown on Saturday, April 12."


@pytest.fixture
def item() -> Item:
    return Item(
        question_id="dragged-0001", dataset="dragged",
        question="When does this year's Passover start?", conflict_type="temporal",
        correct_answers=[GOLD],
        chunks=[
            Chunk(0, "Pesach 2025 begins before sundown on Saturday April 12, 2025.",
                  "correct", date="2025-01-01", url="https://hebcal.com"),
            Chunk(1, "It starts at dusk on April 22, 2024.", "conflicting",
                  date="2024-05-01", url="https://blog.example"),
            Chunk(2, "Passover is a Jewish holiday.", "noise", date="2023-01-01"),
        ],
        behavior_track=True, self_consistency_track=True)


# ── 스키마 ────────────────────────────────────────────────────────────────────

def test_valid_item_passes_conflict_gate(item):
    assert validate_item(item) == []
    assert passes_valid_conflict_gate(item)


def test_behavior_track_rejects_unfinalized_labels():
    bad = Item("dragged-0002", "dragged", "q", "temporal", [],
               chunks=[Chunk(0, "t", "unknown")], behavior_track=True)
    errs = validate_item(bad)
    assert any("unknown" in e for e in errs) and any("correct_answers" in e for e in errs)


def test_render_is_deterministic_per_seed(item):
    text, order = render_documents(item, shuffle_seed=42)
    _, order2 = render_documents(item, shuffle_seed=42)
    assert order == order2 and set(order) == {0, 1, 2}
    assert "[Document 1]" in text and "Date:" in text  # 속성 메타데이터 유지 (§3.1.1)


# ── 채점: 동치·any-gold·기권 분리 (사전등록 §1.3~1.5) ─────────────────────────

def test_equivalence_is_not_string_em():
    assert equivalent("3,559 people", "3559 people")   # 수치 형식 통일
    assert equivalent("April 12, 2025", "2025-04-12")  # 날짜 동치


def test_any_gold():
    assert grade("B", ["A", "B"]) == "correct"


@pytest.mark.parametrize("answer,expected", [
    ("The answer is 3,559 people.", "correct"),
    ("It is 10,000 people.", "wrong"),
    ("I cannot determine which source is right.", "abstain"),
    ("Sources conflict, but the answer is 3,559 people.", "correct"),  # 확정 답 표출
    (None, "abstain"),
    ("", "abstain"),
])
def test_grade_separates_abstain_from_wrong(answer, expected):
    assert grade(answer, ["3,559 people"]) == expected


# ── 트레이스 파싱 ─────────────────────────────────────────────────────────────

def test_parse_think_and_failures():
    p = parse_record({"text": "<think>reasoning</think>\nFinal: X", "model": "qwen"})
    assert p.ok and p.thinking == "reasoning" and p.answer == "Final: X"
    assert parse_record({"text": "<think>cut", "model": "qwen"}).failure == "unclosed_think"
    # 레짐 통제(no-thinking)에서는 사고 부재가 정상 — 실패로 세지 않는다
    assert parse_record({"text": "answer", "model": "qwen", "thinking": False}).ok


def test_parse_harmony_channels():
    h = parse_harmony("<|channel|>analysis<|message|>doc 1 is outdated"
                      "<|end|><|channel|>final<|message|>Answer X<|return|>")
    assert h.ok and "outdated" in h.thinking and h.answer == "Answer X"
    assert parse_harmony("<|channel|>analysis<|message|>only").failure == "no_final_channel"


# ── 라벨러: 4경로 상호배타 귀속 (사전등록 §1.6) ───────────────────────────────

@pytest.mark.parametrize("trace,answer,expected_path", [
    ("The documents conflict on the date. Document 2 is outdated and wrong. "
     "Document 1 is the most recent and correct.", GOLD, "legitimate"),
    ("The documents contradict each other on the date. Passover timing varies.",
     GOLD, "shortcut"),          # L1=detected, L2=unresolved
    ("These documents contradict each other. Document 2 is correct and reliable. "
     "Document 1 is outdated.", GOLD, "discordant_hit"),
    ("Passover starts in April.", GOLD, "blind_hit"),   # 충돌 인지 없음
    ("The sources conflict. Document 1 is correct and most recent.",
     "some wrong answer", None),                        # 오답 → 경로 귀속 없음 (AIR)
])
def test_path_attribution(item, trace, answer, expected_path):
    lab = label_generation(parse_think(f"<think>{trace}</think>\n{answer}"), item, [0, 1, 2])
    assert lab.path == expected_path


def test_air_case_is_correct_resolution_lost_at_expression(item):
    lab = label_generation(
        parse_think(f"<think>The sources conflict. Document 1 is correct and most recent."
                    f"</think>\nApril 22"), item, [0, 1, 2])
    assert lab.l1 == "detected" and lab.l2 == "correct" and lab.fa == "wrong"


def test_l2_is_last_explicit_support_and_counts_flips(item):
    trace = ("Documents conflict. Document 1 is correct. Later, Document 2 is correct "
             "and reliable. Actually Document 1 is the most recent and accurate.")
    lab = label_generation(parse_think(f"<think>{trace}</think>\n{GOLD}"), item, [0, 1, 2])
    assert lab.l2 == "correct" and lab.l2_flip_count == 2


def test_doc_order_maps_render_position_to_source_label(item):
    """트레이스의 '[Document 1]'은 렌더링 위치이지 원본 doc_id가 아니다."""
    lab = label_generation(
        parse_think(f"<think>Documents conflict. Document 1 is correct and reliable."
                    f"</think>\n{GOLD}"), item, [1, 0, 2])  # 위치1 = 원본 doc1(conflicting)
    assert lab.l2 == "wrong" and lab.path == "discordant_hit"


# ── 지표: 분모·기권 제외·전수 분해 (사전등록 §1.7, §2.1) ─────────────────────

@pytest.fixture
def records() -> list[dict]:
    def rec(i, l1, l2, fa, path):
        return {"question_id": f"q{i}", "seed": 1, "l1": l1, "l2": l2, "fa": fa, "path": path}
    return ([rec(i, "detected", "correct", "correct", "legitimate") for i in range(30)]
            + [rec(i, "detected", "correct", "wrong", None) for i in range(30, 40)]
            + [rec(i, "unrecognized", None, "correct", "blind_hit") for i in range(40, 45)]
            + [rec(i, "detected", "correct", "abstain", None) for i in range(45, 50)])


def test_air_excludes_abstain_from_denominator(records):
    m = stage_metrics(records)["AIR"]
    assert m.n_denom == 40 and m.value == pytest.approx(10 / 40)  # 기권 5건 제외
    assert m.ci95[0] < m.value < m.ci95[1]


def test_abstain_rate_is_reported_alongside_air(records):
    assert stage_metrics(records)["abstain_rate"].value == pytest.approx(5 / 50)


def test_four_paths_are_exhaustive(records):
    shares = path_decomposition(records)
    assert sum(m.value for m in shares.values()) == pytest.approx(1.0)


def test_underpowered_cell_is_flagged():
    small = [{"question_id": "q1", "seed": 1, "l1": "detected", "l2": "correct",
              "fa": "wrong", "path": None}] * 5
    m = stage_metrics(small)["AIR"]
    assert not m.comparable and "N<20" in str(m)


def test_unstable_item_flagged_when_seed_majority_below_half():
    recs = [{"question_id": "qb", "seed": 1, "l1": "detected", "l2": "correct",
             "fa": "correct", "path": "legitimate"},
            {"question_id": "qb", "seed": 2, "l1": "detected", "l2": "correct",
             "fa": "wrong", "path": None}]
    assert majority_path_by_item(recs)["qb"]["unstable"]


# ── RAMDocs A/B 분리 ─────────────────────────────────────────────────────────

def test_ramdocs_a_decomposes_to_single_conflict_factor():
    rows = [{
        "question": "population?",
        "documents": [
            {"text": "gold a", "type": "correct", "answer": "3,559 people"},
            {"text": "gold b", "type": "correct", "answer": "3,600 people"},
            {"text": "bad", "type": "misinfo", "answer": "10,000 people"},
            {"text": "noise", "type": "noise", "answer": None}],
        "gold_answers": ["3,559 people", "3,600 people"],
        "wrong_answers": ["10,000 people"]}]
    a, b = build_a(rows), build_b(rows)
    assert len(b) == 1 and len(a) == 2               # gold 단위 분해
    assert a[0].correct_answers == ["3,559 people"]  # 하위 문항은 단일 gold
    assert [c.label for c in a[0].chunks] == ["correct", "conflicting", "noise"]
    assert all(validate_item(x) == [] for x in a + b)


def test_ramdocs_noise_only_item_is_noncontrol_condition():
    rows = [{"question": "q", "documents": [
        {"text": "gold", "type": "correct", "answer": "A"},
        {"text": "n", "type": "noise", "answer": None}],
        "gold_answers": ["A"], "wrong_answers": []}]
    assert build_a(rows)[0].conflict_type == "none"  # within-item 대조의 비충돌 조건


# ── 흐름 행렬 · 이득 분해 (§3.2.2(3)) ────────────────────────────────────────

def test_gain_decomposition_separates_improvement_from_hidden_regression():
    before = ([{"question_id": f"n{i}", "seed": 1, "fa": "wrong", "path": None}
               for i in range(10)]
              + [{"question_id": f"l{i}", "seed": 1, "fa": "correct", "path": "legitimate"}
                 for i in range(10)])
    after = ([{"question_id": "n0", "seed": 1, "fa": "correct", "path": "legitimate"}]
             + [{"question_id": f"n{i}", "seed": 1, "fa": "correct", "path": "shortcut"}
                for i in range(1, 4)]
             + [{"question_id": f"n{i}", "seed": 1, "fa": "wrong", "path": None}
                for i in range(4, 10)]
             + [{"question_id": f"l{i}", "seed": 1, "fa": "correct", "path": "legitimate"}
                for i in range(7)]
             + [{"question_id": "l7", "seed": 1, "fa": "wrong", "path": None},
                {"question_id": "l8", "seed": 1, "fa": "abstain", "path": None},
                {"question_id": "l9", "seed": 1, "fa": "correct", "path": "blind_hit"}])
    gd = gain_decomposition(flow_matrix(before, after)["flows"])
    assert gd["LGR"]["value"] == pytest.approx(0.25)    # 신규 정답 4 중 정상 경로 1
    assert gd["LGR"]["pooled_required"]                 # 분모 < 20 → pooled 대체
    assert gd["hidden_regression"]["value"] == pytest.approx(0.2)
    assert gd["hidden_regression"]["to_abstain"] == 1   # 퇴행-기권 하위 항목
    assert gd["flip_rate"]["value"] == pytest.approx(6 / 20)


def test_recency_authority_not_applicable_to_ramdocs():
    assert not applicable("recency_authority", "ramdocs_a")
    assert applicable("recency_authority", "dragged")


# ── 인과 개입: 해석 규칙 강제 (사전등록 §4) ──────────────────────────────────

def test_truncation_and_filler_preserve_prefix():
    think = "First sentence. Second sentence. Third one. Fourth last."
    t = truncate_thinking(think, 0.5)
    assert len(t) < len(think) and truncate_thinking(think, 1.0) == think
    assert make_filler(think, 0.5).startswith(t) and "..." in make_filler(think, 0.5)


def test_resampling_uses_neighboring_points_for_localization_noise():
    think = "A one. B two. C three. D four."
    assert 1 <= len(resample_prefixes(think, len(think) // 2)) <= 3


def test_causal_interpretation_refused_without_controls():
    assert "refused" in analyze([{"mode": "truncation", "fa": "wrong"}])
    assert "refused" in analyze([{"mode": "truncation", "fa": "wrong"},
                                 {"mode": "noop", "fa": "correct"}])  # filler 없음


def test_causal_contribution_is_truncation_minus_noop_and_checks_filler_ceiling():
    recs = ([{"mode": "noop", "fa": "correct", "origin_path": "legitimate"}] * 20
            + [{"mode": "filler", "fa": "wrong", "origin_path": "legitimate"}] * 2
            + [{"mode": "filler", "fa": "correct", "origin_path": "legitimate"}] * 18
            + [{"mode": "truncation", "fa": "wrong", "fraction": 0.5,
                "origin_path": "shortcut"}] * 15
            + [{"mode": "truncation", "fa": "correct", "fraction": 0.5,
                "origin_path": "legitimate"}] * 10)
    r = analyze(recs)
    assert r["format_perturbation_ceiling"] == pytest.approx(0.1)
    assert r["truncation"]["causal_contribution"] == pytest.approx(0.6)
    assert r["truncation"]["exceeds_format_ceiling"]
    # 경로별 취약성: 취약 경로 정답이 정상 경로보다 잘 깨진다 (§3.3.4)
    by_path = r["truncation"]["by_origin_path"]
    assert by_path["shortcut"]["flip_rate"] == 1.0
    assert by_path["legitimate"]["flip_rate"] == 0.0
