# AIR 파일럿 인수인계 — H100 실험 전용 (2026-08-21)

> H100에서 Claude Code 세션을 열었다면 **이 파일부터 읽고 진행**한다.
> 작업 브랜치는 `main`. 실험 산출물만 커밋한다.

---

## 0. 역할 분담 — 여기서는 실험만 한다

| | 담당 | 산출 |
|---|---|---|
| **H100 (이 세션)** | **실험 자료 생성만** | `results/` 아래 산출물 (§6 규격) |
| 맥 (별도 세션) | 논문 집필·조판·제출 | `유진2025711356.docx` |

**논문은 여기서 쓰지 않는다.** 원고·양식·제출 절차는 맥 세션이 전담한다.
이 세션의 유일한 임무는 **§6 규격에 맞는 산출물을 만드는 것**이다.

> ℹ️ **무리하지 말 것.** 맥 세션의 논문은 이 실험 결과가 **없어도 완결되도록** 설계되어 있다.
> 결과가 나오면 예비 실험 절로 추가될 뿐이다. 사전등록을 깨면서까지 숫자를 만들 이유가 전혀 없다.

---

## 1. 목표 — 두 가지

### ① 완화 이득 분해 (주 목표)

> **완화 기법이 올린 정답률은 진짜 대조 추론에서 온 것인가, 우연에서 온 것인가?**

같은 문항을 **완화 전(`standard`) / 후(`reflection`)** 로 돌려 전환 행렬을 만들고 다음을 계산한다.

| 지표 | 정의 |
|---|---|
| **LGR** | 새로 맞은 정답 중 정상 경로로 맞힌 비율 |
| **HR** | 원래 정상 정답이던 문항이 무너진 비율 |
| **Flip** | 정답↔오답 역전 비율 |

**이것이 이번 파일럿의 헤드라인이다.** 환경이 하나뿐이면 계산 자체가 불가능하므로
**반드시 2개 환경을 돌려야 한다** (§5.4).

### ② AIR (부 목표)

> **AIR** = P(FA = wrong | L1 = detected, L2 = correct)
> 추론에서 올바로 해소하고도 최종 답변에서 뒤집힌 비율

정답 4경로(Legitimate·Shortcut·Discordant Hit·Blind Hit)와 단계별 손실(Loss_L1, Loss_L2)도 함께 산출한다.

> ℹ️ ①은 AIR 값이 작아도 성립한다. 그래서 ①을 주 목표로 둔다.

---

## 2. 데이터셋 — RAMDocs + QACC (DRAGged 제외)

**반드시 2개를 쓴다.** 한 데이터셋만으로는 AIR이 그 데이터셋의 구성 방식에서 온 것인지 구분할 수 없다.

| 데이터셋 | 상태 | 할 일 |
|---|---|---|
| **RAMDocs** | ✅ `data/3_processed/ramdocs/` 완비 (`a` 1,016 · `b` 500 · `pairs` 676) | 없음 — 즉시 사용 |
| **QACC** | 라벨 **공백 0건** (3,049행/333문항). **268문항이 유효 충돌 게이트 통과**하나 `pending_screen` 상태 | 게이트① 스크리닝 (§5.2) |
| DRAGged | ❌ `label` 대부분 공백 (`outdated` 578행 중 **518 공백**) | **이번 범위 밖** |

**RAMDocs만으로는 안 되는 이유** — 과제5에서 이미 확인된 사실:

> RAMDocs는 오정보 문서를 *추가하는* 방식으로 충돌을 만들었으므로 모델은 `n_docs`를 세고 있을 뿐이다.
> 구성 방식의 흔적이지 충돌의 성질이 아니다.

RAMDocs는 위키 문단 합성 배치이고 충돌 비율이 91.2%로 편중돼 있다.
**QACC는 실제 구글 검색 스니펫**이라 생태학적 타당도가 높다.

**DRAGged를 빼는 이유** — build가 채점 트랙 문항의 `unknown` 청크를 거부한다.
LLM 초벌은 가능하나 사람 전수 검토가 남고, 검토 없이 쓰면 사전등록을 깬다.
주력 데이터셋이므로 **논문 1 본실험에서 제대로 검토해 쓴다.**

---

## 3. ⚠️ 모델 — 스모크용과 측정용을 구분하라

| 용도 | 모델 | 근거 |
|---|---|---|
| **파이프라인 스모크** (파서가 도는가, `<think>`가 잡히는가) | 아무 작은 모델이나 무방 | 코드 검증일 뿐 |
| **AIR 측정** | **`Qwen/Qwen3.6-27B` 고정** | 계획서 모델 선정 원칙 |

계획서(PPT 18p)가 정한 원칙:

- **네이티브 추론 모델만. SFT 증류 모델은 장식적 트레이스 위험이 있어 제외**
- **20~32B 오픈 가중치만**
- **비양자화 bf16** (`launch_qwen.sh`에 이유 명시 — 로짓·궤적 왜곡 방지)

8B급 증류 모델로 AIR을 재면 **그 수치가 진짜 추론을 반영하는지 알 수 없다.**
AIR은 트레이스를 읽어서 재는 지표이므로 이 위반은 치명적이다.

> **27B가 시간 안에 안 되면 AIR을 측정하지 않는다.** 작은 모델로 대체하지 말 것.
> 논문은 결과 없이도 완결되며, AIR은 다음 주에 제대로 재면 된다.

---

## 4. ⚠️ VRAM — 모델 2개가 동시에 안 올라간다

`diagnosis/run_labeling.py`의 `SAME_FAMILY`: 트레이스 판정자는 생성 모델과 **다른 계열**이어야 한다
(자기선호 편향 통제). 같은 계열이면 `SystemExit`.

| | VRAM (bf16) |
|---|---|
| Qwen3.6-27B (생성) | ~54GB |
| gpt-oss-20b (판정) | ~40GB |
| **동시** | **~94GB > 80GB** ❌ |

| 방안 | 방법 |
|---|---|
| **C. 판정자 없이 규칙 기반** | `--judge-model` 생략. **10건으로 먼저 시험** — 되면 40GB 다운로드를 아낀다 |
| **A. 순차 서빙** | Qwen 생성 완료 → 종료 → gpt-oss 서빙 → 라벨링 |
| B. 판정자만 양자화 | gpt-oss를 MXFP4(~12–16GB)로. 판정자는 텍스트만 읽으므로 허용 가능 |

**C → A 순으로 시도한다.**

> ※ §5.2의 QACC 스크리닝 판정자는 이것과 **별개**다. 트레이스를 읽지 않으므로 API 모델 가능, VRAM 무관.

---

## 5. 실행 순서

**5.1과 5.2는 병행한다.**

### 5.0 사전 확인

```bash
df -h ~                      # 54GB 여유
du -sh ~/.cache/huggingface  # 진행 상황 (1분 간격 2회 → 실제 속도)
# HF에서 Qwen/Qwen3.6-27B 리포 ID 존재 확인 — 틀리면 54GB 헛다운로드
```

### 5.1 [트랙 A] 환경 + 다운로드

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install vllm && pip install -r requirements.txt
export HF_TOKEN=<값>
nohup hf download Qwen/Qwen3.6-27B > ~/dl_qwen.log 2>&1 &
```

### 5.2 [트랙 B] QACC 게이트① 스크리닝 — 다운로드와 동시에

가짜 충돌(표기·granularity 차이만 있는 것)을 거르는 단계. 현재 268문항이 `pending_screen`.

```bash
python -m preprocessing.qacc_prep estimate-cost    # 비용 먼저 확인
python -m preprocessing.llm_assist qacc --judge 1
python -m preprocessing.llm_assist qacc --judge 2
# → qacc.llm.csv 에서 sharp 판정 문항의 exclusion_flag 비우기
python -m preprocessing.qacc_prep build            # → data/3_processed/qacc/*.jsonl
```

### 5.3 서빙 + 스모크 10건 (절대 건너뛰지 말 것)

```bash
bash serving/launch_qwen.sh
head -10 data/3_processed/ramdocs/ramdocs_a.jsonl > /tmp/smoke.jsonl

python -m serving.client --data /tmp/smoke.jsonl \
  --model qwen --env standard \
  --out results/raw/qwen_standard_ramdocs_smoke.jsonl

python -m diagnosis.run_labeling \
  --generations results/raw/qwen_standard_ramdocs_smoke.jsonl \
  --data /tmp/smoke.jsonl \
  --out results/labels/qwen_standard_ramdocs_smoke.jsonl
```

**`<think>` 블록이 JSONL에 제대로 들어갔는지 눈으로 확인할 것.**
`results/`는 지금까지 비어 있었다 = 이 파이프라인은 **한 번도 완주하지 않았다.**
파서·프롬프트 버그가 나올 확률이 높다.

### 5.4 본실행 — 환경 2개를 같은 문항에 돌린다

**같은 문항 집합**에 환경만 바꿔 돌려야 전환 행렬이 만들어진다. 문항이 다르면 짝지을 수 없다.

> ⚠️ **파일명을 먼저 확정할 것.** `qacc_prep build`는 `write_by_type()`으로 저장하므로
> 출력이 `data/3_processed/qacc/qacc_<유형>.jsonl` 처럼 **유형별로 쪼개진다.** `qacc.jsonl` 단일 파일이 아니다.
> RAMDocs는 `ramdocs_a.jsonl` · `ramdocs_b.jsonl` · `ramdocs_pairs.jsonl` 형태다.

```bash
# 0) 실제 파일명 확인
ls data/3_processed/ramdocs/ data/3_processed/qacc/

# 1) 100건 표본을 먼저 고정 — 두 환경이 같은 문항을 써야 짝지어진다
mkdir -p data/pilot
head -100 data/3_processed/ramdocs/ramdocs_a.jsonl  > data/pilot/ramdocs_a.jsonl
cat  data/3_processed/qacc/qacc_*.jsonl | head -100 > data/pilot/qacc.jsonl

# 2) 고정한 표본에 환경만 바꿔 돌린다
for ENV in standard reflection; do
  for DS in ramdocs_a qacc; do
    python -m serving.client \
      --data data/pilot/${DS}.jsonl \
      --model qwen --env $ENV --seeds 13 \
      --out results/raw/qwen_${ENV}_${DS}.jsonl
  done
done

# 3) 라벨링 — --data 는 2)에서 쓴 것과 반드시 같은 파일
for ENV in standard reflection; do
  for DS in ramdocs_a qacc; do
    python -m diagnosis.run_labeling \
      --generations results/raw/qwen_${ENV}_${DS}.jsonl \
      --data data/pilot/${DS}.jsonl \
      --out results/labels/qwen_${ENV}_${DS}.jsonl
  done
done
```

- 규모: **데이터셋별 100건** — 1)에서 고정한 동일 문항을 두 환경에 재사용
- 시드: **`--seeds 13` 명시 필수** — 생략하면 기본값 5개(13·42·71·108·2026)가 전부 돌아 5배가 된다
- 디코딩: `t=0.6, top_p=0.95` — `serving/client.py`의 `DECODING` 고정값. 건드리지 말 것
- `--env` 유효값: `standard` · `cad` · `cd2` · `recency_authority` · `reflection`

**우선순위 — 시간이 부족하면 위에서부터 확보한다.**

| 순위 | 조건 | 얻는 것 |
|---|---|---|
| 1 | `standard` × 2 데이터셋 | AIR·4경로·단계별 손실 |
| **2** | **`reflection` × 2 데이터셋** | **LGR·HR·Flip (주 목표)** |
| 3 | `thinking off` × `standard` | 추론 채널 인과 대조 (보너스) |

`reflection`은 프롬프트만 바꾸는 환경이라 추가 서빙·다운로드가 없다.
CAD·CD2는 디코딩 개입이 필요해 이번 범위 밖이다.

3순위는 `serving/client.py --no-thinking`으로 같은 가중치에서 토글된다. 여유가 있을 때만.

---

## 6. 📦 산출물 규격 ★ 이 세션의 실제 임무

맥 세션이 이 파일들만 보고 논문을 쓴다. **규격을 지키는 것이 결과를 내는 것보다 중요하다.**

```
results/
├── raw/     qwen_<env>_<ds>.jsonl         생성 원문 (git 미포함)
├── labels/  qwen_<env>_<ds>.jsonl         3단계 라벨
├── records.csv                            ★★ 가장 중요 — 문항 단위 평면 표
├── summary_air.json                       집계 (교차 확인용)
└── RUNLOG.md                              ★ 실제 실행 설정·이슈
```

### 6.1 `results/records.csv` ★★ 최우선

**문항 × 환경 조합마다 한 행.** 지표는 맥 세션에서 계산하므로,
여기서는 **집계하지 말고 원자료를 그대로 내보내면 된다.**

| 컬럼 | 값 |
|---|---|
| `item_id` | 문항 ID — **환경 간 짝짓기의 키. 반드시 동일해야 한다** |
| `dataset` | `ramdocs_a` \| `qacc` |
| `env` | `standard` \| `reflection` \| `standard_nothink` |
| `seed` | 정수 |
| `L1` | `detected` \| `unrecognized` |
| `L2` | `correct` \| `wrong` \| `unresolved` |
| `FA` | `correct` \| `wrong` \| `abstain` |
| `path` | `legitimate` \| `shortcut` \| `discordant_hit` \| `blind_hit` \| `` (오답 시 공란) |
| `is_correct` | 0 \| 1 |
| `n_docs` | 문항의 문서 수 |
| `conflict_type` | 5유형 라벨 |

이 표 하나면 AIR·4경로·전환 행렬·LGR·HR·Flip을 전부 여기서 계산할 수 있다.
**집계된 비율만 오면 계산을 다시 못 하므로 반드시 평면 표로 낼 것.**

> ⚠️ `item_id`가 환경 간에 일치하지 않으면 **주 목표(이득 분해)를 계산할 수 없다.**
> 내보내기 전에 `standard`와 `reflection`의 `item_id` 집합이 같은지 확인할 것.

**이 CSV를 만드는 스크립트는 아직 없다. 직접 작성해야 한다.**
`results/labels/*.jsonl`을 읽어 위 컬럼으로 펼치는 짧은 스크립트면 된다
(예: `diagnosis/export_records.py`). 라벨 필드명은 `diagnosis/labeler.py`와
`diagnosis/metrics.py`의 `stage_metrics()` · `path_decomposition()`이 쓰는 키를 그대로 따르면 된다.

라벨 정의(3단계·4경로)의 근거는 `ThinkConflict_연구보고.pptx` 15–16페이지와
`diagnosis/labeler.py` 구현에 있다. **정의를 새로 만들지 말고 기존 구현을 따를 것.**

### 6.2 `results/summary_air.json`

교차 확인용. 데이터셋 × 환경별로 분리해 담는다. **절대 합치지 않는다.**

```json
{
  "run": {"model": "Qwen/Qwen3.6-27B", "thinking": true, "seeds": [13],
          "temperature": 0.6, "top_p": 0.95,
          "judge": "rule_based | gptoss | none", "date": "2026-08-21"},
  "cells": [
    {"dataset": "ramdocs_a", "env": "standard",
     "n_items": 100,
     "L1": {"detected": 0, "unrecognized": 0},
     "L2": {"correct": 0, "wrong": 0, "unresolved": 0},
     "FA": {"correct": 0, "wrong": 0, "abstain": 0},
     "paths": {"legitimate": 0, "shortcut": 0, "discordant_hit": 0, "blind_hit": 0},
     "metrics": {"loss_l1": 0.0, "loss_l2": 0.0, "AIR": 0.0},
     "air_denominator": 0}
  ]
}
```

- **`air_denominator` 필수** — AIR의 분모(L1=detected ∧ L2=correct 문항 수).
- 기권(abstain)은 판정에서 제외하되 **개수는 반드시 기록**한다.
- **N < 20인 셀은 비율을 `null`** 로 두고 개수만 남긴다 (사전등록 조건).

### 6.3 `results/RUNLOG.md`

논문 방법 절에 그대로 옮길 내용이다. 짧아도 되니 사실만 정확히:

- 실제 사용한 모델 ID·리비전, 시드, 데이터셋별 실제 투입 문항 수
- 판정자 방식 (규칙 기반 / gpt-oss / 없음)
- **중간에 바꾼 설정이 있으면 무엇을 왜 바꿨는지**
- 실패·제외한 문항 수와 사유
- 총 소요 시간

### 6.4 커밋

```bash
git add results/labels results/records.csv results/summary_air.json results/RUNLOG.md
git commit -m "feat(results): mitigation-gain pilot on RAMDocs + QACC"
git push origin main
```

`results/raw/`는 `.gitignore` 대상이므로 커밋되지 않는다 — 정상이다.

---

## 7. ⏰ 마감

**2026-08-21 18:00 (KST)** 이 마지노선이다. 논문 마감이 같은 날 23:59다.

| 시각 | 할 일 |
|---|---|
| **18:00** | 여기까지 나온 것을 **커밋·푸시하고, 사용자에게 상태를 보고**한다 |
| 이후 | 늦게 끝나도 커밋은 해둔다 — 다음 주 논문 1에 그대로 쓰인다 |

**보고 방법**: 이 세션은 맥 세션과 직접 통신할 수 없다.
`git push` 한 뒤 **사용자에게 다음 세 가지를 한 줄씩 알린다.**

1. `results/records.csv`가 생성되었는가 (예/아니오, 행 수)
2. 어느 환경까지 돌았는가 (`standard`만 / `standard`+`reflection`)
3. 막힌 지점이 있으면 무엇인가

18:00까지 아무것도 없어도 **실패가 아니다.** 논문은 이 결과 없이 완결되도록 설계돼 있고,
파이프라인 첫 완주 자체가 논문 1의 필수 선행 작업이다. **사전등록을 깨서 숫자를 만들지 말 것.**

---

## 8. 하지 말 것

- **작은 모델로 AIR 측정** — 스모크 전용. 측정은 27B 고정 (§3)
- `qacc_prep build --allow-unresolved` 강행 — 미판정 충돌이 채점 트랙에 새어든다
- DRAGged 검토 게이트 우회
- 시드·디코딩 변경 — 사전등록 위반
- **데이터셋을 합쳐서 AIR 보고** — 반드시 분리
- `docs/preregistration.md` 수정 — 커밋 타임스탬프가 사전등록의 물증
- 생성 모델 양자화
- **논문 원고 작성** — 맥 세션 담당

---

## 9. 배경 문서

| 파일 | 내용 |
|---|---|
| `docs/연구계획서_ThinkConflict.md` | 논문 1 계획 |
| `docs/preregistration.md` | 사전등록 규약 — 읽기만 |
| `ThinkConflict_연구보고.pptx` | 최신 계획 (24슬라이드) — 3단계 라벨·4경로 정의 |
| `diagnosis/metrics.py` | `print_report()`가 단계별 손실·4경로를 출력 |
