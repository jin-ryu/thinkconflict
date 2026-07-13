"""DRAGged 전처리: 규칙 초안(CSV) → LLM 초벌 → 사람 확정 → JSONL (Phase 1-3, §3.1.1).

원본(`google-research-datasets/rag_conflicts`, conflicts.jsonl) 실측 구조:
    {source, question, conflict_type, correct_answer,
     search_results:[{title, url, snippet, date, response_str, short_text}]}

계획서 서술과 다른 실측 사실 두 가지 (코드가 이를 따른다):
    · 문서 본문 필드가 `text`가 아니다 — short_text(중앙 298단어) → snippet(중앙 22단어)
      → response_str(최대 5만 단어) 순으로 폴백한다. 세 필드가 모두 빈 문서는 0건.
    · 문항당 문서가 10개 고정이 아니다 — 5~20개, 중앙 9개. 따라서 문서 수는
      RQ3 회귀에서 살아있는 공변량이다(상수가 아니다).

유형별 역할 분담 (연구보고 PPT 10·12·22p 확정 — 쓰는 유형과 안 쓰는 유형):

    | 유형              | 건수 | 채점(행동) 트랙        | 자기일관성 트랙       |
    |-------------------|-----|------------------------|-----------------------|
    | temporal (시간)   |  62 | ⓐ 충돌 조건 (전수 검증) | 충돌측 (182의 일부)   |
    | misinfo (오정보)  |   5 | ⓐ 충돌 조건 (전수 검증) | 충돌측 (182의 일부)   |
    | opinion (의견)    | 115 | **미사용** (정답 없음)  | 충돌측 (182의 일부)   |
    | complementary     | 115 | **미사용** (정답 108건 부재) | 비상충측 (276의 일부) + ⓒ 기준선 |
    | none (비충돌)     | 161 | ⓒ 행동 대조군 (RQ3)     | 비상충측 (276의 일부) |

정답 가용성(실측): 사실 충돌 67건과 비충돌 161건은 전건 정답이 있으나,
상보 115건 중 108건·의견 115건 중 113건은 `correct_answer`가 비어 있다.
따라서 **행동 트랙의 대조군은 비충돌 161건**이고(사전등록 §7.2), 상보·의견은
정답 채점 없이 자기일관성 비교(충돌 182 vs 비상충 276)에 쓴다(§3.2 이중 트랙).

파이프라인 (중간 산출물은 CSV — 사람이 열어 보고 고친다):

    draft  →  dragged.draft.csv   규칙이 아는 것(correct)만 채우고 나머지 `label`은 빈칸.
                                  (규칙은 '정답을 담았는가'만 알 뿐, '다른 답을 주장하는가'와
                                   '무관한가'를 가르지 못한다 — 사전등록 §7.6)
    llm    →  dragged.llm.csv     llm_assist가 빈 `label` 칸을 채운다 (초벌)
    사람    →  CSV를 열어 `label`을 확인·수정 (채우는 칸은 이것 하나뿐)
    build  →  dragged.jsonl       CSV에 적힌 값을 그대로 읽어 최종본 생성

규칙이 하는 일: 문자열·앵커 매칭으로 정답 문서를 찾고, 복수 매칭은 제외가 아니라
`date` 최신성으로 해소한다(사전등록 §3.2). 해소 불가만 플래그한다. 오정보 충돌은
최신성이 아니라 출처 권위로 갈리므로 자동 해소하지 않고 사람에게 넘긴다(5건뿐).
정답 오탈자는 corrected_answer 열로 교정한다(실측: "Boston Celtis", "Bolovia").

usage: python -m preprocessing.dragged_prep {draft|build}
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from datetime import datetime, timedelta

from dateutil import parser as dateparser
from rapidfuzz import fuzz

from preprocessing.schema import Chunk, Item, read_jsonl, write_jsonl
from preprocessing.tabular import (label_provenance, read_csv, read_meta, to_items,
                                   write_csv, write_meta)

# 원본 conflict_type 문구 → 공통 스키마 (실측 5종 전부 커버)
CONFLICT_TYPE_MAP = {
    "outdated": "temporal",             # Conflict due to outdated information (62)
    "misinformation": "misinfo",        # Conflict due to misinformation (5)
    "opinion": "opinion",               # Conflicting opinions and research outcomes (115)
    "complementary": "complementary",   # Complementary information (115)
    "no conflict": "none",              # No conflict (161)
}
FACT_CONFLICT_TYPES = ("temporal", "misinfo")  # 행동 트랙 대상 (명목 67건)
CHUNK_LABELS_FINAL = ("correct", "conflict", "noise")  # 시트에서 허용되는 확정 라벨
TEXT_FIELDS = ("short_text", "snippet", "response_str")  # 폴백 순서 (실측 기반)
MAX_DOC_WORDS = 420   # response_str 폴백이 컨텍스트를 삼키지 않도록 상한 (short_text 최대 412)
FUZZ_THRESHOLD = 85   # 문장 전체 부분 일치 임계
ANCHOR_COVERAGE = 0.6  # 앵커 토큰 커버리지 임계

# 계획서 §3.1.1의 "문자열 일치 + 앵커 토큰" 매칭. 세 판정의 합집합으로 초안을 만든다.
# 이 조합의 실측 버킷은 무매칭 6 / 유일 10 / 복수 51로, 계획서 사전 점검(5/9/53)에
# 근사한다 — 초안은 recall 위주이고 확정은 전수 인간 검증이 담당한다.
_STOPWORDS = frozenset(
    "the a an of in on at to for and or is are was were be been by with from as "
    "that this it its his her their there here what when where who".split())


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def anchor_tokens(answer: str) -> list[str]:
    """정답에서 식별력 있는 앵커(고유명·수치·연도)를 뽑는다. 불용어는 버린다."""
    toks = re.findall(r"[A-Za-z][A-Za-z'\-]+|\d[\d,./:]*", answer)
    return [t for t in (x.lower().strip(".,") for x in toks) if t and t not in _STOPWORDS]


def map_conflict_type(raw: str) -> str:
    raw_l = raw.lower()
    for key, val in CONFLICT_TYPE_MAP.items():
        if key in raw_l:
            return val
    raise ValueError(f"미지의 conflict_type: {raw!r} — CONFLICT_TYPE_MAP 갱신 필요")


def doc_text(d: dict) -> str:
    """본문 폴백 체인. 세 필드가 모두 비면 빈 문자열(호출부가 제외)."""
    for f in TEXT_FIELDS:
        v = str(d.get(f) or "").strip()
        if v:
            return " ".join(v.split()[:MAX_DOC_WORDS])
    return ""


def load_raw(raw_dir: Path) -> list[dict]:
    path = raw_dir / "conflicts.jsonl"
    if not path.exists():
        cands = [p for p in sorted(raw_dir.rglob("*.jsonl")) if ".git" not in p.parts]
        if not cands:
            raise FileNotFoundError(f"{raw_dir}에 원본 없음 — data/raw/download.sh 먼저 실행")
        path = cands[0]
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"원본 로드: {path} (N={len(rows)})")
    return rows


def match_answer(answer: str, text: str) -> bool:
    """문자열 포함 ∪ 문장 fuzzy ∪ 앵커 토큰 커버리지 (초안 단계, recall 위주)."""
    a, t = norm(answer), norm(text)
    if not a or not t:
        return False
    if a in t or fuzz.partial_ratio(a, t) >= FUZZ_THRESHOLD:
        return True
    anchors = anchor_tokens(answer)
    if not anchors:
        return False
    hits = sum(1 for x in anchors if x in t)
    return hits / len(anchors) >= ANCHOR_COVERAGE


MISSING_DATE_TOKENS = {"", "na", "n/a", "none", "null", "unknown"}
RELATIVE_DATE_RE = re.compile(r"\b(\d+)\s+(hour|day|week|month|year)s?\s+ago\b", re.I)
_REL_DAYS = {"hour": 1 / 24, "day": 1, "week": 7, "month": 30, "year": 365}


def parse_date(s: str | None, ref: datetime | None = None) -> datetime | None:
    """문서 날짜를 파싱한다. 실측상 세 형태가 섞여 있다:
    ISO(202건) · 자연어 절대일(223건) · `"NA"`(181건) · 상대 표기(`"2 days ago"`, 9건).

    상대 표기는 크롤 시점 기준이므로 `ref`(코퍼스 내 최신 절대일 = 크롤 시점 근사)에서
    빼서 절대일로 환산한다. ref가 없으면 비교 불가로 보고 None을 반환한다 —
    상대 표기 문서가 대개 **가장 최신**이므로, 그냥 버리면 최신성 해소가 구버전을
    승자로 뽑는다(실측: Thanksgiving·Patriots 문항)."""
    if s is None:
        return None
    raw = str(s).strip()
    if raw.lower() in MISSING_DATE_TOKENS:
        return None
    m = RELATIVE_DATE_RE.search(raw)
    if m:
        if ref is None:
            return None
        return ref - timedelta(days=int(m.group(1)) * _REL_DAYS[m.group(2).lower()])
    try:
        return dateparser.parse(raw)
    except (ValueError, OverflowError, TypeError):
        return None


def corpus_reference_date(rows: list[dict]) -> datetime | None:
    """상대 날짜의 기준점 = 코퍼스 내 최신 절대일(크롤 시점 근사, 사전등록 §7.6)."""
    dates = [d for r in rows for doc in r["search_results"]
             if (d := parse_date(doc.get("date"))) is not None]
    return max(dates) if dates else None


def resolve_by_recency(matched: list[Chunk],
                       ref: datetime | None = None) -> tuple[list[int], str | None]:
    """복수 매칭 해소: date 최신 문서를 correct로 선정 (사전등록 §3.2).

    반환: (correct로 확정할 doc_id 목록, exclusion_flag 또는 None).

    최신 날짜를 공유하는 문서가 여럿이어도, 그보다 오래된 매칭 문서가 남아 있으면
    최신본과 구버전을 가를 수 있으므로 해소 성공이다(최신본 전부를 correct로 둔다).
    해소 불가는 매칭 문서를 날짜로 전혀 나눌 수 없을 때뿐이다 — 날짜가 하나도 없거나
    (date_absent), 매칭 문서 전부가 같은 날짜일 때(date_tie)."""
    dated = [(c, parse_date(c.date, ref)) for c in matched]
    with_date = [(c, d) for c, d in dated if d is not None]
    if not with_date:
        return [], "date_absent"
    latest = max(d for _, d in with_date)
    winners = [c.doc_id for c, d in with_date if d == latest]
    if len(winners) == 1 or len(winners) < len(matched):
        return winners, None
    return [], "date_tie"


def build_draft(rows: list[dict]) -> tuple[list[Item], Counter, datetime | None]:
    items, stats = [], Counter()
    ref = corpus_reference_date(rows)  # 상대 날짜 환산 기준점 (크롤 시점 근사)
    for i, row in enumerate(rows):
        ctype = map_conflict_type(row["conflict_type"])
        chunks = []
        for j, d in enumerate(row["search_results"]):
            text = doc_text(d)
            if not text:
                stats["empty_doc_skipped"] += 1
                continue
            chunks.append(Chunk(doc_id=j, text=text, date=(d.get("date") or None),
                                url=d.get("url"), title=d.get("title")))
        answer = str(row.get("correct_answer") or "").strip()
        flag = None
        hints: dict[int, str] = {}

        if ctype in FACT_CONFLICT_TYPES:
            matched = [c for c in chunks if match_answer(answer, c.text)]
            stats[f"{ctype}_match_{min(len(matched), 2)}"] += 1  # 0 / 1 / 2+ 버킷
            if not matched:
                flag = "no_match"
            elif len(matched) == 1:
                matched[0].label = "correct"
            elif ctype == "misinfo":
                # 오정보 충돌은 최신성이 아니라 출처 권위로 갈린다 — 자동 해소하지 않는다
                flag = "multi_match_needs_authority"
            else:
                winners, flag = resolve_by_recency(matched, ref)
                for c in matched:
                    if c.doc_id in winners:
                        c.label = "correct"
            # 나머지 문서는 unknown으로 남긴다. 규칙은 '정답을 담았는가'만 볼 수 있을 뿐
            # '다른 답을 주장하는가(conflict)'와 '무관한가(noise)'를 가를 수 없다 —
            # 실측 반례: 정답 "at least 1,759"에 "1,762"를 주장하는 문서는 정답 문자열이
            # 없어 매칭에 실패하지만 명백한 충돌 문서다. 이 구분은 LLM 초벌 + 사람
            # 전수 검토가 확정한다 (PPT 12p ①, 사전등록 §7.7).
            matched_ids = {c.doc_id for c in matched}
            for c in chunks:
                if c.label == "unknown":
                    hints[c.doc_id] = ("matched_older" if c.doc_id in matched_ids
                                       else "unmatched")
            if flag:
                stats[f"flag_{flag}"] += 1

        elif ctype == "none" and answer:
            # 비충돌: 모든 문서가 같은 사실을 가리켜 매핑이 자명하다 (§3.1.1).
            # 충돌 문서가 존재하지 않는 조건이므로 noise 부여가 안전하다.
            for c in chunks:
                c.label = "correct" if match_answer(answer, c.text) else "noise"
            if not any(c.label == "correct" for c in chunks):
                flag = "no_match"
                stats["flag_control_no_match"] += 1
        # 상보·의견: 정답이 대개 비어 있어 문서 라벨을 확정할 수 없다 → unknown 유지

        scorable = bool(answer) and flag is None
        items.append(Item(
            question_id=f"dragged-{i:04d}",
            dataset="dragged",
            question=row["question"],
            conflict_type=ctype,
            correct_answers=[answer] if answer else [],
            chunks=chunks,
            # 사실 충돌의 behavior_track은 인간 검증 후 final에서 확정한다.
            # 비충돌 대조군(RQ3 행동 트랙 분모)은 매핑이 자명해 초안에서 바로 확정한다.
            behavior_track=(ctype == "none" and scorable),
            # 자기일관성 비교는 충돌측(temporal·misinfo·opinion = 182) vs
            # 비상충측(complementary·none = 276) — 다섯 유형 전부가 대상이다 (§3.2 이중 트랙)
            self_consistency_track=True,
            exclusion_flag=flag,
            meta={"source_row": i, "source": row.get("source"),
                  "raw_conflict_type": row["conflict_type"],
                  "mapping": "draft-string-fuzz",
                  "rule_hint": hints,   # unknown 문서에 대한 규칙 힌트 (확정 아님)
                  "n_docs": len(chunks),
                  "doc_len_words": [len(c.text.split()) for c in chunks]},
        ))
    return items, stats, ref


def build_items(rows: list[dict], meta_by_qid: dict[str, dict]) -> tuple[list[Item], Counter]:
    """CSV 행 → 최종 Item. 라벨 우선순위(사람 > LLM > 규칙)는 tabular.to_items가 적용한다.
    여기서는 DRAGged 고유의 트랙 판정만 한다."""
    items = to_items(rows, meta_by_qid=meta_by_qid)
    stats: Counter = Counter(label_provenance(rows))
    for it in items:
        it.self_consistency_track = True    # 다섯 유형 전부 (§3.2 이중 트랙)
        if it.meta.get("answer_errata"):
            stats["answer_corrected"] += 1

        if it.conflict_type in FACT_CONFLICT_TYPES:
            # 사람/LLM이 correct를 확정했으면 규칙 단계의 보류 플래그는 해소된 것이다
            if it.exclusion_flag in ("no_match", "multi_match_needs_authority") \
                    and any(c.label == "correct" for c in it.chunks):
                it.exclusion_flag = None
            if any(c.label == "unknown" for c in it.chunks):
                it.exclusion_flag = it.exclusion_flag or "unresolved_chunk_labels"
                stats["items_with_unresolved_chunks"] += 1
            it.behavior_track = (it.exclusion_flag is None
                                 and bool(it.correct_answers)
                                 and any(c.label == "correct" for c in it.chunks)
                                 and any(c.label == "conflict" for c in it.chunks))
            stats["behavior_track" if it.behavior_track else "fact_excluded"] += 1
        elif it.conflict_type == "none":
            # ⓒ 행동 대조군: 매핑이 자명해 규칙만으로 확정된다
            it.behavior_track = (it.exclusion_flag is None
                                 and bool(it.correct_answers)
                                 and any(c.label == "correct" for c in it.chunks))
    return items, stats


def report(items: list[Item]) -> None:
    by_type = Counter(it.conflict_type for it in items)
    print("\nconflict_type 분포:", dict(by_type))
    fact = [it for it in items if it.conflict_type in FACT_CONFLICT_TYPES]
    flags = Counter(it.exclusion_flag for it in fact if it.exclusion_flag)
    n_auto = len(fact) - sum(flags.values())
    # 오정보 복수 매칭은 '해소 실패'가 아니라 '권위 판단을 사람에게 넘김'이므로
    # 인간 검증에서 회수될 것으로 기대되는 몫을 따로 센다 (계획서 예상 56~61).
    pending = flags["multi_match_needs_authority"] + flags["no_match"]
    print(f"사실 충돌 {len(fact)}건 — 플래그 {sum(flags.values())}건 {dict(flags)}")
    print(f"  → 자동 해소: {n_auto}건 / 인간 검증 대기(회수 가능): {pending}건 "
          f"/ 해소 불가(날짜): {flags['date_tie'] + flags['date_absent']}건")
    print(f"  → 인간 검증 후 채점 가능 상한 {n_auto + pending}건 (계획서 사전 점검 예상 56~61)")
    ctrl = [it for it in items if it.conflict_type == "none"]
    print(f"비충돌 대조군(ⓒ 행동): {len(ctrl)}건, 그중 behavior_track "
          f"{sum(1 for it in ctrl if it.behavior_track)}건")
    sc_conflict = sum(1 for it in items
                      if it.conflict_type in ("temporal", "misinfo", "opinion"))
    sc_control = sum(1 for it in items
                     if it.conflict_type in ("complementary", "none"))
    print(f"자기일관성 트랙: 충돌측 {sc_conflict}건(목표 182) vs 비상충측 {sc_control}건(목표 276)")
    print("채점 미사용 유형: opinion(정답 없음) · complementary(정답 108/115 부재) — PPT 10·22p")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["draft", "build"])
    ap.add_argument("--raw-dir", default="data/raw/dragged", type=Path)
    ap.add_argument("--review-dir", default="data/review/dragged", type=Path)
    ap.add_argument("--out-dir", default="data/processed", type=Path)
    ap.add_argument("--csv", type=Path,
                    help="build 입력 CSV (기본: dragged.llm.csv 있으면 그것, 없으면 draft)")
    args = ap.parse_args()
    draft_csv = args.review_dir / "dragged.draft.csv"
    llm_csv = args.review_dir / "dragged.llm.csv"
    meta_path = args.review_dir / "dragged.meta.json"

    if args.stage == "draft":
        items, stats, ref = build_draft(load_raw(args.raw_dir))
        hints = {it.question_id: (it.meta.get("rule_hint") or {}) for it in items}
        write_csv(items, draft_csv, hints=hints)
        write_meta(items, meta_path)
        n_open = sum(1 for it in items for c in it.chunks
                     if c.label == "unknown" and it.conflict_type in FACT_CONFLICT_TYPES)
        print(f"초안 CSV: {draft_csv} (문항 {len(items)} · 행 {sum(len(it.chunks) for it in items)})")
        print(f"  확정 필요 문서(사실 충돌): {n_open}건 — `label` 열의 빈칸을 채우면 된다")
        print(f"  상대 날짜 기준점(코퍼스 최신 절대일): {ref}")
        print("  매칭 버킷(0=무매칭 1=유일 2=복수):",
              {k: v for k, v in sorted(stats.items()) if "_match_" in k})
        report(items)
    else:  # build
        src = args.csv or (llm_csv if llm_csv.exists() else draft_csv)
        if not src.exists():
            raise SystemExit(f"입력 CSV 없음: {src} — `draft` 단계 먼저 실행")
        rows = read_csv(src)
        items, stats = build_items(rows, read_meta(meta_path))
        write_jsonl(items, args.out_dir / "dragged.jsonl")
        print(f"입력: {src}")
        print(f"확정: {args.out_dir / 'dragged.jsonl'} (N={len(items)})")
        print(f"라벨 출처: 규칙 {stats['rule']} · LLM {stats['llm']} · 사람 {stats['human']} "
              f"· 미확정 {stats['unresolved']}")
        print(f"사실 충돌: behavior_track {stats['behavior_track']}건 / "
              f"제외 {stats['fact_excluded']}건 "
              f"(그중 라벨 미확정 {stats['items_with_unresolved_chunks']}건)")
        if stats["answer_corrected"]:
            print(f"정답 정오표 교정: {stats['answer_corrected']}건")
        report(items)


if __name__ == "__main__":
    main()
