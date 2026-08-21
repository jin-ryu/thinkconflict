# AIR 파일럿 인수인계 (2026-08-20)

> H100 서버에서 새 Claude Code 세션을 열었다면 **이 파일부터 읽고 이어서 진행**한다.
> 브랜치: `pilot/air-ramdocs`

---

## 1. 지금 무엇을 하려는가

**논문 1(ThinkConflict)의 RQ1 축소판 — RAMDocs 한정 AIR 실측.**

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

## 2. 왜 RAMDocs만인가

| 데이터셋 | `data/3_processed/` | 이유 |
|---|---|---|
| **RAMDocs** | ✅ `ramdocs_a.jsonl` (1,016) · `ramdocs_b.jsonl` (500) · `ramdocs_pairs.jsonl` (676) | 문서별 `correct/misinfo/noise` 라벨이 **원본 내장** → 사람 검토 불필요 |
| DRAGged | ❌ 비어 있음 | `data/2_review/dragged/*.draft.csv`에서 사람 전수 검토 미완 |
| QACC | ❌ 비어 있음 | 동일 |

`preprocessing/schema.py`의 `assert_reviewed`가 검토 미완 데이터의 빌드를 거부한다.
DRAGged 458건 검토는 마감 내 불가능하므로 **파일럿은 RAMDocs로 한정**한다.

이 제약은 논문에 한계로 명시한다 — RAMDocs는 위키 문단 합성 배치라 생태학적 타당도가 낮고,
충돌 문항 비율이 91.2%로 편중돼 있다.

---

## 3. ⚠️ 먼저 해결할 문제 — 모델 2개가 필요하다

`diagnosis/run_labeling.py`의 `SAME_FAMILY` 규칙:

> 판정자는 트레이스 생성 모델과 **다른 계열**이어야 한다 (자기선호 편향 통제, 부록 A(a)).
> 같은 계열을 지정하면 `SystemExit`으로 거부한다.

즉 **생성용 Qwen + 판정용 gpt-oss** 두 개가 필요하다. 그런데:

| 모델 | 대략 VRAM (bf16) |
|---|---|
| Qwen3.6-27B | ~54GB |
| gpt-oss-20b (MoE 21B) | ~40GB |
| **동시 서빙** | **~94GB > 80GB** ❌ |

**H100 80GB 한 장에 동시에 못 올린다.** 선택지:

| 방안 | 방법 | 비고 |
|---|---|---|
| **A. 순차 서빙** ✅ 권장 | Qwen 서빙 → 생성 완료 → 종료 → gpt-oss 서빙 → 라벨링 | 안전. 모델 교체 시간 필요 |
| B. 판정자만 양자화 | gpt-oss를 MXFP4로 (~12–16GB) 올려 동시 서빙 | 판정자는 텍스트만 읽으므로 양자화 허용 가능. 단 비양자화 원칙은 **생성 모델에만** 적용됨을 논문에 명시 |
| C. 규칙 기반 라벨만 | `--judge-model` 생략 (코드상 `None` 허용) | ⚠️ **확인 필요**: `label_generation`이 judge 없이 동작하는지 미검증. 되면 가장 빠름 |

**먼저 C를 10건으로 시험해 보라.** 되면 판정자 다운로드(~40GB)를 통째로 아낀다.
안 되면 A로 간다.

---

## 4. 실행 순서

### 4.0 사전 확인 (다운로드 전 필수)

```bash
df -h ~                                    # 54GB(+40GB) 여유 확인
# HF에서 Qwen/Qwen3.6-27B 리포 ID가 실제로 존재하는지 브라우저로 확인
#   → serving/client.py MODELS dict에 적힌 값. 틀리면 54GB 헛다운로드
```

### 4.1 환경

```bash
git checkout -b pilot/air-ramdocs
python -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install vllm && pip install -r requirements.txt
export HF_TOKEN=<값>
```

### 4.2 모델 다운로드 (가장 긴 직렬 작업 — 제일 먼저 백그라운드로)

```bash
nohup hf download Qwen/Qwen3.6-27B > ~/dl_qwen.log 2>&1 &
tail -f ~/dl_qwen.log
```

### 4.3 서빙

```bash
bash serving/launch_qwen.sh     # 포트 8001, bf16 비양자화 고정
```

### 4.4 생성 — 먼저 10건으로 완주 테스트

```bash
head -10 data/3_processed/ramdocs/ramdocs_a.jsonl > /tmp/smoke.jsonl

python -m serving.client \
  --data /tmp/smoke.jsonl \
  --model qwen --env standard \
  --out results/raw/qwen_standard_ramdocs_smoke.jsonl
```

**여기서 `<think>` 블록이 JSONL에 제대로 들어갔는지 눈으로 확인할 것.**
`results/`는 지금까지 비어 있었다 = **이 파이프라인은 한 번도 end-to-end로 안 돌았다.**
파서·프롬프트에서 버그가 나올 가능성이 높으므로 10건 단계를 절대 건너뛰지 말 것.

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

10건이 통과하면 **100–200건**으로 확대.

- 시드: `serving/client.py`의 `SEEDS = (13, 42, 71, 108, 2026)` 중 **1–2개만** (5개는 시간 부족)
- 환경: `standard`만. CAD·CD2는 이번 파일럿 범위 밖
- 디코딩: `t=0.6, top_p=0.95` 고정 (사전등록, 건드리지 말 것)

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
- 분량 **3쪽 이상** (제출안내 "최소 3쪽" ≥ 양식 "2페이지 이상")

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
- DRAGged·QACC 검토 게이트 우회 — 논문 1 본실험의 신뢰도가 걸림
- 시드·디코딩 설정 변경 — 사전등록 위반
