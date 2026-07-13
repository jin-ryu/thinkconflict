"""RAMDocs 전처리: 라벨 승계 + A/B 분리 + within-item 매칭 쌍 (Phase 1-1, §3.1.2, §3.3.3).

원본(`HanNight/RAMDocs`, test 500문항) 실측 구조:
    {question, documents:[{text, type∈{correct,misinfo,noise}, answer}],
     disambig_entity, gold_answers[], wrong_answers[]}
문서별 `type`과 gold/wrong answers가 원본에 라벨돼 있어 골드 매핑이 불필요하다 —
라벨을 그대로 승계만 한다(세 데이터셋 중 가장 기계적 → 먼저 처리).

산출물 3종:
    ramdocs_b.jsonl     원본 결합형(모호성 + 오정보 + 노이즈 공존). 향후 과제용 보관.
    ramdocs_a.jsonl     분해형(충돌 1요인) = 본 실험용. 원본은 '복수 정답(모호성)'과
        '오정보 충돌' 두 요인이 결합돼 전환 행렬 해석이 흐려지므로, gold 단위로 분해해
        각 하위 문항이 오정보 충돌 1요인만 갖게 한다.
    ramdocs_pairs.jsonl RQ3 within-item 매칭 대조쌍 (§3.3.3(a)). 같은 문항에서
        misinfo ↔ noise 만 교체하고 **문서 수를 고정**해 충돌의 순효과를 격리한다.

within-item 쌍 구성 규칙 (실측 기반 설계 결정):
    노이즈 문서는 질문과 같은 주제의 무응답 지문이라 다른 문항에서 빌려올 수 없다.
    따라서 같은 문항 안에서만 교체한다. misinfo m개, noise n개일 때 k = min(m, n):
        conflict 변형 = support + misinfo(k) + noise(n − k)
        control  변형 = support + noise(n)
    둘 다 문서 수가 |support| + n으로 같고, 오직 충돌(오정보) 유무만 다르다.
    m > n인 문항은 초과 misinfo(m − k)가 conflict 변형에서 빠지므로 meta에 기록한다.
    n = 0인 문항은 교체할 노이즈가 없어 쌍을 만들 수 없다 — 제외하고 건수를 보고한다.

usage: python -m preprocessing.ramdocs_prep
       (CSV → data/2_review/ramdocs/ · 최종 JSONL → data/3_processed/ramdocs/)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from preprocessing.schema import Chunk, Item, write_jsonl
from preprocessing.tabular import write_csv

TYPE_TO_LABEL = {"correct": "correct", "misinfo": "conflict", "noise": "noise"}


def load_raw(raw_dir: Path) -> list[dict]:
    candidates = [p for p in sorted(raw_dir.rglob("*.jsonl")) if ".cache" not in p.parts]
    if not candidates:
        raise FileNotFoundError(f"{raw_dir}에 원본 없음 — data/1_raw/download.sh 먼저 실행")
    path = next((p for p in candidates if "test" in p.name.lower()), candidates[0])
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"원본 로드: {path} (N={len(rows)})")
    return rows


def to_chunks(docs: list[dict]) -> list[Chunk]:
    """doc_id는 렌더링 순서가 아니라 이 문항 안에서의 안정적 식별자다.

    supported_answer는 '이 문서가 주장하는 답'이다 — noise 문서는 질문에 답하지 않으므로
    비운다(원본은 'unknown' 같은 자리표시자를 넣어 두었다; 공통 스키마 규약)."""
    out = []
    for i, d in enumerate(docs):
        label = TYPE_TO_LABEL[d["type"]]
        answer = (d.get("answer") or "").strip()
        if label == "noise" or answer.lower() in ("unknown", "none", "n/a"):
            answer = ""
        out.append(Chunk(doc_id=i, text=d["text"], label=label,
                         supported_answer=answer or None))
    return out


def _by_type(docs: list[dict]) -> tuple[list[dict], list[dict]]:
    return ([d for d in docs if d["type"] == "misinfo"],
            [d for d in docs if d["type"] == "noise"])


def _supporting(docs: list[dict], gold: str) -> list[dict]:
    return [d for d in docs if d["type"] == "correct" and d.get("answer") == gold]


def _common_meta(row: dict, chunks: list[Chunk], i: int) -> dict:
    """세 데이터셋 공통 규약 (PPT 11p): 문서 길이를 회귀 보정용 공변량으로 기록하고,
    스키마에 자리가 없는 원본 필드(`disambig_entity`)는 meta에 보존한다."""
    return {"source_row": i,
            "n_docs": len(chunks),
            "doc_len_words": [len(c.text.split()) for c in chunks],
            "disambig_entity": row.get("disambig_entity")}


def build_b(rows: list[dict]) -> list[Item]:
    """원본 결합형: 문항 구조 그대로, any-gold 정답 집합 승계."""
    items = []
    for i, row in enumerate(rows):
        misinfo, _ = _by_type(row["documents"])
        multi_gold = len(row.get("gold_answers", [])) > 1
        items.append(Item(
            question_id=f"ramdocs-{i:04d}",
            dataset="ramdocs_b",
            question=row["question"],
            conflict_type="misinfo" if misinfo else ("ambiguous" if multi_gold else "none"),
            correct_answers=list(row.get("gold_answers", [])),
            wrong_answers=list(row.get("wrong_answers", [])),
            chunks=(ch := to_chunks(row["documents"])),
            meta={**_common_meta(row, ch, i),
                  "n_gold": len(row.get("gold_answers", []))},
        ))
    return items


def build_a(rows: list[dict]) -> tuple[list[Item], dict]:
    """분해형: gold 단위로 분해해 충돌 요인을 오정보 하나로 고정 (본 실험용)."""
    items, dropped = [], 0
    for i, row in enumerate(rows):
        docs = row["documents"]
        misinfo, noise = _by_type(docs)
        golds = list(row.get("gold_answers", []))
        for j, gold in enumerate(golds):
            support = _supporting(docs, gold)
            if not support:
                dropped += 1  # 지지 문서 없는 gold는 하위 문항이 성립하지 않는다
                continue
            items.append(Item(
                question_id=f"ramdocs-{i:04d}-a{j}",
                dataset="ramdocs_a",
                question=row["question"],
                conflict_type="misinfo" if misinfo else "none",
                correct_answers=[gold],
                wrong_answers=list(row.get("wrong_answers", [])),
                chunks=(ch := to_chunks(support + misinfo + noise)),
                meta={**_common_meta(row, ch, i),
                      "gold_index": j, "variant": "full",
                      "original_gold_answers": golds,
                      "n_misinfo": len(misinfo), "n_noise": len(noise)},
            ))
    return items, {"dropped_gold_without_support": dropped}


def build_pairs(rows: list[dict]) -> tuple[list[Item], dict]:
    """RQ3 within-item 매칭 대조쌍: misinfo↔noise 교체, 문서 수 고정 (§3.3.3(a))."""
    items = []
    stats = {"pairs": 0, "no_noise_to_swap": 0, "misinfo_truncated": 0,
             "dropped_gold_without_support": 0}
    for i, row in enumerate(rows):
        docs = row["documents"]
        misinfo, noise = _by_type(docs)
        if not misinfo:
            continue  # 충돌 조건을 만들 수 없다 (between-item 대조는 ramdocs_a가 담당)
        if not noise:
            stats["no_noise_to_swap"] += 1  # 교체할 노이즈가 없어 문서 수를 맞출 수 없다
            continue
        k = min(len(misinfo), len(noise))
        if k < len(misinfo):
            stats["misinfo_truncated"] += 1

        for j, gold in enumerate(row.get("gold_answers", [])):
            support = _supporting(docs, gold)
            if not support:
                stats["dropped_gold_without_support"] += 1
                continue
            pair_id = f"ramdocs-{i:04d}-a{j}"
            common = {"dataset": "ramdocs_a", "question": row["question"],
                      "correct_answers": [gold],
                      "wrong_answers": list(row.get("wrong_answers", [])),
                      }
            # 충돌 변형: misinfo k개가 noise k개를 밀어낸다
            items.append(Item(
                question_id=f"{pair_id}-conflict", conflict_type="misinfo",
                chunks=(ch := to_chunks(support + misinfo[:k] + noise[k:])),
                meta={**_common_meta(row, ch, i),
                      "gold_index": j, "variant": "conflict",
                      "pair_id": pair_id, "n_swapped": k,
                      "misinfo_dropped": len(misinfo) - k}, **common))
            # 대조 변형: 같은 자리에 noise가 그대로 남는다 (문서 수 동일)
            items.append(Item(
                question_id=f"{pair_id}-control", conflict_type="none",
                chunks=(ch := to_chunks(support + noise)),
                meta={**_common_meta(row, ch, i),
                      "gold_index": j, "variant": "control",
                      "pair_id": pair_id, "n_swapped": k}, **common))
            stats["pairs"] += 1
    return items, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/1_raw/ramdocs", type=Path)
    ap.add_argument("--review-dir", default="data/2_review/ramdocs", type=Path)
    ap.add_argument("--out-dir", default="data/3_processed", type=Path)
    args = ap.parse_args()

    rows = load_raw(args.raw_dir)
    b = build_b(rows)
    a, a_stats = build_a(rows)
    pairs, p_stats = build_pairs(rows)

    for items, name in ((a, "ramdocs_a"), (b, "ramdocs_b"), (pairs, "ramdocs_pairs")):
        write_jsonl(items, args.out_dir / "ramdocs" / f"{name}.jsonl")  # 최종본 (검토 불필요)
        write_csv(items, args.review_dir / f"{name}.csv")        # 눈으로 확인하는 용도

    n_conf = sum(1 for it in a if it.conflict_type == "misinfo")
    print("CSV도 함께 생성 — 라벨이 원본에 내장돼 있어 LLM·사람 검토가 필요 없다")
    print(f"ramdocs_b (원본 결합형): N={len(b)}")
    print(f"ramdocs_a (분해형, 본 실험용): N={len(a)} "
          f"— 오정보 충돌 {n_conf} / 비충돌 {len(a) - n_conf}")
    print(f"   지지 문서 없어 탈락한 gold: {a_stats['dropped_gold_without_support']}")
    print(f"ramdocs_pairs (RQ3 within-item 매칭): 쌍 {p_stats['pairs']} "
          f"(문항 {len(pairs) // 2 if pairs else 0}쌍 → 아이템 {len(pairs)})")
    print(f"   노이즈 부재로 쌍 구성 불가한 문항: {p_stats['no_noise_to_swap']}")
    print(f"   misinfo 일부가 잘린 문항(m>n): {p_stats['misinfo_truncated']}")

    # 문서 수 고정 확인 — 매칭 대조의 전제 (§3.3.3(a): '동일 문서 수')
    by_pair: dict[str, list[Item]] = {}
    for it in pairs:
        by_pair.setdefault(it.meta["pair_id"], []).append(it)
    mismatched = [p for p, v in by_pair.items() if len({len(x.chunks) for x in v}) != 1]
    print(f"   문서 수 불일치 쌍: {len(mismatched)} (0이어야 매칭 대조가 성립)")


if __name__ == "__main__":
    main()
