# DRAGged 문서 라벨 부트스트랩 — 과제3 산출물 재활용

작성 2026-08-21 · 상태: **검증 완료, 적용 대기**

---

## 0. 요약

DRAGged는 build 게이트에 막혀 채점 트랙에 못 들어간다. 원인은 **문서 단위 라벨 부재**다.
그런데 별도 파이프라인(석사 과제3)이 같은 원본에서 이미 문서 단위 판정을 상당 부분 만들어 두었고,
**조인이 4,212행 전부에서 무손실로 성립함을 검증했다.**

이 문서는 그 조인 근거와, 조인 후에도 남는 작업을 정리한다.

| | 조인 전 | 조인 후 |
|---|---|---|
| `outdated` 결측 | 518 / 578행 | **43행** |
| `misinformation` 결측 | 45 / 45행 | **9행** |
| 사실 충돌 2유형 결측 합 | 563행 | **52행 (−91%)** |

---

## 1. 왜 DRAGged가 막혀 있나

`preprocessing/dragged_prep.py`의 build는 채점 트랙 문항에 `unknown` 청크가 있으면 거부한다.
현재 draft CSV의 상태는 다음과 같다.

```
라벨 값 분포 : correct 800 · noise 659 · 공백 2,753
conflict 라벨 : 0개
게이트(correct+conflict 공존) 통과 문항 : 458 중 0개
```

`conflict`가 하나도 없다. `build_draft`의 규칙이 **"정답을 담았는가"만 판정**할 수 있기 때문이다
(코드 주석: *"나머지 문서는 unknown(빈칸)으로 남긴다. 규칙은 '정답을 담았는가'만 볼 수 있을 뿐"*).
어떤 문서가 정답과 **모순**되는지는 문자열 매칭으로 알 수 없다.

**주의**: DRAGged의 *문항 단위* 충돌 유형(5유형, 전문가 주석)은 458문항 전부 존재한다.
없는 것은 *문서 단위* 지지/모순 라벨이며, 해소(L2) 채점에 필요한 것은 후자다.

---

## 2. 재활용 대상 — 과제3 파이프라인

경로: `~/대학원/2026-여름-도전학기/Python활용인문사회과학논문쓰기/과제3/`
산출물: `data/processed/rag_conflict_docs.csv` (CONFLICTS 4,212행)

같은 원본 `conflicts.jsonl`을 별도 스크립트(`scripts/02_build_dataset.py`)로 정규화했고,
`answer_in_text()`로 문서별 정답 포함 여부를 **1 / 0 / 결측** 세 값으로 기록했다.
thinkconflict 쪽이 0을 공백으로 버린 것과 달리 **0을 명시적으로 남긴 것**이 차이다.

| `doc_supports_gold` | 행 수 |
|---|---|
| 1 (정답 문자열 포함) | 556 |
| 0 (정답 문자열 없음) | 1,062 |
| 결측 (판정 불가) | 2,594 |

과제3의 보수적 규칙: 정답이 없거나 2글자 이하이거나 yes/no류면 **0이 아니라 결측**으로 남긴다.

---

## 3. 조인 검증 — 무손실 확인

두 파이프라인은 ID 체계가 다르다.

| | 문항 ID | 문서 ID |
|---|---|---|
| thinkconflict | `dragged-0012` | `0`, `1`, … (문항 내 0-based) |
| 과제3 | `CONFLICTS-0000` | `CONFLICTS-0000-d01` (`doc_rank` 1-based) |

직접 교집합은 0이다. **질문 텍스트 + 문서 순서**로 조인한다.

```python
tk["qkey"]   = tk.question.str.strip().str.lower()
c3["qkey"]   = c3.question.str.strip().str.lower()
tk["rank1"]  = tk.doc_id.astype(int) + 1          # 0-based → 1-based
j = tk.merge(c3, left_on=["qkey", "rank1"], right_on=["qkey", "doc_rank"], how="left")
```

검증 결과 — **네 항목 모두 완전 일치**:

| 확인 | 결과 |
|---|---|
| 문항 수 | 458 = 458 |
| 질문 텍스트 교집합 | 458 / 458 |
| 문항별 문서 수 일치 | 458 / 458 |
| 조인 성공 행 | **4,212 / 4,212** |
| 본문 앞 80자 일치 | **4,212 / 4,212 (100.0%)** |

두 파이프라인이 원본의 `search_results` 순서를 똑같이 보존했다는 뜻이다.
본문 일치 검증까지 통과했으므로 순서 조인은 안전하다.

---

## 4. 산출 파일

`data/2_review/dragged/labels_from_assignment3.csv` (4,212행)

| 컬럼 | 의미 |
|---|---|
| `question_id` · `doc_id` | **thinkconflict 자체 ID** — draft CSV와 그대로 조인된다 |
| `conflict_type` | 5유형 |
| `question` | 조인 검증용 |
| `supports_gold_a3` | 과제3 판정: `1` / `0` / 공백 |
| `source_a3` | `derived_stringmatch` 또는 `undetermined` |
| `label_current` | 현재 draft CSV의 label (비교용) |

### 유형별 확보량

| 유형 | 문항 | 행 | `1` | `0` | 결측 |
|---|---|---|---|---|---|
| **outdated** | 62 | 578 | **122** | **413** | 43 |
| **misinformation** | 5 | 45 | **15** | **21** | 9 |
| complementary | 115 | 1,067 | 16 | 27 | 1,024 |
| conflicting_opinions | 115 | 1,123 | 0 | 0 | 1,123 |
| no_conflict | 161 | 1,399 | 403 | 601 | 395 |

---

## 5. ⚠️ 그대로 쓰면 안 되는 이유

**`supports_gold_a3 == 0`은 `conflict`가 아니다.**

0의 의미는 *"정답 문자열이 본문에 없다"* 이다. 이 안에는 두 가지가 섞여 있다.

- **conflict** — 정답과 모순되는 답(예: 구버전 정답)을 담은 문서
- **noise** — 질문과 무관하거나 어느 답도 담지 않은 문서

`passes_valid_conflict_gate`는 `correct`와 `conflict`의 공존을 요구하므로,
0을 일괄 `conflict`로 매핑하면 **노이즈 문서가 충돌 문서로 둔갑**한다.
그러면 L2 채점이 오염되고, 그것은 사전등록이 막으려던 바로 그 사고다.

`1 → correct` 매핑은 안전하다(문자열 포함은 보수적 규칙 통과분).

---

## 6. 남은 작업

| # | 작업 | 규모 | 자동화 |
|---|---|---|---|
| 1 | `1` → `label = correct` 일괄 반영 | 137행 (사실충돌 2유형) | ✅ 스크립트 |
| 2 | **`0` → `conflict` / `noise` 판별** | **434행** (413 + 21) | LLM 초벌 + 층화 인간 검증 |
| 3 | 결측 보충 | 52행 | LLM 초벌 + 검증 |
| 4 | `conflicting_opinions` 방침 결정 | 115문항 | ❌ **설계 판단 필요** |

### 2번 권장 절차

1. `preprocessing/llm_assist.py`로 434행 초벌 판정 (`conflict` / `noise`)
2. 층화 표본 150행을 사람이 직접 라벨
3. Cohen's κ 산출 → **κ ≥ 0.7이면 LLM 라벨 채택**, 미만이면 정의 수정 후 재라벨
4. 판정 근거를 `label_source` 컬럼에 기록 (`annotated` / `llm_verified` / `derived_rule`)

전수 검토가 아니라 κ 검증 방식이므로 **반나절 규모**다.

### 4번이 진짜 문제

`conflicting_opinions` 115문항은 `gold_answer` 자체가 비어 있어 1도 0도 판정되지 않았다(표 참조: 1이 0개, 0이 0개).
정답이 하나로 정해지지 않는 유형이므로 **"정답 지지 문서" 개념이 성립하지 않는다.**
이는 라벨링 노동의 문제가 아니라 채점 규칙 설계의 문제다.

선택지:

- **A. 제외** — 사실 충돌(`outdated` + `misinformation`) 67문항만 채점 트랙에 넣는다. 정의가 깨끗하나 표본이 얇다
- **B. any-gold 적용** — 계획서 §3.2 *"복수 유효 정답 중 하나를 지지·표출하면 correct"* 규칙을 확장 적용해 182문항으로 늘린다. 표본은 늘지만 복수 정답 목록을 별도로 구축해야 한다

논문 1의 표본 규모가 B에 달려 있다. **실험을 늘리기 전에 이 결정을 먼저 내려야 한다.**

---

## 7. 재현

```bash
python3 - <<'PY'
import pandas as pd, glob, re
G3 = "<과제3 경로>/data/processed/rag_conflict_docs.csv"
c3 = pd.read_csv(G3, encoding="utf-8-sig"); c3 = c3[c3.dataset == "CONFLICTS"].copy()
c3["qkey"] = c3.question.str.strip().str.lower()
tks = []
for p in glob.glob("data/2_review/dragged/*.draft.csv"):
    t = pd.read_csv(p, encoding="utf-8-sig"); t.columns = [c.lstrip("﻿") for c in t.columns]
    t["type"] = re.search(r"dragged_(.+)\.draft", p).group(1); tks.append(t)
tk = pd.concat(tks, ignore_index=True)
tk["qkey"] = tk.question.str.strip().str.lower(); tk["rank1"] = tk.doc_id.astype(int) + 1
j = tk.merge(c3[["qkey","doc_rank","doc_supports_gold","doc_support_source","doc_text"]],
             left_on=["qkey","rank1"], right_on=["qkey","doc_rank"], how="left")
assert j.doc_rank.notna().all()
assert (j.text.fillna("").str.strip().str[:80] == j.doc_text.fillna("").str.strip().str[:80]).all()
print("조인 검증 통과:", len(j), "행")
PY
```

과제3 저장소에는 수집 스크립트(`scripts/01_download.py`, `02_build_dataset.py`)와
SHA-256 체크섬 매니페스트가 함께 있어 원본까지 재현 가능하다.
