# AIR 파일럿 인수인계 (2026-08-20)

> H100 서버에서 새 Claude Code 세션을 열었다면 **이 파일부터 읽고 이어서 진행**한다.
> 이 문서는 `main`에 있다. 실험 작업은 `main`에서 브랜치를 따서 한다 (§0).

---

## 0. 브랜치

이 문서는 조정용이라 **`main`에 둔다** — 어느 머신에서 clone해도 브랜치 이름을 몰라도 보이게 하기 위해서다.
실험 산출물·코드 수정은 브랜치에서 한다.

```bash
git checkout main && git pull origin main
git checkout -b pilot/air        # 데이터셋이 늘었으므로 ramdocs 한정 이름은 쓰지 않는다
```

이미 `pilot/air-ramdocs`를 만들어 두었고 **커밋한 것이 없다면** 지우고 다시 만든다:

```bash
git branch -D pilot/air-ramdocs
git checkout -b pilot/air
```

**이미 커밋한 것이 있다면** 지우지 말고 옮겨 붙인다:

```bash
git checkout pilot/air-ramdocs
git rebase main
git branch -m pilot/air
```

---

## 1. 지금 무엇을 하려는가

**논문 1(ThinkConflict)의 RQ1 축소판 — AIR 실측.**

논문 1 전체가 아니다. 측정하려는 것은 단 하나:

> **AIR** = P(FA = wrong | L1 = detected, L2 = correct)
> 추론에서 충돌을 인지하고 올바로 해소했는데, 최종 답변에서 뒤집힌 비율

이 수치가 이후 모든 계획을 좌우한다.

| AIR | 판단 |
|---|---|
| ≥ 10% | 논문 1 헤드라인 확보. 논문 2는 표출 단계 개입(분기 A)으로 확정 |
| 3–10% | 헤드라인을 Shortcut·Blind-Hit로 이동 |
| < 3% | 표출 가설 재검토. 논문 2 분기 B/C로 전환 |

부수 목표: 이 결과로 **8/21 마감 최종논문**을 쓴다 (§5).

---

## 2. 어느 데이터셋을 쓰는가 — RAMDocs + QACC

**2개를 쓴다.** 한 데이터셋만으로는 AIR이 그 데이터셋의 구성 방식에서 온 것인지 구분할 수 없다.

| 데이터셋 | 라벨 상태 | 남은 작업 | 판단 |
|---|---|---|---|
| **RAMDocs** | ✅ `data/3_processed/ramdocs/` 완비 — `a` 1,016 · `b` 500 · `pairs` 676 | **없음** | ✅ 즉시 사용 |
| **QACC** | ✅ 라벨 **공백 0건** (3,049행 / 333문항, `noise` 1638 · `correct` 934 · `conflict` 477). **268문항이 유효 충돌 게이트 통과** | 게이트① 스크리닝 (`pending_screen`) — **LLM 자동화 가능** | ✅ 사용 (§4.2) |
| DRAGged | ❌ `label` 대부분 공백 — `outdated` 578행 중 **518행 공백** | LLM 초벌 + **사람 전수 검토** | ❌ 이번 파일럿 제외 |

### RAMDocs만으로는 안 되는 이유

과제5에서 이미 내린 결론이다:

> *RAMDocs 내부 CV AUC 0.872 — 높지만 신호가 아니다. 오정보 문서를 **추가하는** 방식으로 충돌을 만들었으므로
> 모델은 `n_docs`를 세고 있을 뿐이다. **구성 방식의 흔적이지 충돌의 성질이 아니다.***

RAMDocs는 위키 문단 합성 배치이고 충돌 문항 비율이 91.2%로 편중돼 있다.
여기서만 AIR을 재면 "합성 데이터에서의 AIR"이 된다.
**QACC는 실제 구글 검색 스니펫**이라 생태학적 타당도가 높고, 두 데이터셋에서 방향이 일치하면 주장이 훨씬 강해진다.

### DRAGged를 빼는 이유

`preprocessing/dragged_prep.py`의 build는 채점 트랙 문항에 `unknown` 청크가 있으면 거부한다.
`llm_assist`로 초벌 라벨은 뽑을 수 있으나 **사람 전수 검토**가 남고, 검토 없이 쓰면 사전등록 규약을 깬다.
62문항짜리 `outdated`를 급하게 태우는 것보다 **논문 1 본실험에서 제대로 검토해 주력으로 쓰는 것**이 맞다.

→ 파일럿 한계에 **"주력 데이터셋 DRAGged는 라벨 검토 미완으로 제외"** 를 명시한다.

---

## 3. ⚠️ 모델 2개가 필요하다 — VRAM 확인

`diagnosis/run_labeling.py`의 `SAME_FAMILY` 규칙:

> 트레이스 판정자는 생성 모델과 **다른 계열**이어야 한다 (자기선호 편향 통제, 부록 A(a)).
> 같은 계열을 지정하면 `SystemExit`으로 거부한다.

| 모델 | 대략 VRAM (bf16) |
|---|---|
| Qwen3.6-27B (생성) | ~54GB |
| gpt-oss-20b (판정) | ~40GB |
| **동시 서빙** | **~94GB > 80GB** ❌ |

H100 80GB 한 장에 동시에 못 올린다. 선택지:

| 방안 | 방법 | 비고 |
|---|---|---|
| **A. 순차 서빙** | Qwen 생성 완료 → 종료 → gpt-oss 서빙 → 라벨링 | 안전. 교체 시간 필요 |
| B. 판정자만 양자화 | gpt-oss를 MXFP4(~12–16GB)로 동시 서빙 | 판정자는 텍스트만 읽으므로 허용 가능. **비양자화 원칙은 생성 모델에만** 적용됨을 논문에 명시 |
| C. 판정자 없이 규칙 기반 | `--judge-model` 생략 (코드상 `None` 허용) | ⚠️ **미검증** — `label_generation`이 judge 없이 도는지 10건으로 먼저 확인 |

**10건으로 C부터 시험하라.** 되면 판정자 다운로드 ~40GB를 통째로 아낀다. 안 되면 A.

> ※ §4.2의 **QACC 스크리닝 판정자는 이것과 별개다.** 트레이스를 읽지 않고 질문·답변만 보므로
> API 모델로 돌리면 되고 VRAM을 쓰지 않는다.

---

## 4. 실행 순서

**4.1과 4.2는 병행한다.** 다운로드가 도는 동안 QACC 준비를 끝낸다.

### 4.0 사전 확인 (다운로드 전 필수)

```bash
df -h ~                                    # 54GB(+40GB) 여유 확인
# HF에서 Qwen/Qwen3.6-27B 리포 ID 존재 확인 — serving/client.py MODELS dict 값
#   틀리면 54GB 헛다운로드 + 1시간 손실
```

### 4.1 [트랙 A] 환경 + 모델 다운로드 — 지금 바로 백그라운드

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install vllm && pip install -r requirements.txt
export HF_TOKEN=<값>

nohup hf download Qwen/Qwen3.6-27B > ~/dl_qwen.log 2>&1 &
tail -f ~/dl_qwen.log
```

### 4.2 [트랙 B] QACC 게이트① 스크리닝 — 다운로드와 동시에

가짜 충돌(표기·granularity 차이만 있는 것)을 걸러내는 단계. 현재 **268문항이 `pending_screen`** 상태다.

```bash
python -m preprocessing.llm_assist qacc --judge 1
python -m preprocessing.llm_assist qacc --judge 2
# → data/2_review/qacc/qacc.llm.csv 생성
# → sharp로 판정된 문항의 exclusion_flag를 비운다
python -m preprocessing.qacc_prep build     # → data/3_processed/qacc/*.jsonl
```

- 판정자 2종은 **API 모델 가능** (`.env`에 GPT·Claude·Gemini 키 존재). VRAM 경합 없음
- 비용을 먼저 보려면: `python -m preprocessing.qacc_prep estimate-cost`
- 강행 옵션 `--allow-unresolved`가 있으나 **쓰지 말 것** — 미판정 충돌이 채점 트랙에 새어든다

### 4.3 서빙

```bash
bash serving/launch_qwen.sh     # 포트 8001, bf16 비양자화 고정
```

### 4.4 생성 — 반드시 10건 완주 테스트부터

```bash
head -10 data/3_processed/ramdocs/ramdocs_a.jsonl > /tmp/smoke.jsonl

python -m serving.client \
  --data /tmp/smoke.jsonl \
  --model qwen --env standard \
  --out results/raw/qwen_standard_ramdocs_smoke.jsonl
```

**`<think>` 블록이 JSONL에 제대로 들어갔는지 눈으로 확인할 것.**
`results/`는 지금까지 비어 있었다 = **이 파이프라인은 한 번도 end-to-end로 돌지 않았다.**
파서·프롬프트 버그가 나올 가능성이 높으므로 이 단계를 절대 건너뛰지 말 것.

### 4.5 라벨링 — 10건

```bash
python -m diagnosis.run_labeling \
  --generations results/raw/qwen_standard_ramdocs_smoke.jsonl \
  --data /tmp/smoke.jsonl \
  --out results/labels/qwen_standard_ramdocs_smoke.jsonl
  # 판정자 필요 시: --judge-model gptoss --judge-url http://localhost:8003/v1
```

`diagnosis/metrics.py`의 `print_report()`가 단계별 손실·4경로 분해를 출력한다.

### 4.6 본실행

10건이 통과하면 **데이터셋별 100건씩**으로 확대 (RAMDocs + QACC).

- 시드: `SEEDS = (13, 42, 71, 108, 2026)` 중 **1–2개만** (5개는 시간 부족)
- 환경: `standard`만. CAD·CD2는 이번 파일럿 범위 밖
- 디코딩: `t=0.6, top_p=0.95` 고정 (사전등록 — 건드리지 말 것)
- **데이터셋별로 AIR을 따로 보고한다.** 합치지 않는다 (과제3~5에서 확인한 원칙)

---

## 5. 8/21 마감 최종논문

**마감: 2026-08-21(금) 23:59:00 · 지각 불가 · 미제출 F**

### 제출물 4종

| # | 항목 | 비고 |
|---|---|---|
| 1 | `유진2025711356.docx` **+ `.pdf`** | 둘 다 제출 |
| 2 | 사용한 CSV | 용량 한도 사전 확인 |
| 3 | Colab 링크 | **공유 필수** · `colab.research.google.com` 주소여야 함 (drive 링크 불가) |
| 4 | 코멘트에 링크 기록 | |

### 양식 (`2026논문양식-2.docx`)

- A4 **2단**, 여백 상하 12mm / 좌우 15mm, 줄간격 150%
- 폰트: 큰제목 9 · 본문 8.5 · 그림표 8 · 참고문헌 8
- 구성: 국문제목 → 영문제목 → 저자 → **요약** → 1.서론 → 2.이론적 배경 → 3.본론 → 참고문헌
- 캡션은 `(그림 1)` `(표 1)`, **본문 인용은 괄호 없이** "표 1과 같이"
- 분량 **3쪽 이상**

### 노트북 제출 방식

H100에서 **주피터 노트북 하나로 생성 + 분석**을 모두 수행하고, **출력을 저장한 채로** Colab에 업로드한다.
(과제1 노트북이 출력 0건으로 제출된 전례가 있으니 반드시 확인)

필수 요건: **Python 데이터 처리 · 시각화**가 실제 실행되어 들어가야 한다.

---

## 6. 🔴 체크포인트 규칙

> **8/21 12:00까지 10건 파이프라인이 완주하지 않으면, 즉시 폴백으로 전환한다.**

이 규칙이 없으면 저녁 8시에 파서 디버깅을 하다가 미제출(F)로 간다.

### 폴백: 벤치마크 감사 논문

과제3~5에서 **이미 실행 완료된** 결과로 조립만 하면 되는 논문.

- 위치: `~/대학원/2026-여름-도전학기/Python활용인문사회과학논문쓰기/`
- 재료: 노트북 3개에 **PNG 그림 21장이 이미 박혀 있음** (과제3_1: 4 · 과제4: 7 · 과제5: 10) — 재실행 불필요
- 핵심 결과: Cramér's V=0.762 · 출처 탐침 정확도 1.000 · LODO 평균 AUC 0.534 · ARI(출처) 0.965 vs ARI(충돌) 0.234
- 추가할 것 1개: **QACC `unattributed → 0` 코딩 민감도 분석**
  - 현행 코딩: 상위 0.427 / 하위 0.261, OR 2.11, χ²=445.6
  - unattributed 제외: 상위 0.870 / 하위 0.888, **OR 0.84**, χ²=4.2
  - → QACC의 위치 편향은 주석 커버리지 산물. 논문의 가장 날카로운 결과

두 논문 모두 나중에 논문 1의 §2·§3 재료가 되므로 어느 쪽도 낭비가 아니다.

---

## 7. 배경 문서

| 파일 | 내용 |
|---|---|
| `docs/연구계획서_ThinkConflict.md` | 논문 1 계획 |
| `docs/preregistration.md` | 사전등록 규약 — **건드리지 말 것** |
| `docs/thinkconflict_repo_plan.md` | 레포 구조·단계 |
| `ThinkConflict_연구보고.pptx` | 최신 연구 계획 (24슬라이드) |
| `~/대학원/.../연구계획서/2편_연구계획_진단과처방.md` | 논문 1·2 구조 + 선행연구 조사표 |

## 8. 하지 말 것

- `docs/preregistration.md` 수정 — 커밋 타임스탬프가 사전등록의 물증
- 생성 모델 양자화 — `launch_qwen.sh`에 bf16 고정 이유가 적혀 있음 (로짓·궤적 왜곡 방지)
- `qacc_prep build --allow-unresolved` 강행 — 미판정 충돌이 채점 트랙에 새어든다
- DRAGged 검토 게이트 우회 — 논문 1 본실험의 신뢰도가 걸림
- 시드·디코딩 설정 변경 — 사전등록 위반
- 데이터셋 합쳐서 AIR 보고 — 반드시 분리 보고
