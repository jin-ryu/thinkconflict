# 작업용 중간 산출물 (검토·수정하는 곳)

**여기가 사람이 손대는 폴더다.** 최종본은 `data/processed/`에 있고, 실험은 그쪽만 읽는다.

```
data/raw/         원본           (git 미포함 — download.sh + checksums.lock으로 재현)
data/review/     작업용 CSV     (커밋) ← 지금 이 폴더. 검토 상태가 git 이력에 남는다
data/processed/   최종 JSONL     (커밋) ← 실험이 읽는 유일한 입력
```

`preprocessing/`은 이 데이터를 만드는 **코드**다 (폴더 이름이 비슷해 헷갈리기 쉽다).

## 파이프라인 — 중간 산출물은 전부 CSV

JSONL은 **맨 마지막에만** 나온다. 그 전 단계는 Excel/Numbers로 열어 보고 고칠 수 있다.

```
원본 → [draft] → review/<ds>.draft.csv → [llm] → review/<ds>.llm.csv → [사람] → [build] → processed/<ds>.jsonl
                  규칙이 채움                       LLM이 빈칸 채움          final_* 확정        최종본
```

**채우는 칸은 하나뿐이다.** 문서 라벨은 `label`, QACC 판정은 `verdict`·`conflict_type`.
규칙이 아는 값은 미리 채워져 있고, LLM은 **빈칸만** 메우며, 사람은 아무 칸이나 고쳐 쓴다 —
CSV에 적힌 값이 그대로 최종본이 된다(우선순위 규칙 같은 건 없다).
빈칸으로 남은 라벨은 `unknown`이 되고, `unknown`이 있는 문항은 채점 트랙에 못 들어간다.

검토가 끝나기 전 초안으로 실험을 돌리는 사고는 **코드가 막는다** —
`serving/client.py`와 `diagnosis/run_labeling.py`는 `data/review/` 경로를 거부한다.

## 구조

```
data/review/
├── dragged/
│   ├── dragged.draft.csv    규칙 초안 — 563문서의 `label`이 빈칸 👈 검토 대상
│   └── dragged.llm.csv      LLM이 빈칸을 채운 것 (사람이 여기서 확인·수정)
├── qacc/                    (동일 구조: draft.csv · llm.csv)
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
#   ↳ review/dragged/dragged.llm.csv 를 열어 `label` 확인·수정
python -m preprocessing.dragged_prep build    # → data/processed/dragged.jsonl

# QACC — 스키마 변환 → 판정자 2종 → 사람 확정 → 최종본
python -m preprocessing.qacc_prep   draft
python -m preprocessing.llm_assist  qacc --judge 1 --base-url ... --model MODEL_A
python -m preprocessing.llm_assist  qacc --judge 2 --base-url ... --model MODEL_B  # 다른 계열
#   ↳ review/qacc/qacc.llm.csv 를 열어 `verdict`·`conflict_type` 확인·수정
python -m preprocessing.qacc_prep   build     # → data/processed/qacc.jsonl

python -m preprocessing.schema data/processed/*.jsonl   # 산출물 검증 + 게이트 통과율
```

## CSV 열 — 전부 공통 스키마 필드다

보조 열(`rule_hint`, `note`, `*_source`, `verdict`)은 두지 않는다. 검토자가 보는 모든 칸이
최종 JSONL의 필드에 그대로 대응한다.

| 열 | 스키마 | 채우나 |
|---|---|---|
| `label` | `Chunk.label` | 👈 **`correct` / `conflict` / `noise`** — 빈칸을 채운다 |
| `correct_answer` | `Item.correct_answers` | 👈 정답. 오타면 그 자리에서 고친다 (실측: `Boston Celtis`, `Bolovia`) |
| `conflict_type` | `Item.conflict_type` | 👈 규칙 초벌값이 들어 있다. 틀렸으면 고친다 |
| `exclusion_flag` | `Item.exclusion_flag` | 👈 **비우면 채점 트랙에 들어간다.** 사유가 있으면 적는다 |
| `question_id` · `dataset` · `question` · `doc_id` · `date` · `url` · `supported_answer` · `text` | 그대로 | 읽기용 |

### QACC 게이트 ①은 `exclusion_flag`로 표현한다

sharp/soft를 위한 별도 열을 만들지 않는다 — 스키마에 이미 있는 칸을 쓴다.

| `exclusion_flag` 값 | 뜻 |
|---|---|
| `pending_screen` | 아직 판정 안 됨 (기본값) → **채점 트랙 진입 불가** |
| `soft_conflict` | 사이비 충돌(표기 차이) → 드롭 |
| (빈칸) | **sharp = 진짜 사실 모순 → 채점 트랙 진입** |
| `no_valid_conflict_pair` 등 | 규칙이 붙인 다른 제외 사유 |

판정자 2종의 원 판정은 검토 CSV를 어지럽히지 않도록 `qacc/judges/judge{1,2}.csv`에 따로
남는다. **둘이 일치할 때만** 검토 CSV에 반영되고, 불일치하면 `pending_screen`으로 남아
사람이 adjudication한다(부록 A(b)).

⚠️ **`label`이 빈칸인 563개 문서 중에는 "다른 답을 주장하는 충돌 문서"가 섞여 있다**
(예: 정답 `at least 1,759`인데 `1,762`를 주장). 규칙은 "정답 문자열이 없다"는 것만 알 뿐
그게 딴소리인지 무관한지 모른다 — `text`를 보고 판단해야 하며, 이 구분이 유효 충돌 게이트를
좌우한다 (사전등록 §7.6).

## 현재 상태 (2026-07-13)

| 데이터셋 | 상태 | N | 채점 트랙 |
|---|---|---|---|
| RAMDocs | ✅ 완료 | a=1,016 / b=500 / pairs=338쌍 | 495 (충돌) + 521 (대조) |
| DRAGged | ⏳ 검토 대기 | 초안 458 (행 4,212) | 0 — 563문서 라벨 미확정 (상한 62) |
| QACC | ⏳ 판정 대기 | 초안 333 (행 3,049) | 0 — sharp/soft 게이트 미실행 (예상 ~134) |
