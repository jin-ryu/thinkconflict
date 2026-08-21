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

## 1. 목표 — 단 하나의 수치

> **AIR** = P(FA = wrong | L1 = detected, L2 = correct)
> 추론에서 충돌을 인지하고 올바로 해소했는데, 최종 답변에서 뒤집힌 비율

논문 1(ThinkConflict)의 RQ1 축소판이다. 다른 RQ는 이번 범위가 아니다.

부수 산출: 단계별 손실(Loss_L1, Loss_L2)과 정답 4경로 분포.

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

### 5.4 본실행

- 규모: **데이터셋별 100건** (RAMDocs + QACC)
- 시드: `SEEDS`(13, 42, 71, 108, 2026) 중 **1–2개만**
- 환경: `standard`만. CAD·CD2는 범위 밖
- 디코딩: `t=0.6, top_p=0.95` 고정 — 건드리지 말 것

---

## 6. 📦 산출물 규격 ★ 이 세션의 실제 임무

맥 세션이 이 파일들만 보고 논문을 쓴다. **규격을 지키는 것이 결과를 내는 것보다 중요하다.**

```
results/
├── raw/     qwen_standard_<ds>.jsonl      생성 원문 (git 미포함)
├── labels/  qwen_standard_<ds>.jsonl      3단계 라벨
├── summary_air.json                       ★ 논문에 들어갈 집계
└── RUNLOG.md                              ★ 실제 실행 설정·이슈
```

### 6.1 `results/summary_air.json`

**데이터셋별로 분리해서 담는다. 절대 합치지 않는다.**

```json
{
  "run": {
    "model": "Qwen/Qwen3.6-27B",
    "env": "standard",
    "thinking": true,
    "seeds": [13],
    "temperature": 0.6,
    "top_p": 0.95,
    "judge": "rule_based | gptoss | none",
    "date": "2026-08-21"
  },
  "datasets": {
    "ramdocs_a": {
      "n_items": 100,
      "n_records": 100,
      "L1": {"detected": 0, "unrecognized": 0},
      "L2": {"correct": 0, "wrong": 0, "unresolved": 0},
      "FA": {"correct": 0, "wrong": 0, "abstain": 0},
      "paths": {"legitimate": 0, "shortcut": 0,
                "discordant_hit": 0, "blind_hit": 0},
      "metrics": {"loss_l1": 0.0, "loss_l2": 0.0, "AIR": 0.0},
      "air_denominator": 0
    },
    "qacc": { "...동일 구조..." }
  }
}
```

- **`air_denominator` 필수** — AIR의 분모(L1=detected ∧ L2=correct 인 문항 수).
  분모 없이 비율만 오면 논문에 쓸 수 없다.
- 기권(abstain)은 판정에서 제외하되 **개수는 반드시 기록**한다.
- 어떤 셀이든 **N < 20이면 비율을 내지 말고 `null`** 로 두고 개수만 남긴다 (사전등록 조건).

### 6.2 `results/RUNLOG.md`

논문 방법 절에 그대로 옮길 내용이다. 짧아도 되니 사실만 정확히:

- 실제 사용한 모델 ID·리비전, 시드, 데이터셋별 실제 투입 문항 수
- 판정자 방식 (규칙 기반 / gpt-oss / 없음)
- **중간에 바꾼 설정이 있으면 무엇을 왜 바꿨는지**
- 실패·제외한 문항 수와 사유
- 총 소요 시간

### 6.3 커밋

```bash
git add results/labels results/summary_air.json results/RUNLOG.md
git commit -m "feat(results): AIR pilot on RAMDocs + QACC"
git push origin main
```

`results/raw/`는 `.gitignore` 대상이므로 커밋되지 않는다 — 정상이다.

---

## 7. ⏰ 마감

| 시각 | 할 일 |
|---|---|
| **18:00** | **결과 유무를 맥 세션에 알린다.** 이 시각까지 `summary_air.json`이 없으면 논문은 AIR 없이 확정된다 |
| 이후 | 늦게 끝나도 커밋은 해둔다 — 다음 주 논문 1에 그대로 쓰인다 |

18:00을 넘겨도 **실패가 아니다.** 파이프라인 첫 완주 자체가 논문 1의 필수 선행 작업이다.

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
