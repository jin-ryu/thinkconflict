# 전처리 산출물

**이 폴더는 데이터다** (`preprocessing/`는 이 데이터를 만드는 **코드**다).

**git 커밋 대상이다.** 중간 CSV에는 사람이 확정한 라벨이 담기는데, 이는 재현 불가능한
인간 노동의 산물이므로 이력으로 남긴다 (계획서 §5). 검토가 어디까지 진행됐는지도 그대로
추적된다.

> ⚠️ **공개 시 라이선스 확인.** 이 산출물은 원본 문서 본문을 포함한다. 논문용 익명 미러를
> 만들 때 QACC 파생물은 **CC BY-SA 3.0**(저작자 표시 + 동일조건변경허락) 대상임을 확인할 것.
> 라이선스 사본: `data/raw/LICENSES/`. 원본 자체(`data/raw/`)는 여전히 커밋하지 않으며
> `download.sh` + `checksums.lock`으로 재현된다.

## 파이프라인 — 중간 산출물은 전부 CSV

JSONL은 **맨 마지막에만** 나온다. 그 전 단계는 Excel/Numbers로 열어 보고 고칠 수 있다.

```
원본 → [draft] → <ds>.draft.csv → [llm] → <ds>.llm.csv → [사람] → [build] → <ds>.jsonl
                  규칙이 채움              LLM이 빈칸 채움    final_* 확정      최종본
```

라벨 우선순위: **`final_*`(사람) > `llm_*`(LLM) > `rule_*`(규칙)**.
사람이 빈칸으로 두면 LLM 제안이, LLM도 없으면 규칙 값이 쓰인다. 셋 다 없으면 `unknown`으로
남고, `unknown`이 있는 문항은 채점 트랙에 못 들어간다(스키마 검증이 막는다).

## 구조

```
data/processed/
├── dragged/
│   ├── dragged.draft.csv    규칙 초안 — correct만 확정, 나머지 563문서는 빈칸 👈 검토 대상
│   ├── dragged.llm.csv      LLM 초벌이 llm_label을 채운 것
│   ├── dragged.meta.json    문항별 부가 정보(출처·문서 길이 공변량) — 본문 없음
│   └── dragged.jsonl        최종본 (build 산출)
├── qacc/
│   ├── qacc.draft.csv       스키마 변환 + DRAGged 중복 제거
│   ├── qacc.llm.csv         판정자 2종이 judge{1,2}_verdict/_type을 채운 것
│   ├── qacc.meta.json       문항별 부가 정보
│   └── qacc.jsonl           최종본 (sharp 판정분만)
└── ramdocs/
    ├── ramdocs_a.csv/.jsonl      분해형(충돌 1요인) — 본 실험용
    ├── ramdocs_b.csv/.jsonl      원본 결합형 — 향후 과제용 보관
    └── ramdocs_pairs.csv/.jsonl  RQ3 within-item 매칭 대조쌍
```

**RAMDocs는 LLM·사람 검토가 없다.** 문서별 `type`과 정답이 원본에 라벨돼 있어 승계만 하면
된다 — LLM을 태우면 원본 골드 라벨을 추측으로 덮어쓰는 셈이라 오히려 품질이 낮아진다.
CSV는 눈으로 확인하는 용도로만 함께 낸다.

## 재현 절차

```bash
bash data/raw/download.sh                     # 체크섬 고정 다운로드

# RAMDocs — 원스텝 (LLM 불필요)
python -m preprocessing.ramdocs_prep

# DRAGged — 규칙 초안 → LLM 초벌 → 사람 확정 → 최종본
python -m preprocessing.dragged_prep draft
python -m preprocessing.llm_assist  dragged --base-url http://HOST:PORT/v1 --model MODEL
#   ↳ dragged.llm.csv 를 열어 final_label 확정 (빈칸이면 llm_label이 쓰인다)
python -m preprocessing.dragged_prep build

# QACC — 스키마 변환 → 판정자 2종 → 사람 확정 → 최종본
python -m preprocessing.qacc_prep   draft
python -m preprocessing.llm_assist  qacc --judge 1 --base-url ... --model MODEL_A
python -m preprocessing.llm_assist  qacc --judge 2 --base-url ... --model MODEL_B  # 다른 계열
#   ↳ qacc.llm.csv 를 열어 final_verdict(sharp/soft)·final_conflict_type 확정
python -m preprocessing.qacc_prep   build

python -m preprocessing.schema data/processed/*/*.jsonl   # 산출물 검증 + 게이트 통과율
```

## CSV 열 읽는 법

| 열 | 뜻 |
|---|---|
| `rule_label` | 규칙이 확정한 것 — DRAGged는 `correct`만 채워진다 |
| `rule_hint` | `matched_older`(정답 문자열은 있으나 구버전) / `unmatched`(정답 문자열 없음) — **참고용, 확정 아님** |
| `llm_label` | LLM 초벌 제안 |
| `final_label` | 👈 **사람이 확정하는 값** (`correct` / `conflict` / `noise`) |
| `corrected_answer` | 정답 오타 교정 (실측: `Boston Celtis`, `Bolovia`) |
| `text` | 판단 근거인 문서 본문 |

⚠️ **`rule_hint = unmatched`를 "무관 문서"로 읽으면 안 된다.** 정답과 **다른 답을 주장하는
충돌 문서**가 여기 섞여 있다(예: 정답 `at least 1,759`에 `1,762`를 주장하는 문서).
이 구분이 유효 충돌 게이트를 좌우한다 (사전등록 §7.6).

## 현재 상태 (2026-07-13)

| 데이터셋 | 상태 | N | 채점 트랙 |
|---|---|---|---|
| RAMDocs | ✅ 완료 | a=1,016 / b=500 / pairs=338쌍 | 495 (충돌) + 521 (대조) |
| DRAGged | ⏳ 검토 대기 | 초안 458 (행 4,212) | 0 — 563문서 라벨 미확정 (상한 62) |
| QACC | ⏳ 판정 대기 | 초안 333 (행 3,049) | 0 — sharp/soft 게이트 미실행 (예상 ~134) |
