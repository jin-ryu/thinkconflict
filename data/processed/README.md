# 전처리 산출물 (공통 스키마 JSONL)

**이 폴더는 데이터다** (`preprocessing/`는 이 데이터를 만드는 **코드**다).

**git 미포함.** 원본 문서 본문을 담고 있어(QACC는 CC BY-SA 3.0 ShareAlike 대상)
커밋하지 않는다. `data/raw/download.sh` + `preprocessing/` 코드 + `checksums.lock`으로
완전히 재현된다.

## 구조 (데이터셋별 폴더)

```
data/processed/
├── dragged/
│   ├── dragged.draft.jsonl    # 규칙 초안 — correct만 확정, 나머지는 unknown
│   └── dragged.jsonl          # 최종본 (인간 검토 후 `dragged_prep final`이 생성)
├── qacc/
│   ├── qacc.draft.jsonl       # 스키마 변환 + DRAGged 중복 제거
│   └── qacc.jsonl             # 최종본 (게이트 통과분; `qacc_prep final`이 생성)
└── ramdocs/
    ├── ramdocs_a.jsonl        # 분해형(충돌 1요인) — 본 실험용
    ├── ramdocs_b.jsonl        # 원본 결합형 — 향후 과제용 보관
    └── ramdocs_pairs.jsonl    # RQ3 within-item 매칭 대조쌍
```

`*.draft.jsonl`은 중간 산출물이고, **최종본은 접미사 없는 `*.jsonl`** 이다.
RAMDocs는 라벨이 원본에 내장돼 있어 draft 단계 없이 바로 최종본이 나온다.

## 재현 절차

```bash
bash data/raw/download.sh                     # 체크섬 고정 다운로드

# RAMDocs — LLM·사람 불필요 (라벨 승계). 바로 최종본.
python -m preprocessing.ramdocs_prep

# DRAGged — 규칙 초안 → LLM 초벌 → 사람 전수 검토 → 최종본
python -m preprocessing.dragged_prep draft
python -m preprocessing.llm_assist  dragged --base-url ... --model ...   # 선택(권장)
python -m preprocessing.dragged_prep sheet    # → preprocessing/review/dragged_review.csv
#   ↳ 사람이 final_label 확정
python -m preprocessing.dragged_prep final

# QACC — 스키마 변환 → 판정자 2종 → 사람 확정 → 최종본
python -m preprocessing.qacc_prep   convert
python -m preprocessing.qacc_prep   screen    # → preprocessing/review/qacc_screen.csv
python -m preprocessing.llm_assist  qacc --judge 1 --base-url ... --model A
python -m preprocessing.llm_assist  qacc --judge 2 --base-url ... --model B
#   ↳ 사람이 verdict·final_type 확정
python -m preprocessing.qacc_prep   final

python -m preprocessing.schema data/processed/*/*.jsonl   # 산출물 검증 + 게이트 통과율
```

## 현재 상태 (2026-07-10)

| 데이터셋 | 상태 | N | 채점 트랙 |
|---|---|---|---|
| RAMDocs | ✅ 완료 | a=1,016 / b=500 / pairs=338쌍 | 495 (충돌) + 521 (대조) |
| DRAGged | ⏳ 검토 대기 | 초안 458 | **0** — 563문서 라벨 미확정 (상한 62) |
| QACC | ⏳ 판정 대기 | 초안 333 | **0** — sharp/soft 게이트 미실행 (예상 ~134) |

## 실측으로 확정된 수치

- **DRAGged**: conflict_type 분포 161/115/115/62/5 — 계획서 Table 2와 정확히 일치.
  자기일관성 트랙 충돌 182 vs 비상충 276 (목표치 일치). ⓒ 행동 대조군 145건 확정.
- **QACC**: 충돌 381건(답 2/3/4개 = 243/94/44) — 계획서 실측과 일치.
  DRAGged 중복 48건 제거(계획서 47), 경계 사례 28건(계획서 27).
- **RAMDocs**: 500문항, 문항당 평균 5.53문서, gold 평균 2.2개 — 계획서와 일치.
