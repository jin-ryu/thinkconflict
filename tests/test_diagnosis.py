"""진단 파이프라인 회귀 테스트.

라벨러·채점기·지표는 본 연구의 측정 도구 자체다 — 여기 조용한 버그가 생기면
전환 행렬과 모든 지표가 무효가 되므로, 사전등록된 규칙을 실행 가능한 검사로 고정한다.

    pytest tests/
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

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
from preprocessing.dragged_prep import (anchor_tokens, build_draft, doc_text,
                                        map_conflict_type, match_answer, parse_date,
                                        resolve_by_recency, to_iso)
from preprocessing.qacc_prep import as_list, letters_to_indices
from preprocessing.ramdocs_prep import build_a, build_b, build_pairs
from preprocessing.schema import (Chunk, Item, assert_reviewed, is_scorable,
                                  passes_valid_conflict_gate, render_documents,
                                  validate_item)
from preprocessing.tabular import (COLUMNS, PENDING_SCREEN, SOFT_CONFLICT,
                                   label_provenance, original_answers, read_csv,
                                   to_items, write_csv)

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
            Chunk(1, "It starts at dusk on April 22, 2024.", "conflict",
                  date="2024-05-01", url="https://blog.example"),
            Chunk(2, "Passover is a Jewish holiday.", "noise", date="2023-01-01"),
        ],
        )


# ── 스키마 ────────────────────────────────────────────────────────────────────

def test_valid_item_passes_conflict_gate(item):
    assert validate_item(item) == []
    assert passes_valid_conflict_gate(item)


def test_scorability_is_derived_not_flagged():
    """트랙 플래그를 들고 다니지 않는다 — 정답·제외사유·라벨 확정 여부로 파생한다."""
    ok = Item("dragged-0001", "dragged", "q", "temporal", ["A"],
              chunks=[Chunk(0, "t", "correct"), Chunk(1, "t", "conflict")])
    assert is_scorable(ok)
    # 정답이 없는 문항(의견 충돌)은 채점 대상이 아니다
    assert not is_scorable(Item("dragged-0002", "dragged", "q", "opinion", [],
                                chunks=[Chunk(0, "t", "noise")]))
    # 라벨이 미확정이면 채점할 수 없다
    assert not is_scorable(Item("dragged-0003", "dragged", "q", "temporal", ["A"],
                                chunks=[Chunk(0, "t", "unknown")]))
    # 제외 사유가 붙으면 빠진다
    assert not is_scorable(Item("dragged-0004", "dragged", "q", "temporal", ["A"],
                                chunks=[Chunk(0, "t", "correct")],
                                exclusion_flag="date_tie"))


def test_opinion_items_are_not_graded():
    """정답이 없는 문항을 wrong으로 세면 자기일관성 트랙이 통째로 오염된다."""
    assert grade("Yes, it may be possible.", []) is None
    assert grade("No, humans cannot.", []) is None


def test_hedge_is_counted_separately_not_as_inconsistency():
    """양쪽 병기(hedge)는 불일치가 아니다 — 의견 질의에서 정당한 행동일 수 있다 (§1.8)."""
    op = Item("dragged-0002", "dragged", "Can humans live past 150?", "opinion", [],
              chunks=[Chunk(0, "Experts say yes.", "noise")])
    lab = label_generation(parse_think(
        "<think>Experts lean yes.</think>\nExperts disagree; both views exist."), op, [0])
    assert lab.stance == "hedge"
    assert lab.fa is None          # 채점하지 않는다


def test_render_is_deterministic_per_seed(item):
    text, order = render_documents(item, shuffle_seed=42)
    _, order2 = render_documents(item, shuffle_seed=42)
    assert order == order2 and set(order) == {0, 1, 2}
    assert "[Document 1]" in text and "Date:" in text  # 속성 메타데이터 유지 (§3.1.1)


# ── 채점: 동치·any-gold·기권 분리 (사전등록 §1.3~1.5) ─────────────────────────

def test_equivalence_is_not_string_em():
    assert equivalent("3,559 people", "3559 people")   # 수치 형식 통일
    assert equivalent("April 12, 2025", "2025-04-12")  # 날짜 동치


# 아래 gold 문자열은 DRAGged 원본 실측값이다. 표기 차이를 오답으로 세면 AIR이
# 부풀려지므로(사전등록 §1.4), 실제 gold로 채점기를 고정한다.
@pytest.mark.parametrize("pred,gold", [
    ("El Capitan", "EL-Capitan"),                                   # 하이픈
    ("Jannik Sinner", "Jannik Sinner ( ITA )"),                     # 괄호 부가정보
    ("November 27, 2025", "For 2025 it is November 27th"),          # 서술형 gold + 서수
    ("Monday, May 26, 2025", "Memorial Day, on Monday, May 26, 2025."),
    ("Operation Market Garden", "Operation Market Garden during World War II."),
    ("The answer is 3,559 people.", "3,559 people"),                # 모델이 문장으로 답함
    ("It begins at sundown on Saturday, April 12.",
     "begins at sundown on Saturday, April 12."),
])
def test_real_dragged_gold_strings_are_graded_correct(pred, gold):
    assert grade(pred, [gold]) == "correct"


@pytest.mark.parametrize("pred,gold", [
    ("November 20, 2025", "For 2025 it is November 27th"),  # 수치 앵커 불일치
    ("1,762 tornadoes", "at least 1,759"),                  # 실제 충돌 문서의 답
    ("10,000 people", "3,559 people"),
    ("The Boy", "The Boy and the Heron"),                   # 부분만 답함
    ("people", "3,559 people"),                             # 수치 누락
    ("April 22", "begins at sundown on Saturday, April 12."),
])
def test_grading_does_not_over_accept_different_answers(pred, gold):
    assert grade(pred, [gold]) == "wrong"


def test_gold_typos_stay_wrong_until_errata_correction():
    """gold 오타는 규칙이 넘겨짚지 않는다 — 정오표(사람)가 고쳐야 correct가 된다."""
    assert grade("The Boston Celtics", ["Boston Celtis"]) == "wrong"
    assert grade("The Boston Celtics", ["Boston Celtics"]) == "correct"


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
    a, _ = build_a(rows)
    b = build_b(rows)
    assert len(b) == 1 and len(a) == 2               # gold 단위 분해
    assert a[0].correct_answers == ["3,559 people"]  # 하위 문항은 단일 gold
    assert [c.label for c in a[0].chunks] == ["correct", "conflict", "noise"]
    assert all(validate_item(x) == [] for x in a + b)


def test_ramdocs_gold_without_supporting_doc_is_dropped():
    rows = [{"question": "q", "documents": [{"text": "g", "type": "correct", "answer": "A"}],
             "gold_answers": ["A", "B"], "wrong_answers": []}]
    a, stats = build_a(rows)
    assert len(a) == 1 and stats["dropped_gold_without_support"] == 1


def test_ramdocs_within_item_pair_holds_document_count_fixed():
    """RQ3 매칭 대조의 전제: misinfo↔noise만 바뀌고 문서 수는 같아야 한다 (§3.3.3(a))."""
    rows = [{"question": "q", "documents": [
        {"text": "g", "type": "correct", "answer": "A"},
        {"text": "m1", "type": "misinfo", "answer": "X"},
        {"text": "n1", "type": "noise", "answer": None},
        {"text": "n2", "type": "noise", "answer": None}],
        "gold_answers": ["A"], "wrong_answers": ["X"]}]
    pairs, stats = build_pairs(rows)
    assert stats["pairs"] == 1 and len(pairs) == 2
    conflict, control = pairs
    assert len(conflict.chunks) == len(control.chunks)      # 문서 수 고정
    assert conflict.conflict_type == "misinfo" and control.conflict_type == "none"
    assert any(c.label == "conflict" for c in conflict.chunks)
    assert not any(c.label == "conflict" for c in control.chunks)
    assert conflict.meta["pair_id"] == control.meta["pair_id"]


def test_ramdocs_pair_skipped_when_no_noise_to_swap():
    """노이즈 문서는 질문 고유라 외부에서 빌려올 수 없다 — 쌍을 만들지 않고 보고한다."""
    rows = [{"question": "q", "documents": [
        {"text": "g", "type": "correct", "answer": "A"},
        {"text": "m", "type": "misinfo", "answer": "X"}],
        "gold_answers": ["A"], "wrong_answers": ["X"]}]
    pairs, stats = build_pairs(rows)
    assert pairs == [] and stats["no_noise_to_swap"] == 1


def test_ramdocs_noise_only_item_is_control_condition():
    rows = [{"question": "q", "documents": [
        {"text": "gold", "type": "correct", "answer": "A"},
        {"text": "n", "type": "noise", "answer": None}],
        "gold_answers": ["A"], "wrong_answers": []}]
    a, _ = build_a(rows)
    assert a[0].conflict_type == "none"  # between-item 대조의 비충돌 조건


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


# ── DRAGged 전처리: 원본 실측 구조에 대한 계약 ───────────────────────────────

def test_dragged_conflict_type_map_covers_all_five_raw_labels():
    raw = ["No conflict", "Complementary information",
           "Conflicting opinions and research outcomes",
           "Conflict due to outdated information", "Conflict due to misinformation"]
    assert [map_conflict_type(r) for r in raw] == [
        "none", "complementary", "opinion", "temporal", "misinfo"]


def test_dragged_unknown_conflict_type_raises_rather_than_silently_passing():
    with pytest.raises(ValueError):
        map_conflict_type("Some new category")


def test_dragged_doc_text_falls_back_short_text_then_snippet():
    """원본 문서에는 `text` 키가 없다 — 폴백 체인이 본문을 찾아야 한다."""
    assert doc_text({"short_text": "body", "snippet": "s"}) == "body"
    assert doc_text({"short_text": "", "snippet": "s"}) == "s"
    assert doc_text({"short_text": "", "snippet": "", "response_str": "r"}) == "r"
    assert doc_text({}) == ""


def test_dragged_anchor_matching_finds_outdated_doc_mentioning_same_entity():
    """시간 충돌에서 구버전 문서도 정답 개체를 언급한다 → 복수 매칭이 정상."""
    gold = "begins at sundown on Saturday, April 12."
    assert match_answer(gold, "Pesach begins before sundown on Saturday April 12, 2025.")
    assert not match_answer(gold, "Passover is a Jewish holiday celebrated worldwide.")
    assert "april" in anchor_tokens(gold) and "the" not in anchor_tokens(gold)


def test_recency_resolves_multi_match_when_an_older_doc_exists():
    matched = [Chunk(0, "t", date="2025-01-01"), Chunk(1, "t", date="2024-01-01")]
    winners, flag = resolve_by_recency(matched)
    assert winners == [0] and flag is None


def test_missing_date_tokens_are_not_parsed_as_dates():
    """원본에는 date='NA'가 181건 있다 — 날짜로 오인하면 최신성 해소가 오염된다."""
    for token in ("NA", "n/a", "", "  ", "none"):
        assert parse_date(token) is None


def test_relative_dates_resolve_against_corpus_reference():
    """'2 days ago' 문서가 대개 최신본이다 — 버리면 구버전이 승자가 된다 (실측 반례)."""
    ref = datetime(2025, 4, 3)
    assert parse_date("5 days ago", ref) == datetime(2025, 3, 29)
    assert parse_date("5 days ago") is None      # 기준점 없으면 비교 불가
    newest_is_relative = [Chunk(0, "t", date="Nov 18, 2024"),
                          Chunk(1, "t", date="5 days ago")]
    winners, flag = resolve_by_recency(newest_is_relative, ref)
    assert winners == [1] and flag is None


def test_recency_tie_is_only_unresolvable_when_all_matched_share_the_date():
    """최신 날짜를 공유해도 더 오래된 매칭 문서가 있으면 구버전을 가릴 수 있다."""
    split = [Chunk(0, "t", date="2025-01-01"), Chunk(1, "t", date="2025-01-01"),
             Chunk(2, "t", date="2020-01-01")]
    winners, flag = resolve_by_recency(split)
    assert winners == [0, 1] and flag is None

    all_same = [Chunk(0, "t", date="2025-01-01"), Chunk(1, "t", date="2025-01-01")]
    assert resolve_by_recency(all_same) == ([], "date_tie")
    assert resolve_by_recency([Chunk(0, "t"), Chunk(1, "t")]) == ([], "date_absent")


# ── 검토 전 데이터로 실험하는 사고 방지 ──────────────────────────────────────

def test_build_refuses_to_emit_final_output_before_review(tmp_path, monkeypatch):
    """data/3_processed/는 '검토 끝난 것만' 들어오는 곳이다 — 미확정 라벨이 남아 있으면
    build가 최종본을 만들지 않는다. 그러지 않으면 채점 표본이 조용히 0건이 된다."""
    import subprocess, sys, textwrap
    raw = tmp_path / "raw"; raw.mkdir()
    (raw / "conflicts.jsonl").write_text(json.dumps({
        "question": "How many tornadoes?",
        "conflict_type": "Conflict due to outdated information",
        "correct_answer": "at least 1,759",
        "search_results": [
            {"short_text": "confirmed at least 1,759 tornadoes", "date": "2025-01-08"},
            {"short_text": "the count stands at 1,762 tornadoes", "date": "2024-11-02"}],
    }) + "\n", encoding="utf-8")
    review, out = tmp_path / "review", tmp_path / "processed"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
    base = [sys.executable, "-m", "preprocessing.dragged_prep"]
    args = ["--raw-dir", str(raw), "--review-dir", str(review), "--out-dir", str(out)]

    assert subprocess.run(base + ["draft"] + args, env=env,
                          capture_output=True).returncode == 0
    done = subprocess.run(base + ["build"] + args, env=env, capture_output=True, text=True)
    assert done.returncode != 0                       # 검토 전이므로 거부
    assert "검토가 끝나지 않았다" in done.stderr
    assert not list(out.glob("*.jsonl"))              # 최종본을 만들지 않았다


@pytest.mark.parametrize("path", [
    "data/2_review/dragged/dragged.draft.csv",
    "data/2_review/dragged/dragged.llm.csv",     # 순번(2_)이 붙어도 review 단계로 인식해야 한다
    "data/review/dragged/dragged.llm.csv",       # 순번이 없어도 마찬가지
    "data/3_processed/dragged.draft.jsonl",      # 이름에 draft가 있으면 경로 무관하게 차단
])
def test_unreviewed_input_is_refused(path):
    with pytest.raises(SystemExit):
        assert_reviewed(path)


@pytest.mark.parametrize("path", [
    "data/3_processed/dragged/dragged_temporal.jsonl",
    "data/3_processed/ramdocs/ramdocs_a.jsonl",
])
def test_final_input_is_accepted(path):
    assert_reviewed(path)   # 예외가 나지 않아야 한다


# ── CSV 계층: 파이프라인의 중간 표현 (draft → llm → build) ───────────────────

def test_csv_round_trip_preserves_items(tmp_path, item):
    path = tmp_path / "x.csv"
    write_csv([item], path)
    back = to_items(read_csv(path))[0]
    assert back.question_id == item.question_id
    assert back.correct_answers == item.correct_answers
    assert [c.label for c in back.chunks] == [c.label for c in item.chunks]
    assert [c.text for c in back.chunks] == [c.text for c in item.chunks]
    assert back.chunks[0].date == item.chunks[0].date


def test_dates_are_normalized_to_iso():
    """원본 date는 ISO·자연어·상대표기·NA가 뒤섞여 있다 — 저장 시점에 ISO로 통일한다."""
    ref = datetime(2025, 4, 3)
    assert to_iso("2025-01-20 00:00:00") == "2025-01-20"   # ISO+시각
    assert to_iso("Nov 2, 2024") == "2024-11-02"           # 자연어
    assert to_iso("5 days ago", ref) == "2025-03-29"       # 상대 표기
    assert to_iso("NA") is None and to_iso(None) is None   # 날짜 없음


def test_schema_rejects_non_iso_dates():
    bad = Item("dragged-0001", "dragged", "q", "temporal", ["x"],
               chunks=[Chunk(0, "t", "correct", date="Nov 2, 2024")])
    assert any("ISO-8601" in e for e in validate_item(bad))


def test_noise_chunk_carries_no_supported_answer():
    """supported_answer = '이 문서가 주장하는 답' — noise는 질문에 답하지 않으므로 비운다."""
    bad = Item("qacc-0001", "qacc", "q", "misinfo", ["A"],
               chunks=[Chunk(0, "t", "noise", supported_answer="A")])
    assert any("noise chunk must not carry" in e for e in validate_item(bad))


def test_csv_columns_are_schema_fields_only(tmp_path, item):
    """CSV 열은 전부 공통 스키마(Item/Chunk) 필드다 — 보조 열을 만들지 않는다."""
    path = tmp_path / "x.csv"
    write_csv([item], path)
    assert set(read_csv(path)[0]) == set(COLUMNS)
    assert not any(c.endswith("_source") or c in ("rule_hint", "note", "verdict")
                   for c in COLUMNS)


def test_rule_prefills_label_and_leaves_unknown_blank(tmp_path, item):
    """draft CSV: 규칙이 아는 값은 채워지고, 모르는 것은 빈칸으로 남는다."""
    item.chunks[1].label = "unknown"          # 규칙이 판정하지 못한 문서
    path = tmp_path / "x.csv"
    write_csv([item], path)
    rows = read_csv(path)
    assert rows[0]["label"] == "correct"
    assert rows[1]["label"] == ""


def test_single_label_column_last_value_wins(tmp_path, item):
    """채우는 칸은 `label` 하나뿐 — 규칙·LLM·사람이 같은 칸에 쓰고, 적힌 값이 그대로 최종."""
    path = tmp_path / "x.csv"
    write_csv([item], path)
    rows = read_csv(path)
    rows[0]["label"] = "conflict"     # 사람이 규칙 값을 덮어씀
    rows[1]["label"] = "noise"        # LLM이 채움
    rows[2]["label"] = ""             # 아무도 안 채움
    labels = [c.label for c in to_items(rows)[0].chunks]
    assert labels == ["conflict", "noise", "unknown"]


def test_blank_label_becomes_unknown_and_blocks_scoring(tmp_path, item):
    path = tmp_path / "x.csv"
    write_csv([item], path)
    rows = read_csv(path)
    for r in rows:
        r["label"] = ""
    built = to_items(rows)[0]
    assert all(c.label == "unknown" for c in built.chunks)
    assert not is_scorable(built)   # 미확정 라벨이 있으면 채점 대상이 아니다


def test_gold_typo_is_fixed_in_place_and_original_preserved(tmp_path):
    """정답 오타는 `correct_answer` 칸을 직접 고친다. 원본은 초안 CSV와 대조해 보존한다."""
    it = Item("dragged-0090", "dragged", "q", "temporal", ["Boston Celtis"],
              chunks=[Chunk(0, "the Celtics won", "correct")])
    draft = tmp_path / "draft.csv"
    write_csv([it], draft)
    originals = original_answers(draft)

    rows = read_csv(draft)
    rows[0]["correct_answer"] = "Boston Celtics"     # 사람이 그 자리에서 고침
    built = to_items(rows, original_answers=originals)[0]
    assert built.correct_answers == ["Boston Celtics"]
    assert built.meta["answer_errata"] == "Boston Celtis"


def test_covariates_are_derived_from_chunks_not_a_sidecar(tmp_path, item):
    """문서 길이·개수는 별도 파일 없이 CSV의 본문에서 다시 계산한다 (RQ3 공변량)."""
    path = tmp_path / "x.csv"
    write_csv([item], path)
    meta = to_items(read_csv(path))[0].meta
    assert meta["n_docs"] == 3
    assert meta["doc_len_words"] == [len(c.text.split()) for c in item.chunks]


def test_wrong_answers_are_derived_from_supported_answers(tmp_path):
    """오답 목록은 문서별 supported_answer에서 파생한다 (사람이 채우는 칸이 아니다)."""
    it = Item("qacc-0001", "qacc", "q", "misinfo", ["A"],
              chunks=[Chunk(0, "t1", "correct", supported_answer="A"),
                      Chunk(1, "t2", "conflict", supported_answer="B"),
                      Chunk(2, "t3", "noise")])
    path = tmp_path / "x.csv"
    write_csv([it], path)
    assert to_items(read_csv(path))[0].wrong_answers == ["B"]


def test_qacc_gate_is_expressed_as_exclusion_flag(tmp_path):
    """sharp/soft 판정은 별도 열이 아니라 스키마의 exclusion_flag로 표현한다."""
    it = Item("qacc-0001", "qacc", "q", "misinfo", ["A"],
              chunks=[Chunk(0, "t", "correct")], exclusion_flag=PENDING_SCREEN)
    path = tmp_path / "x.csv"
    write_csv([it], path)
    rows = read_csv(path)
    assert rows[0]["exclusion_flag"] == PENDING_SCREEN      # 판정 전엔 채점 트랙 진입 불가
    rows[0]["exclusion_flag"] = ""                          # sharp 판정 → 비운다
    assert to_items(rows)[0].exclusion_flag is None
    rows[0]["exclusion_flag"] = SOFT_CONFLICT               # soft 판정 → 드롭
    assert to_items(rows)[0].exclusion_flag == SOFT_CONFLICT


def test_provenance_is_derived_by_diffing_against_the_draft():
    """출처 열을 두지 않는다 — 초안 CSV와 대조해 '규칙이 채운 값'과 '이후 채운 값'을 가른다."""
    draft = [{"question_id": "q1", "doc_id": "0", "label": "correct"},
             {"question_id": "q1", "doc_id": "1", "label": ""},
             {"question_id": "q1", "doc_id": "2", "label": ""}]
    final = [{"question_id": "q1", "doc_id": "0", "label": "correct"},   # 규칙 값 그대로
             {"question_id": "q1", "doc_id": "1", "label": "conflict"},  # 이후 채움
             {"question_id": "q1", "doc_id": "2", "label": ""}]          # 미확정
    assert label_provenance(final, draft) == {"rule": 1, "filled": 1, "unresolved": 1}


# ── QACC 전처리: MTurk 플랫 포맷 파싱 계약 ───────────────────────────────────

def test_draft_leaves_conflict_vs_noise_unresolved_for_fact_conflicts():
    """규칙은 '정답을 담았는가'만 안다 — 다른 답을 주장하는 문서(conflict)와
    무관한 문서(noise)를 가르지 못하므로 빈칸으로 남기고 LLM+사람에게 넘긴다.
    실측 반례: 정답 'at least 1,759'에 '1,762'를 주장하는 문서는 매칭에 실패한다."""
    rows = [{
        "question": "How many tornadoes so far?",
        "conflict_type": "Conflict due to outdated information",
        "correct_answer": "at least 1,759",
        "search_results": [
            {"short_text": "confirmed at least 1,759 tornadoes", "date": "2025-01-08"},
            {"short_text": "the count stands at 1,762 tornadoes", "date": "2024-11-02"},
            {"short_text": "tornado safety tips for families", "date": "2024-05-01"}],
    }]
    items, _, _ = build_draft(rows)
    labels = [c.label for c in items[0].chunks]
    assert labels[0] == "correct"
    assert labels[1] == labels[2] == "unknown"   # 충돌/무관을 규칙이 단정하지 않는다


def test_draft_control_items_get_noise_since_no_conflicting_doc_exists():
    rows = [{"question": "q", "conflict_type": "No conflict", "correct_answer": "Paris",
             "search_results": [{"short_text": "the capital is Paris", "date": "2025-01-01"},
                                {"short_text": "unrelated travel deals", "date": "2025-01-01"}]}]
    items, _, _ = build_draft(rows)
    assert [c.label for c in items[0].chunks] == ["correct", "noise"]
    assert is_scorable(items[0])    # ⓒ 대조군은 매핑이 자명해 초안에서 바로 채점 가능


def test_qacc_letter_codes_index_into_contexts():
    assert letters_to_indices(["A", "C", "J"], 10) == [0, 2, 9]
    assert letters_to_indices(["K"], 10) == []      # 범위 밖은 버린다
    assert letters_to_indices(["", "AB"], 10) == []


def test_qacc_as_list_parses_string_literal_safely():
    assert as_list("['I', 'G']") == ["I", "G"]
    assert as_list(float("nan")) == [] and as_list(None) == [] and as_list("") == []
    assert as_list("not a list") == []              # eval 대신 literal_eval → 예외 없이 빈 리스트


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
