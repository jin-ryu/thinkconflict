# RUNLOG — AIR·완화 이득 분해 파일럿 (H100, 2026-08-21)

> 실험 세션 기록. 논문 방법 절에 옮길 사실만 적는다. 수치 해석은 하지 않는다.
> 서버 시계는 KST보다 약 9시간 빠르다 — 아래 시각은 **서버 시각**(로그와 대조용)이다.

## 1. 실행 설정

| 항목 | 값 |
|---|---|
| 생성 모델 | `Qwen/Qwen3.6-27B` (HF 리비전 `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9`) · bf16 비양자화 · vLLM 0.27.1 |
| 디코딩 | `temperature=0.6, top_p=0.95` (사전등록 고정값, `serving/client.py DECODING`) |
| 시드 | **13** 단일 (셔플 시드 = 생성 시드) |
| max_tokens | 8192 · `max_model_len` 32768 |
| 환경 | `standard` · `reflection` · `standard_nothink`(보너스, 사고 채널 하드 토글 off) |
| 판정자 | 하이브리드 — 규칙 1차 → 규칙이 `unresolved`로 넘긴 건만 `openai/gpt-oss-20b`(교차 계열) 판정. gpt-oss는 MXFP4 네이티브 정밀도로 서빙(`DTYPE=auto`; **판정자 전용** — 생성 모델 비양자화 원칙과 무관) |
| 서빙 | 순차(방안 A): Qwen 생성 → 종료 → gpt-oss 라벨링. 동시 서빙 불가(94GB > 80GB) |

## 2. 데이터셋·표본

| 데이터셋 | 표본 파일 | N | 구성 | 비고 |
|---|---|---|---|---|
| `ramdocs_a` | `data/pilot/ramdocs_a.jsonl` | **200** | `misinformation` 전부 (`no_conflict` 제외) | `ramdocs_a.jsonl` 495 misinformation 문항을 시드 13으로 셔플한 앞 200 |
| `qacc` | `data/pilot/qacc.jsonl` | **138** | `misinformation` 120 · `outdated` 18 | 게이트① 통과 140 중 채점 가능(정답 있음) 138. `conflicting_opinions` 2건 제외 |
| DRAGged | — | — | — | 라벨 검토 미완으로 범위 밖 (인수인계 §2) |

**RAMDocs 표본을 `head -100`이 아니라 충돌 문항 200으로 잡은 이유**: `head -100`은 `no_conflict` 45건을 포함해
L1·AIR 분모가 절반으로 준다. 표본은 시드로 고정돼 있고 두 환경이 같은 파일을 쓰므로 짝짓기에는 영향이 없다.
`records.csv`에 `conflict_type`이 있어 층화는 논문 쪽에서 가능하다.

### QACC 충돌 유형(conflict_type) 부여 — 연구보고 11·13p "assign(LLM+인간)"

- 사전값: `qacc_prep`의 규칙 prior — 원본 `reasons`에 최신성 코드(A)가 있으면 `outdated`, 아니면 `misinformation` (draft: 292/41)
- 게이트① 판정자 2종(Qwen 사고 off · gpt-oss effort low)이 sharp/soft와 함께 **유형(outdated/misinformation/conflicting_opinions/na)** 을 판정. **두 판정자 유형이 일치할 때만** 덮어씀 — 채점 트랙 140문항 중 **128은 판정자 일치 유형**, **12는 사전값 유지**(유형 불일치 조합: outdated↔misinformation 8, opinions↔misinformation 2, 빈칸 2). 판정자 일치로 사전값에서 바뀐 문항 23
- 최종 pilot 표본: `misinformation` 120 · `outdated` 18 (`conflicting_opinions` 2는 정답 없음으로 제외)
- ⚠️ **사람 검수 미실시** — 연구보고 13p "LLM이 먼저 나누고 사람이 검수" 중 앞 단계만. 유형 축 분석(유형별 층화·유형 인지율)은 이 한계를 안고 읽는다. `records.csv`에 `conflict_type`·`type_recognition` 열이 있어 재분류 후 재집계 가능.
- **유형 인지율(RQ1 두 번째 지표)** 은 `summary_air.json` 셀의 `type_recognition_rate`·`by_conflict_type`, 노트북 표 5에 있다. 값은 `labeler.TYPE_CUES`의 **규칙 단서**(outdated: 'more recent/newer/연도 쌍…', misinformation: 'misinformation/unreliable/credib…')로만 잰 것이라 단서 목록의 민감도에 좌우된다 — 실측: outdated(DRAGged) 0.34→0.77(standard→reflection)인데 misinformation(RAMDocs 0.01–0.03 · QACC 0.04–0.09)은 매우 낮다. 모델이 오정보를 '틀린 문서'로 다루면서 해당 어휘를 안 쓰는 경우가 많아 **과소 추정**일 가능성이 크며, 판정자 기반 유형 인지 판정은 본실험 과제다.

### QACC 게이트① 스크리닝 (§5.2)

- 판정자 1: `Qwen/Qwen3.6-27B` (사고 off) · 판정자 2: `openai/gpt-oss-20b` (effort=low) — 교차 계열
- 333문항 중 **둘 다 sharp 140** → 채점 트랙 / 둘 다 soft 62 → `soft_conflict` / **불일치·빈 판정 66 → `judge_disagreement`로 제외**
- 불일치 66건은 사람 adjudication 대상이나 이번엔 시간상 **보수적으로 제외**했다(채점 트랙에 미판정 충돌이 새어들지 않는다). `--allow-unresolved`는 쓰지 않았다. 입력 CSV: `data/2_review/qacc/qacc.pilot.csv` (`qacc.llm.csv`에서 pending만 플래그 변경)
- 판정자 1 재현성: 동일 설정 재실행 시 333건 중 1건만 verdict 변동(`judges/judge1_v1.csv` ↔ `judge1.csv`), 일치 집합 변화 없음

## 3. 실행 순서·소요 (서버 시각)

| 시각 | 단계 |
|---|---|
| 01:07 | Qwen 다운로드 시작 (55.6GB, ~147MB/s) |
| 01:21–01:35 | vLLM 기동 실패 2회 → 수정 후 기동 (§5 이슈 1·2) |
| 01:40–02:05 | 스모크 10건 생성 + 라벨링 — **파이프라인 첫 end-to-end 완주**. 파서 버그 발견·수정 (§5 이슈 3) |
| 02:07–02:22 | RAMDocs misinformation 200 × 시드 13·42 `standard` 생성 (400건, 12 동시요청, ~18건/분) |
| 02:25–02:58 | GPU → gpt-oss. QACC 판정자 2 (이슈 5·6 수정 후 재실행) |
| 04:02–04:08 | RAMDocs 400건 판정자 라벨링 (부수 결과, §6) |
| 04:40–04:44 | QACC 판정자 2 최종 · `qacc_prep build` (140 통과) |
| 04:44–04:48 | GPU → Qwen |
| 04:48–05:16 | 생성 체인: `reflection` ramdocs(11분) → `standard` qacc(6분) → `reflection` qacc(7분) → `standard_nothink` ramdocs(2분)·qacc(1분) |
| 05:16–05:19 | GPU → gpt-oss |
| 05:19–05:33 | 라벨링 6파일(규칙+판정자), 파싱 실패 0 |
| 05:35 | `export_records` → `records.csv` 1,014행 · `summary_air.json` 6셀·전환 4 |

**총 소요**: 다운로드 시작(01:07)부터 산출물(05:35)까지 약 4.5시간. 그중 실제 GPU 계산은 생성 ~30분 + 라벨링 ~15분이고, 나머지는 다운로드·기동 실패 디버깅·모델 스왑(3회, 회당 4–6분)·파이프라인 버그 수정.

## 4. 투입·제외 건수

| 데이터셋 | 환경 | 문항 | 레코드 | FA correct/wrong/abstain | L1 detected | AIR 분모 | 파싱 실패 |
|---|---|---|---|---|---|---|---|
| ramdocs_a | standard | 200 | 200 | 168/32/0 | 111 | 83 | 0 |
| ramdocs_a | reflection | 200 | 200 | 176/24/0 | 186 | 141 | 0 |
| ramdocs_a | standard_nothink | 200 | 200 | 188/12/0 | 0 | 0 | 0 |
| qacc | standard | 138 | 138 | 97/41/0 | 33 | 30 | 0 |
| qacc | reflection | 138 | 138 | 101/37/0 | 133 | 111 | 0 |
| qacc | standard_nothink | 138 | 138 | 109/29/0 | 0 | 0 | 0 |

- 생성 오류·파싱 실패·제외 문항 **0건**. 기권(abstain) 0건 — 모든 기권율은 0.
- 환경 간 `item_id` 집합 동일 확인(데이터셋별 3환경 모두 같은 집합) → 전환 행렬 짝짓기 가능.
- `records.csv`의 `L2` 빈칸(551행) = L1 미탐지 건(L2는 L1=detected일 때만 판정됨 — `diagnosis/labeler.py`). `path` 빈칸(175행) = 오답.
- **`standard_nothink` 셀 주의**: 사고 채널이 없으므로 L1은 정의상 전부 `unrecognized`(Loss_L1=1.0), L2·AIR은 정의되지 않는다(`null`). 이 셀에서 비교 가능한 지표는 **정확도와 전환 행렬**뿐이다. 정답은 전부 `blind_hit`으로 귀속되는데 이는 "언어화된 인지 없음"의 기계적 결과다.
- `summary_air.json`의 규약: N<20 셀의 비율은 `null`, 개수만 기록. 전환 지표(LGR·HR·flip)도 동일 — LGR 분모(새로 정답이 된 문항)가 7·11·13·21로 작아 대부분 `null`이다. 이는 기저 정확도가 이미 높아(0.70–0.84) 새로 맞는 문항 자체가 적기 때문이며, 원자료(`records.csv`)에서 pooled 계산은 가능하다.

## 5. 중간에 바꾼 것 — 무엇을 왜

모두 **측정 도구의 버그 수정**이며 사전등록 항목(시드·디코딩·라벨 정의)은 건드리지 않았다. 회귀 테스트 동반(`tests/test_diagnosis.py`, 92개 통과).

| # | 위치 | 문제 | 수정 |
|---|---|---|---|
| 1 | `.venv/.../flashinfer/comm/fd_exchange.py` | py3.11에서 `array.array[int]` 주석 평가 실패 → vLLM 기동 불가 (vLLM은 `ImportError`만 잡아 통과 못 함) | `from __future__ import annotations` 1줄 (venv 패치, 레포 외) |
| 2 | `serving/launch_qwen.sh` | Qwen3.6은 하이브리드 Mamba — 기본 `max_num_seqs=1024` > 캐시 블록 334 → CUDA 그래프 캡처 실패 | `--max-num-seqs 256` (서빙 동시성 상한, 디코딩과 무관) |
| 3 | `diagnosis/trace_parser.py` | Qwen3.6 템플릿은 `<think>`를 **프롬프트**에 넣어 완성문엔 `</think>`만 남음 → 전 건 `no_think_tag` 파싱 실패 | 닫는 태그만 있는 경우 파싱. 닫은 직후 절단은 `empty_answer` 실패로 분리(빈 답이 기권으로 새는 것 방지) |
| 4 | `diagnosis/run_labeling.py` | 행동 트랙 필터가 `l2 is not None` → L1 미탐지 건이 통째로 빠져 **Loss_L1이 구조적으로 0**, blind_hit 소멸 | `fa is not None`(채점 성립 여부)으로 |
| 5 | `diagnosis/labeler.py` | L2 규칙의 160자 고정 창이 문장·절 경계를 넘어 지지/기각 동사를 엉뚱한 인용에 귀속 (실측 2건: 정답 문서 지지를 `wrong`으로 뒤집음) | 같은 문장·같은 절 안, 인접 인용 사이만 판독. 지지·기각 공존 시 규칙 기권→판정자 |
| 6 | `preprocessing/llm_assist.py` · `diagnosis/labeler.py` | 사고형 판정자가 짧은 토큰 예산을 사고에 다 써 **빈 판정**(QACC 333건 전부). gpt-oss는 선택지 목록을 되받아써 앞에서부터 찾으면 **첫 선택지**로 오염 | 사고 off(Qwen)/effort=low(gpt-oss) + 예산 256, 폼 필드 기준 파싱(`form_field`) |
| 7 | `diagnosis/run_labeling.py` | 자기선호 가드가 정확 일치 비교라 `Qwen/Qwen3.6-27B`를 넘기면 통과 | 부분 문자열 비교 |
| 8 | `serving/client.py` | 순차 요청(32초/건)으로 100건당 53분 | `--workers` 동시 요청(기본 1 — 기존 동작 유지). 디코딩·시드는 요청마다 동일 |
| 9 | `serving/launch_gptoss.sh` | bf16 강제 시 MXFP4 체크포인트를 역양자화 | `DTYPE` 환경변수(기본 bf16 유지, 판정자 전용 실행만 `auto`) |

추가: `diagnosis/export_records.py` 신규 — `records.csv`·`summary_air.json` 생성 (규격 §6.1·6.2).

**알려진 미수정**: `labeler.label_stance`의 판정자 과제(`answer_stance_vs_trace`)가 L2용 프롬프트(선택지 correct/wrong/unresolved)를 그대로 써서 `stance`는 항상 None이 된다. 정답 있는 문항만 쓰는 이번 파일럿에는 영향 없음(규격에 stance 없음). 판정자 호출이 헛되이 2배 드는 비효율만 있음.

## 6. 부수 결과 — RAMDocs `standard` 200문항 × 시드 13·42 (원자료: `results/raw/qwen_standard_ramdocs_a_mis200_seeds13-42.jsonl`, git 미포함)

라벨링 방식 민감도. 같은 400 레코드를 규칙만 / 규칙+gpt-oss 판정자로 라벨:

| | 규칙만 | +판정자 |
|---|---|---|
| AIR | 0.066 (N=76) | 0.092 (N=153) CI95 [0.046, 0.144] |
| Loss_L1 | 0.480 | 0.480 |
| Loss_L2 | 0.635 | 0.264 |
| legitimate / shortcut / discordant / blind | .211 / .298 / .030 / .461 | .414 / .036 / .089 / .461 |

규칙이 `unresolved`로 기권한 115건(detected의 55%)을 판정자가 대부분 `correct`로 해소 → AIR 분모 2배. L1·blind_hit은 판정자 무관.
본 산출물(`records.csv`)은 **판정자 포함** 라벨이며 `l2_source` 열로 구분 가능.

## 6b. 추가 실험 — DRAGged 사실충돌 44문항 (2026-08-21 오후 추가)

커밋 `f7ef15c`(과제3 문서 라벨 부트스트랩)를 받아 DRAGged를 채점 트랙에 넣었다. 같은 설계(시드 13, standard·reflection·standard_nothink, 판정자 gpt-oss)로 돌렸다.

**문서 라벨 확정 절차** (`data/2_review/dragged/`):
1. 과제3 `supports_gold_a3 == 1` → `label=correct` 104행 (`a3_stringmatch`), 규칙 확정 60행 유지
2. 남은 빈칸 459행(outdated 429 + misinformation 30)을 gpt-oss-20b(effort low)로 초벌 — `llm_assist dragged`는 QACC에서 고친 것과 같은 버그(`max_tokens=60`, 줄 위치 파싱)가 있어 먼저 수정
3. 층화 표본 **145행**(유형 × a3값 × LLM 라벨, 시드 13; 층 상한 때문에 150 미만)을 **이 세션의 Claude가 본문을 읽고 직접 판정** — `review_sheet_150.csv`의 `label_reviewed`·`note`
4. gpt-oss ↔ 검토 일치율 0.930, **Cohen's κ = 0.885** (N=143, 빈칸 2 제외; conflict-이분 κ 0.874; outdated 0.945 / misinformation 0.800) → 부트스트랩 문서 §6 규칙(κ ≥ 0.7)대로 LLM 라벨 채택, 검토 145행은 검토 판정이 덮어씀(12행 변경). `review_kappa.json`
5. `dragged_prep build` (`--allow-unresolved` 없이) → 사실충돌 67 중 **채점 가능 44** (outdated 41 · misinformation 3). 제외 23 = 유효충돌쌍 없음 15 · no_match 3 · date_tie 3 · date_absent 2
6. 출처는 `label_sources.csv` (`rule_draft` 60 · `a3_stringmatch` 104 · `llm_gptoss` 314 · `reviewed_claude_session` 145)

⚠️ **한계 — 반드시 명시**: 사전등록의 "사람 전수/κ 검토"에서 검토자가 **사람이 아니라 이 세션의 Claude**다. κ는 교차 계열 LLM 2종(gpt-oss ↔ Claude) 간 일치이지 사람-LLM 일치가 아니다. 논문 1 본실험 전에 사람이 `review_sheet_150.csv` 145행(불일치 사유는 `note`)을 재검토해야 하며, 그 전까지 DRAGged 셀은 **예비 결과**로만 읽는다. 표본이 44라 AIR 분모는 20 미만 → `summary_air.json`에서 `null`(개수만).

`conflicting_opinions` 115문항은 채점 트랙에서 제외했다(정답 없음). 방침 제안: any-gold 확장(B)이 아니라 사전등록된 자기일관성 트랙(§1.8·§3.2, `label_stance`)으로 보내는 것 — 정답·문서 라벨이 필요 없다. 단 현재 `label_stance`의 판정 프롬프트가 L2용이라 stance가 항상 None이 되는 미수정 버그(§5 말미)를 먼저 고쳐야 한다.

### 6c. DRAGged 실행 기록 (서버 시각)

| 시각 | 단계 |
|---|---|
| 06:5x–07:1x | llm_assist 수정 · gpt-oss 초벌 459행 · 검토 145행 · κ · build |
| 07:19–07:23 | GPU → Qwen |
| 07:23–07:30 | 생성 `standard`(3분) · `reflection`(3분) · `standard_nothink`(1분), 44문항 × 시드 13, 12 동시요청 |
| 07:30–07:32 | GPU → gpt-oss |
| 07:32–07:34 | 라벨링 3파일(규칙+판정자), 파싱 실패 0 |
| 07:36 | `export_records` 재실행 → `records.csv` **1,146행**(9셀) · `summary_air.json` 9셀·전환 6 · `air_analysis.ipynb` 재실행(그림 4, 에러 0) |

| 데이터셋 | 환경 | 문항 | FA correct/wrong/abstain | L1 detected | AIR 분모 | 파싱 실패 |
|---|---|---|---|---|---|---|
| dragged | standard | 44 | 34/10/0 | 21 | 18 (<20 → AIR null) | 0 |
| dragged | reflection | 44 | 35/9/0 | 41 | 38 | 0 |
| dragged | standard_nothink | 44 | 37/7/0 | 0 | 0 | 0 |

- 환경 간 `item_id` 집합 동일(44). `records.csv`의 `dataset=dragged`, `conflict_type ∈ {outdated 41, misinformation 3}`.
- **AIR 분모 18(standard)은 20 미만이라 비율을 보고하지 않는다**(개수만). 이는 표본 44의 구조적 한계이지 결과가 아니다.

## 7. 한계

- DRAGged(주력) 제외 · QACC 불일치 66문항 사람 adjudication 미실시(제외)
- 시드 1개 — 문항 내 안정성 플래그 산출 불가(전환 행렬의 `unstable`은 항상 0)
- 판정자 옵션 스왑(부록 A(a)) 미적용, 판정자 1종만
