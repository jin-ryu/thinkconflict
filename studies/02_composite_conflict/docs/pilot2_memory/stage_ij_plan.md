# 파일럿 2 Stage I–J: 데이터 보강과 간섭 검증 계획

> 작성일: 2026-08-28
> 상태: Stage I-1·I-2 구축, Stage J-1~J-4 완료(2026-08-28). 결과는 [stage_j_result.md](stage_j_result.md). H-B·H-C 기각
> 위치: 파일럿 2의 연장(2F 데이터 보강, 2G 간섭 검증). 문제 정의·MemConflict instance·judge protocol·지표를 Stage G–H와 그대로 쓰므로 [plan.md §11.1](plan.md#111-pilot-번호-결정) 기준에 따라 새 파일럿으로 분리하지 않는다
> 선행: [Stage G 결과](stage_g_result.md), [Stage H 결과](stage_h_result.md), [2026 memory conflict 조사](../background/related_work_memory_2026.md)
> 후속: Stage J gate 통과 후 [파일럿 3 CMCR 계획](../pilot3_cmcr/plan.md)
> 목표 제출: 2026-10 ARR

---

## 0. 이 단계가 결정할 것

Pilot 2까지의 결과는 세 모델에서 (1) atomic 성공 후 composite 실패, (2) evidence-order flip, (3) 같은 K에서 H1→H2 하락을 관측했다. 그러나 다음 넷이 비어 있어 논문 주장으로 올릴 수 없다.

| 공백 | 왜 문제인가 | 이 파일럿의 대응 |
|---|---|---|
| H 효과와 policy identity가 얽힘 | H2 cell은 VERIFY_PREFER·CONDITION unit을 포함해 atomic 자체가 어려움. Llama-70B에서 atomic-all-correct 조건부로는 K2H2 composition-specific failure(15%)가 K2H1(22%)보다 낮음 | anchor-unit 짝 설계 (Stage I-2) |
| "질문이 여러 개라 어렵다"와 구분 안 됨 | conflict 없는 통제군이 없음. 2608.12426의 독립 실패 null model을 이기지 못하면 간섭 주장 불가 | no-conflict 통제군 (I-1), 독립 null 검정 (J-1) |
| composite query가 번호 목록, memory가 source 라벨 달린 JSON | batch QA·라벨 읽기라는 비판. VERIFY_PREFER가 `source` 필드 읽기로 환원 | 대화형 context (I-3), goal-framed query (I-4) |
| 강한 모델 결과 없음 | 8B~70B open model만. frontier에서 사라지면 동기 붕괴 | frontier gate (J-0)를 가장 먼저 |

주장을 다음 순서로 세운다. 앞 단계가 실패하면 뒤를 하지 않는다.

```text
J-0  frontier 모델에서도 gap이 남는가                  → 아니오: 주제 재고
J-1  composite 실패가 독립 누적보다 큰가                → 아니오: benchmark/분석 논문으로 축소
J-2  conflict가 있을 때만 떨어지는가                    → 아니오: multi-question 현상으로 보고
J-3  짝 unit의 policy가 바뀌면 같은 unit이 틀리는가     → 아니오: H를 분석 축으로만 유지
J-4  틀린 값이 옆 unit의 policy로 설명되는가            → 예: policy leakage가 main claim
Pilot 3  gold-free resolver가 gap을 닫는가              → 방법 기여 ([파일럿 3 계획](../pilot3_cmcr/plan.md))
```

---

## 1. 주장과 가설

### 1.1 Main claim 후보

> LLM은 memory conflict를 하나씩은 해결하지만, 서로 다른 resolution policy가 필요한 conflict가 한 요청에 섞이면 합성에서 실패한다. 이 실패는 독립 실패의 누적보다 크고, 한 unit의 policy가 다른 unit에 유출되는 형태로 나타나며, unit별 policy를 분리해 적용하면 완화된다.

### 1.2 가설

- **H-A (interference beyond independence):** composite all-unit success < Π(unit별 atomic success). composite 안의 unit별 정확도 < 같은 unit의 atomic 정확도.
- **H-B (conflict-specific):** conflict 없는 K개 질문에서는 H-A의 gap이 없거나 작다.
- **H-C (heterogeneity):** 같은 anchor unit이 same-policy 짝과 있을 때보다 different-policy 짝과 있을 때 더 자주 틀린다.
- **H-D (policy leakage):** heterogeneous composite의 오답은 옆 unit의 policy가 골랐을 값과 일치하는 비율이 homogeneous보다 높다.
- **H-E (cross-unit order):** unit A의 evidence 순서만 바꿔도 unit B의 답이 바뀐다.
- **H-F (global-policy collapse):** 전역 policy prompt(항상 latest / 항상 caution)는 한 유형을 올리고 다른 유형을 내린다.

### 1.3 주장하지 않는 것

- 자연 발생 prevalence
- H가 1 늘 때마다 단조 감소
- 세 유형이 memory conflict의 완전한 taxonomy

---

## 2. Stage I: 데이터 보강

모든 layer는 MemConflict `Data/Step4_4.jsonl`(revision `ec51d5d3`)에서 source-grounded로 만든다. 새 사실·timestamp·conflict relation을 발명하지 않는다. Stage G의 `prepare_pilot2_stage_g.py`를 확장하며, 기존 150 base와 instance ID 체계를 유지한다.

### I-1. No-conflict 통제군 `K2_C0`, `K3_C0`

**목적:** H-B. conflict 없이 질문 수만 같은 조건.

**재료:** 각 persona의 `Fixed_Profile`(Birthdate, Birthplace, Education 등)과 session의 `Revealed_Attributes` 중 이후 어떤 session에서도 conflict record(Static/Conditional/Dynamic 정보)가 붙지 않은 attribute. 조건: 해당 attribute가 `Full_Session_Chain`에서 정확히 한 번 공개되고, 같은 attribute path에 대한 conflict ID가 없음.

**구성:**

| 항목 | 값 |
|---|---|
| cell | `K2_C0` 30, `K3_C0` 30 |
| unit | 위 조건의 attribute를 K개, 같은 persona |
| query 형식 | Stage G와 동일 목록 형식. "As of {date}: {question}" |
| memory record | attribute당 record 1개 + **filler record**로 record 수를 짝지은 conflict cell의 중앙값(K=2: 5, K=3: 9)에 맞춤 |
| filler | 같은 persona의 다른 무관 attribute의 단일 record. conflict 없는 것만 |
| order variant | original / reverse / interleaved |
| atomic probe | unit별 1개 (K2: 60, K3: 90) |

**검증:** filler가 unit attribute와 같은 path가 아님, 각 unit의 gold가 record 하나로 결정됨, token 길이가 짝 cell의 ±15% 이내.

### I-2. Anchor-unit 짝 설계

**목적:** H-C. policy identity confound 제거.

**설계:** anchor unit `a`(policy P) 하나에 대해 두 composite를 만든다.

```text
same-policy 짝:      a + b        b.policy == P
different-policy 짝: a + c        c.policy != P
```

`b`와 `c`는 같은 persona에서 고르고 record 수 차이 1 이하, token 길이 차이 10% 이하로 맞춘다. 가능하면 `c`의 policy를 나머지 두 policy에 균등 배분한다.

| 항목 | 값 |
|---|---|
| anchor 수 | 60 (policy당 20) |
| composite | 120 (anchor당 2), 모두 K=2 |
| order variant | 3 |
| atomic probe | anchor 60 + partner 최대 120 (중복 제거) |
| 확장 (선택) | K=3: `a+b+b'` vs `a+c+c'` 30 anchor, 60 composite |

**분석 단위:** anchor. 같은 anchor의 두 조건을 paired로 비교하므로 unit 난이도가 상쇄된다.

**제외 규칙:** anchor의 atomic probe가 세 생성 모델 중 둘 이상에서 틀리면 anchor에서 제외하고 대체한다. 단독으로 못 푸는 unit은 간섭 측정에 쓸 수 없다.

### I-3. 대화형 context (`ctx=dialogue`)

**목적:** source 라벨 제거. `source: verified_profile_record` 같은 필드가 policy를 직접 알려주는 문제 해소.

**방법:** Stage G 150 base의 각 memory record를 `Session_Dialogue`에서 해당 값을 언급한 turn으로 치환한다.

1. record의 `memory_id`가 가리키는 session과 attribute를 찾는다.
2. 그 session의 `Session_Dialogue` turn 중 값 문자열(또는 그 일부)을 포함하는 user turn을 찾는다.
3. record를 `{date, speaker: "user", text: <turn>}`로 재작성한다. `source` 필드는 제거한다.
4. 값이 turn에서 찾아지지 않는 record(예: `Others_Dynamic_Information`으로만 등장)는 원 대화의 인접 turn을 사용하고, 그것도 없으면 해당 base를 `ctx=dialogue` subset에서 제외한다. 억지로 paraphrase하지 않는다.

**산출:** 대화형으로 변환 가능한 base의 수와 cell 분포를 기록한다. 목표 120/150 이상. 미달이면 cell당 최소 20으로 축소한다.

**주의:** static conflict의 "other_person_statement"는 대화상 "내 이웃이 말하길 …" 형태가 되므로 owner 정보가 문장에 남는다. 이것은 현실적이며 제거하지 않는다. 제거하는 것은 record 수준 메타 라벨뿐이다.

### I-4. Goal-framed 자연 query subset

**목적:** 번호 목록이 아니라 하나의 사용자 목표로 K unit을 요구하는 형식. batch QA 비판 대응.

**방법:** Stage G에서 cell당 10 base(Stage H 선택분 50 base 재사용)를 대상으로, 같은 unit·같은 gold를 요구하는 단일 goal query를 작성한다.

예: `K3_H3` (Career_Status SUPERSEDE, Birthdate VERIFY_PREFER, puzzle game CONDITION)
- 목록형: "1. As of 2023-01-06: How did the user's career situation change? 2. …"
- goal형: "I'm filling in a profile form for a mentoring program dated 2024-07-21. It asks for my current job and how it changed from before, my date of birth, and when I'd normally reach for a puzzle game. Draft the three answers from what you remember about me."

**규칙:**
- unit deletion test: 어느 한 unit을 지우면 query를 완성할 수 없어야 한다.
- gold 노출 금지: query가 답이나 조건을 직접 말하지 않는다.
- 날짜는 unit별 target date 중 가장 늦은 것으로 통일하되, 모든 unit의 gold가 그 날짜에도 유효한 base만 사용한다. 유효하지 않으면 base를 교체한다.
- 작성: 연구자 초안 → Codex 검토 → 두 형식의 unit·gold 동일성 자동 검증.

**산출:** 50 base × 2 형식(list / goal) × 3 order.

### I-5. Cross-unit order variant

**목적:** H-E.

**설계:** K=2 base(Stage G `K2_*` 60 + I-2 120 = 180)에 대해 unit block 위치는 고정(A block 다음 B block)하고 block 내부 순서만 바꾼다.

| variant | A 내부 | B 내부 |
|---|---|---|
| oo | original | original |
| ro | reverse | original |
| or | original | reverse |
| rr | reverse | reverse |

`oo`는 Stage G `original`과 동일하므로 재실행하지 않는다. 추가로 block 자체를 바꾼 `swap`(B block 다음 A block, 내부 original) 1개를 둔다. base당 신규 4 variant.

### I-6. Policy-leakage 채점용 대안값 표

**목적:** H-D를 결정론적으로 채점.

각 unit에 대해 record별 값에 "어느 policy가 골랐을 값인지"를 라벨링한다.

| unit policy | gold 값 | 대안값과 라벨 |
|---|---|---|
| SUPERSEDE | update 값 | prior 값 → `stale_kept` (VERIFY_PREFER식 "안정된 옛 값 유지"로 오해) |
| VERIFY_PREFER | verified 값 | 나중 false 값 → `latest_applied` (SUPERSEDE 유출), other_person 값 → `wrong_owner` |
| CONDITION | query 조건의 item | 다른 조건 item → `wrong_condition`, 가장 최근 언급 item → `latest_applied` (SUPERSEDE 유출), 여러 item 나열 → `over_preserved` |

이 표는 Stage G gold_units와 memory_context에서 자동 생성한다. 채점은 candidate final answer에서 unit별 값을 추출(judge가 이미 unit별 판정을 내므로 판정 출력에 `extracted_value` 필드 추가)한 뒤 표와 문자열·의미 매칭한다.

### I-7. 규모 요약

| layer | base | order/variant | composite trial | atomic probe |
|---|---|---|---|---|
| Stage G (기존) | 150 | 3 | 450 | 390 |
| I-1 C0 | 60 | 3 | 180 | 150 |
| I-2 anchor | 120 | 3 | 360 | ≤180 |
| I-3 dialogue | ≤150 | 3 | ≤450 | ≤390 |
| I-4 goal | 50 | 3 (goal형만 신규) | 150 | 0 |
| I-5 cross-order | 180 | 4 신규 | 720 | 0 |
| 합계 신규 | | | ≤1,860 | ≤720 |

생성 모델 3개 기준 신규 생성 약 7,700회, judge 동수. H100 1장 vLLM으로 Stage G(2,520회) 대비 약 3배이며 실행 가능하다.

---

## 3. Stage J: 간섭 검증 실험

### J-0. Frontier gate (가장 먼저)

- 모델: 제출 시점 기준 강한 API reasoning model 1종. 선택과 버전을 run manifest에 동결.
- 입력: Stage G 150 base × 3 order + atomic 390 = 840 call.
- 판정: evidence-aware v3, judge는 Llama-70B (self-judge 회피).
- **Go:** worst-order all-unit success < 80% **그리고** atomic-all-correct base 중 composite 실패 ≥ 10%.
- **No-go:** 위 미달. 이 경우 주제를 "작은 모델의 문제"로 한정하거나 재고한다. 나머지 Stage를 진행하지 않는다.

비용은 API 840 call이며 하루 안에 끝난다.

### J-1. 독립 null 검정 (H-A)

- 데이터: Stage G 150 base + I-3 dialogue.
- 지표 1: **composite 안의 unit별 정확도** vs 같은 unit의 atomic 정확도. base·unit paired McNemar. 이것이 primary다.
- 지표 2: composite all-unit success vs atomic-all-correct 비율. 후자가 독립 null의 상한이다.
- 지표 3: composition-specific failure(기존).
- 보고: 2608.12426 식으로 "개별 통과율의 곱 대비 관측치" 그래프를 cell별로.

judge 출력에 unit별 판정이 이미 있으므로 추가 생성 없이 계산 가능하다. Stage G 데이터로 지금 당장 계산할 수 있는 항목이며, I-1 이전에 먼저 계산한다.

### J-2. Conflict-specific 검정 (H-B)

- `K2_C0` vs `K2_H1`, `K2_H2`; `K3_C0` vs `K3_H1`, `K3_H2`, `K3_H3`.
- 지표: J-1의 unit-level gap(atomic − in-composite)을 cell별로 비교. C0의 gap이 0에 가깝고 conflict cell의 gap이 유의하게 크면 통과.
- 길이 통제: C0의 token 길이를 conflict cell과 맞췄으므로 길이 설명은 배제된다.

### J-3. Anchor 짝 검정 (H-C)

- anchor별로 same-policy 짝에서의 anchor 정확도 vs different-policy 짝에서의 anchor 정확도. paired McNemar, anchor policy별 층화.
- worst-order 기준과 order별 기준을 둘 다 보고.
- 통과: 세 생성 모델 중 둘 이상에서 different-policy 조건의 anchor 정확도가 유의하게 낮음. 유의하지 않으면 H는 분석 축으로만 남긴다.

### J-4. Policy-leakage 혼동행렬 (H-D)

- I-6 표로 모든 오답을 `stale_kept / latest_applied / wrong_owner / wrong_condition / over_preserved / omission / other`로 자동 분류.
- 행렬: intended policy × applied label. homogeneous vs heterogeneous cell 비교.
- 핵심 검정: heterogeneous composite에서 `latest_applied` 비율(VERIFY_PREFER·CONDITION unit이 SUPERSEDE처럼 처리됨)이 homogeneous 대비 높은가. 그리고 SUPERSEDE unit이 VERIFY_PREFER 옆에 있을 때 `stale_kept`가 늘어나는가.
- 통과 시 이것이 논문의 Figure 1이다.

### J-5. Cross-unit order (H-E)

- I-5 variant로 K=2 base 180개.
- 지표: A 내부 순서만 바꿨을 때(`oo`→`ro`) **A 답은 그대로인데 B 답이 바뀐** base 비율. 반대 방향(`oo`→`or`)도.
- baseline: 단일 conflict 순서 flip(2605.14115: 11~25%). cross-unit flip이 0과 유의하게 다르면 통과.
- `swap`으로 block 위치 효과를 별도 보고.

### J-6. 형식·context 재현

- I-3 dialogue context에서 J-1, J-4 재계산. structured와 dialogue의 gap 차이를 보고. VERIFY_PREFER 정확도가 dialogue에서 크게 떨어지면 structured 결과의 일부가 라벨 읽기였다는 뜻이므로 dialogue를 main으로 승격한다.
- I-4 goal형 vs list형 50 base. all-unit success와 omission rate 비교. goal형이 더 나쁘면 goal형 결과를 main text에, list형을 appendix에.

### J-7. Global-policy prompt baseline (H-F)

- prompt 2종: `always_latest`("가장 최근 기록을 항상 우선하라"), `always_cautious`("불일치가 있으면 확정하지 말고 모든 가능성을 남겨라").
- Stage G 150 base × original order × 2 prompt.
- 기대: `always_latest`는 SUPERSEDE unit ↑, VERIFY_PREFER·CONDITION ↓. `always_cautious`는 반대. MemSyco-Bench와 같은 trade-off 재현.
- 이 결과가 "unit별 policy가 필요하다"는 방법 동기다.

### J-8. 인간 검증

- 층화 표본 200 trial: cell 5 × 정답/오답 × judge 불일치 여부. dialogue subset 포함.
- 주석자 2명, unit별 정답 여부와 leakage 라벨. Cohen's κ 보고. κ < 0.6이면 rubric 수정 후 재주석.
- judge와 인간의 일치율을 cell별로 보고하고 composite κ 0.435 문제를 해소한다.

### J-9. 모델

| 역할 | 모델 |
|---|---|
| frontier gate | API reasoning model 1종 (J-0) |
| 주력 open | Qwen3-8B, Mistral-Small-3.2-24B, Llama-3.1-70B-AWQ (Stage G와 동일) |
| judge | 생성 모델과 교차. API 모델 출력은 Llama-70B가 판정 |
| 추가 (선택) | reasoning mode 켠 Qwen3-8B 1회. "reasoning이 줄이지만 없애지 못한다" 확인 |

설정은 Stage G와 동일: temperature 0, seed 고정, max tokens 900, thinking off(선택 실험 제외).

---

## 4. 중단·축소 기준

| 상황 | 결정 |
|---|---|
| J-0 no-go | 주제 재고. 작은 모델 한정 주장은 하지 않음 |
| J-1 gap 없음 | 간섭 주장 철회. MemConflict 시스템별 anti-correlation을 근거로 "composition은 가장 약한 policy에 의해 결정된다"는 benchmark·분석 논문으로 축소 |
| J-2에서 C0도 같은 gap | multi-question 현상으로 보고. memory 논문이 아님 |
| J-3, J-4 모두 실패 | H를 분석 축으로 강등. main claim은 atomic-to-composite gap과 cross-unit order effect |
| 파일럿 3에서 CAR-style과 동등 | method 기여 제거 |
| 유사 논문 공개 (CAR 후속, IBA-Bench 확장) | 차별점을 leakage 분석과 dialogue context로 좁힘 |

---

## 5. 일정 (2026-10 ARR 기준 약 7주)

| 주 | 작업 | 산출 |
|---|---|---|
| 1 (8/31~) | J-1 기존 데이터 재계산, I-1·I-2 생성기, J-0 API 실행 | go/no-go |
| 2 | I-1·I-2·I-5 세 모델 실행과 판정, J-2·J-3·J-5 분석 | 간섭 여부 확정 |
| 3 | I-3·I-4·I-6 구축, J-4·J-6·J-7 실행, J-8 인간 검증 시작 | Figure 1 후보 |
| 4 | 파일럿 3 CMCR-Linear 구현, 비교군 실행 | method 결과 |
| 5 | 파일럿 3 ablation, K3_H≥2 분석, J-8 완료 | |
| 6 | 외부 전이 (선택), 통계 정리, 표·그림 | |
| 7 | 집필, 내부 리뷰 | 제출 |

3주차 말에 4절 기준으로 논문 유형(method vs benchmark·분석)을 확정한다.

---

## 6. 산출물 위치

파일럿 2 폴더 아래에 stage 단위로 둔다.

```text
data/pilot2_memory/
├── stage_i_controls/          I-1 C0 cells, atomic probes, filler manifest
├── stage_i_anchor/            I-2 anchor pairs, matching covariates
├── stage_i_dialogue/          I-3 dialogue-form contexts, conversion log
├── stage_i_goal/              I-4 goal-framed queries, deletion-test log
├── stage_i_cross_order/       I-5 variants
└── stage_i_leakage_tables.jsonl   I-6

results/pilot2_memory/
├── stage_j_frontier/          J-0
├── stage_j_independence/      J-1
├── stage_j_controls/          J-2
├── stage_j_anchor/            J-3
├── stage_j_leakage/           J-4
├── stage_j_cross_order/       J-5
├── stage_j_format/            J-6
├── stage_j_global_policy/     J-7
├── stage_j_human/             J-8
└── stage_j_run_manifest.yaml

src/composite_conflict/
├── prepare_pilot2_stage_i_controls.py
├── prepare_pilot2_stage_i_anchor.py
├── prepare_pilot2_stage_i_dialogue.py
├── prepare_pilot2_stage_i_cross_order.py
├── build_pilot2_leakage_tables.py
├── analyze_pilot2_stage_j_independence.py
└── analyze_pilot2_stage_j_leakage.py
```

---

## 7. 체크리스트

### Stage I

- [x] I-1 no-conflict attribute 추출 규칙 구현, persona별 후보 수 기록 (dynamic 속성의 첫 update 이전 단일 record 166건. static·conditional에는 단일 record ID가 없음)
- [x] I-1 `K2_C0`, `K3_C0` 각 30 + filler 길이 맞춤 검증 (record 5/8 정확히 일치). 첫 판정에서 gold가 record 전체 dict라 정답을 incomplete로 처리하는 문제가 있어 gold를 질문이 묻는 필드로 한정(입력 불변, 재판정만 수행)
- [x] I-2 anchor 60 선정, same/different 짝 120, covariate 표 (`data/pilot2_memory/stage_i_anchor/matching_covariates.jsonl`)
- [ ] I-3 dialogue 변환률 기록, 미변환 base 제외 목록 (미구축)
- [ ] I-4 goal query 50 작성, unit deletion test, gold 동일성 검증 (미구축)
- [ ] I-5 cross-order variant 720 생성 (미구축)
- [x] I-6 leakage 대안값 표: `analyze_pilot2_stage_j_leakage.py`가 record에서 자동 생성 (토큰 겹침 매칭). 수동 확인은 J-8과 함께
- [x] validation.json과 run manifest 동결 (`results/pilot2_memory/stage_j_run_manifest.yaml`)

### Stage J

- [x] judge protocol v4 `v4_unit_isolated` 추가: unit별 격리 판정과 `extracted_answer`. v3 판정에서 다른 unit의 오류가 이 unit 판정에 섞이는 사례가 확인돼 도입. v3 파일은 보존하고 v4로 Stage G·I 전량 재판정
- [x] 실행기 throttle 수정: 로컬 vLLM 실행은 직렬화하지 않음 (`--api-key-env` 또는 cooldown>0일 때만 throttle)

- [x] J-1 Stage G 기존 판정으로 unit-level gap 즉시 계산 ([stage_j_result.md](stage_j_result.md))
- [ ] J-0 API 모델 840 call, go/no-go 기록 (API 키 없음. 대신 Qwen3-32B thinking on/off로 크기·reasoning 효과 확인)
- [x] J-2~J-4 네 모델(Qwen3-8B/32B, Mistral-24B, Llama-70B) 실행, judge 교차(v4), 분석. J-5 cross-unit order는 미생성·미실행 ([stage_j_result.md](stage_j_result.md))
- [ ] J-6 dialogue·goal 재현 (I-3·I-4 미구축)
- [ ] J-7 global-policy prompt 2종 (미실행)
- [~] J-8: 인간 주석 대신 독립 LLM(Claude) blind 주석 168 trial/420 unit 완료. 기계 v4와 κ 0.82, 불일치 29건은 `stage_j_human/claude_vs_machine/disagreements.jsonl`. 인간은 이 29건만 adjudicate하면 됨. 통제군 LOOKUP에서 기계가 과도하게 엄격함을 확인 → `v4_lookup_lenient`로 통제군 재판정(주석 일치 0.77→0.90), J-2 재계산 후에도 excess ≈ 0
- [x] 4절 기준으로 논문 유형 결정: H-B·H-C 기각 → 간섭·이질성 주장 철회. order robustness 방법 또는 benchmark·분석 논문으로 전환 제안 ([stage_j_result.md 결론](stage_j_result.md))

파일럿 3 체크리스트는 [파일럿 3 계획](../pilot3_cmcr/plan.md)에 있다.
