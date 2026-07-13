# 작업용 중간 산출물 (검토·수정하는 곳)

**여기가 사람이 손대는 폴더다.** 최종본은 `data/processed/`에 있고, 실험은 그쪽만 읽는다.

```
data/raw/         원본           (git 미포함 — download.sh + checksums.lock으로 재현)
data/interim/     작업용 CSV     (커밋) ← 지금 이 폴더. 검토 상태가 git 이력에 남는다
data/processed/   최종 JSONL     (커밋) ← 실험이 읽는 유일한 입력
```

`preprocessing/`은 이 데이터를 만드는 **코드**다 (폴더 이름이 비슷해 헷갈리기 쉽다).

## 파이프라인 — 중간 산출물은 전부 CSV

JSONL은 **맨 마지막에만** 나온다. 그 전 단계는 Excel/Numbers로 열어 보고 고칠 수 있다.

```
원본 → [draft] → interim/<ds>.draft.csv → [llm] → interim/<ds>.llm.csv → [사람] → [build] → processed/<ds>.jsonl
                  규칙이 채움                       LLM이 빈칸 채움          final_* 확정        최종본
```

라벨 우선순위: **`final_*`(사람) > `llm_*`(LLM) > `rule_*`(규칙)**.
사람이 빈칸으로 두면 LLM 제안이, LLM도 없으면 규칙 값이 쓰인다. 셋 다 없으면 `unknown`으로
남고, `unknown`이 있는 문항은 채점 트랙에 못 들어간다(스키마 검증이 막는다).

검토가 끝나기 전 초안으로 실험을 돌리는 사고는 **코드가 막는다** —
`serving/client.py`와 `diagnosis/run_labeling.py`는 `data/interim/` 경로를 거부한다.

## 구조

```
data/interim/
├── dragged/
│   ├── dragged.draft.csv    규칙 초안 — correct만 확정, 나머지 563문서는 빈칸 👈 검토 대상
│   ├── dragged.llm.csv      LLM 초벌이 llm_label을 채운 것
│   └── dragged.meta.json    문항별 부가 정보(출처·문서 길이 공변량) — 본문 없음
├── qacc/                    (동일 구조: draft.csv · llm.csv · meta.json)
└── ramdocs/                 CSV만 — 눈으로 확인하는 용도 (검토 불필요)
```

**RAMDocs는 LLM·사람 검토가 없다.** 문서별 `type`과 정답이 원본에 라벨돼 있어 승계만 하면
된다 — LLM을 태우면 원본 골드 라벨을 추측으로 덮어쓰는 셈이라 오히려 품질이 낮아진다.

## 재현 절차

```bash
bash data/raw/download.sh                     # 체크섬 고정 다운로드

# RAMDocs — 원스텝 (LLM 불필요, 바로 processed/로 나간다)
python -m preprocessing.ramdocs_prep

# DRAGged — 규칙 초안 → LLM 초벌 → 사람 확정 → 최종본
python -m preprocessing.dragged_prep draft
python -m preprocessing.llm_assist  dragged --base-url http://HOST:PORT/v1 --model MODEL
#   ↳ interim/dragged/dragged.llm.csv 를 열어 final_label 확정 (빈칸이면 llm_label이 쓰인다)
python -m preprocessing.dragged_prep build    # → data/processed/dragged.jsonl

# QACC — 스키마 변환 → 판정자 2종 → 사람 확정 → 최종본
python -m preprocessing.qacc_prep   draft
python -m preprocessing.llm_assist  qacc --judge 1 --base-url ... --model MODEL_A
python -m preprocessing.llm_assist  qacc --judge 2 --base-url ... --model MODEL_B  # 다른 계열
#   ↳ interim/qacc/qacc.llm.csv 를 열어 final_verdict(sharp/soft)·final_conflict_type 확정
python -m preprocessing.qacc_prep   build     # → data/processed/qacc.jsonl

python -m preprocessing.schema data/processed/*.jsonl   # 산출물 검증 + 게이트 통과율
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

`build`는 **규칙↔LLM 불일치 건수를 경고로 출력**한다 — 그 문서는 사람이 반드시 확인한다.
QACC 판정자 2종이 불일치한 문항은 `llm_verdict`가 비어 있다 → 사람이 adjudication한다(부록 A(b)).

## 현재 상태 (2026-07-13)

| 데이터셋 | 상태 | N | 채점 트랙 |
|---|---|---|---|
| RAMDocs | ✅ 완료 | a=1,016 / b=500 / pairs=338쌍 | 495 (충돌) + 521 (대조) |
| DRAGged | ⏳ 검토 대기 | 초안 458 (행 4,212) | 0 — 563문서 라벨 미확정 (상한 62) |
| QACC | ⏳ 판정 대기 | 초안 333 (행 3,049) | 0 — sharp/soft 게이트 미실행 (예상 ~134) |
