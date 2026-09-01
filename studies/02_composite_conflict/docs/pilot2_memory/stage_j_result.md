# Stage J 결과: 간섭 검증 (진행 중)

> 실행일: 2026-08-28
> 상태: J-1~J-4 완료(생성 모델 4종). J-8은 인간 대신 독립 LLM(Claude) blind 주석 420 unit으로 대체 수행(κ 0.82). J-5~J-7 미실행, J-0 frontier gate는 API 키 확보 후
> 계획: [stage_ij_plan.md](stage_ij_plan.md)
> 산출물: `results/pilot2_memory/stage_j_independence/`

## J-1. Unit-level gap과 독립 null

새 생성 없이 Stage G의 evidence-aware v3 판정을 unit 단위로 재결합했다. 통계 단위는 (base, unit)이며, composite 판정은 세 evidence order 모두 정답이어야 하는 worst-order와 order별 값을 함께 본다. 검정은 discordant pair에 대한 exact McNemar, 구간은 base cluster bootstrap 2,000회다.

### 결과 요약 (worst-order)

| 생성 / 판정 | n unit | atomic | in-composite | gap | atomic 정답 중 composite에서도 정답 | p |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-8B / Llama-70B | 390 | 0.844 | 0.326 | +0.518 [0.46, 0.58] | 0.371 | <1e-6 |
| Llama-70B / Qwen3-8B | 390 | 0.772 | 0.533 | +0.238 [0.18, 0.30] | 0.654 | <1e-6 |
| Mistral-24B / Llama-70B | 390 | 0.787 | 0.420 | +0.367 [0.30, 0.43] | 0.482 | <1e-6 |
| Mistral-24B / Qwen3-8B | 390 | 0.713 | 0.477 | +0.236 [0.18, 0.29] | 0.629 | <1e-6 |

order별로 보면 gap은 Qwen +0.28~0.36, Mistral +0.10~0.23, Llama +0.07~0.16으로 줄지만 모든 order에서 양수다. worst-order의 엄격함만으로 설명되지 않는다.

### 독립 null

base 단위로 "모든 atomic이 정답"인 비율이 독립 실패 가정의 상한이다. 관측 worst-order all-unit success는 모든 조합에서 그 상한보다 낮다.

| 생성 / 판정 | 상한(all atomic ok) | 관측 worst-order | 관측 best-order | all atomic ok인 base 중 세 order 모두 성공 |
|---|---:|---:|---:|---:|
| Qwen / Llama | 0.680 | 0.160 | 0.447 | 22/102 |
| Llama / Qwen | 0.507 | 0.373 | 0.633 | 50/76 |
| Mistral / Llama | 0.520 | 0.233 | 0.573 | 25/78 |
| Mistral / Qwen | 0.433 | 0.353 | 0.567 | 47/65 |

### Policy별: 어느 unit이 composite에서 무너지는가

worst-order 기준, 같은 policy의 unit을 homogeneous 짝과 heterogeneous 짝으로 나눴다.

| 생성 / 판정 | policy | atomic | in-composite (hom) | in-composite (het) |
|---|---|---:|---:|---:|
| Qwen / Llama | SUPERSEDE | 0.98 | 0.52 | 0.34 |
| Llama / Qwen | SUPERSEDE | 1.00 | **0.88** | **0.49** |
| Mistral / Llama | SUPERSEDE | 0.99 | 0.38 | 0.34 |
| Mistral / Qwen | SUPERSEDE | 1.00 | **0.90** | **0.35** |
| Llama / Qwen | CONDITION | 0.97 | 0.88 | 0.85 |
| Mistral / Qwen | CONDITION | 0.92 | 0.94 | 0.69 |
| 전체 | VERIFY_PREFER | 0.22~0.64 | 0.00~0.12 | 0.08~0.28 |

세 모델에서 atomic 정확도가 거의 1.0인 **SUPERSEDE unit이 heterogeneous 짝에서 크게 무너진다**(Llama 0.88→0.49, Mistral/Qwen-judge 0.90→0.35). 같은 policy·같은 pool에서 뽑힌 unit이므로 policy identity로는 설명되지 않고, 짝 unit의 policy가 다를 때 생기는 효과다. 이것이 J-3 anchor 짝 설계와 J-4 policy leakage 분석의 직접 동기다. VERIFY_PREFER는 atomic 자체가 낮아 composite 수치가 정보를 주지 못한다.

### 해석과 한계

- 지지: unit이 단독으로 풀리더라도 composite에서 실패하며, 실패는 독립 누적 상한보다 크다. 세 생성 모델·두 judge에서 방향이 같다.
- 한계: judge κ가 composite에서 0.435이므로 절대값은 탐색 수치다. 통제군(J-2) 없이는 "질문 수" 효과와 분리되지 않는다. heterogeneous 효과는 아직 anchor 짝(J-3)으로 확인되지 않았다.

## J-4. Policy leakage (v3 판정 기준, 예비)

각 unit의 memory record에서 대안값을 뽑고 "어느 policy가 골랐을 값인지" 라벨을 붙인 뒤(SUPERSEDE의 prior → `stale_kept`, VERIFY_PREFER의 나중 거짓 값 → `latest_applied`, 타인 값 → `wrong_owner`, CONDITION의 다른 조건 → `wrong_condition`), 오답 판정 unit의 답에 어떤 값이 들어갔는지 문자열로 귀인했다. gold 비교는 gold 답 문장이 아니라 gold record 값으로 한다(gold 답 문장에는 "X에서 Y로" 식으로 대안값도 언급되기 때문).

| 생성 / 판정 | unit policy | 오답 trial | latest_applied | stale_kept | wrong_condition | gold 값 포함인데 오답 | 미귀인 |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen / Llama | VERIFY_PREFER | 306 | 0.27 | - | - | 0.26 | 0.42 |
| Llama / Qwen | VERIFY_PREFER | 284 | 0.12 | - | - | 0.43 | 0.42 |
| Mistral / Llama | VERIFY_PREFER | 237 | 0.21 | - | - | 0.30 | 0.46 |
| Qwen / Llama | SUPERSEDE | 161 | - | 0.07 | - | 0.90 | 0.03 |
| Llama / Qwen | SUPERSEDE | 86 | - | 0.01 | - | 0.44 | 0.55 |
| Qwen / Llama | CONDITION | 99 | - | - | 0.33 | 0.11 | 0.55 |

관찰:

1. VERIFY_PREFER 오답의 12~27%는 실제로 "나중의 거짓 값"을 답으로 낸 `latest_applied`다. 다만 이 비율은 heterogeneous보다 **homogeneous**(VERIFY_PREFER끼리) 짝에서 더 높거나 비슷했다(Llama 0.17 vs 0.08, Mistral 0.30 vs 0.13). SUPERSEDE unit이 옆에 있어서 유출된다는 단순 가설은 이 수치로는 지지되지 않는다.
2. SUPERSEDE 오답의 대부분은 gold 값을 답에 포함하고 있다(Qwen 90%). 즉 값을 틀린 것이 아니라 "physical health는 그대로였다"처럼 gold 답의 세부를 빠뜨렸거나, judge가 다른 unit의 오류를 이 unit에 전가했다.
3. 오답 샘플을 직접 보면 judge 오류가 확인된다: "2022-05-05에 바뀌었는데 target date 2022-05-05 이후라서 오답"(모순), CONDITION 정답인데 답에 적힌 날짜가 target date와 달라 오답, 아이 상태 unit이 **같은 답의 성별 서술이 틀렸다는 이유로** 오답. 마지막 유형은 정확히 "atomic 정답, composite 오답" artifact를 만든다.

따라서 v3 판정으로 계산한 J-1 gap의 일부는 judge의 unit 혼동일 수 있다. 이를 분리하기 위해 judge protocol v4(`v4_unit_isolated`)를 도입했다: unit별로 답 구간을 먼저 추출(`extracted_answer`)하고 다른 unit 내용은 판정에 쓰지 말라고 명시하며, 날짜 표기 차이·설명 누락을 벌점하지 않는다. Stage G 전량과 Stage I를 v4로 재판정해 v3와 비교한다. v3 파일은 보존한다.

## 판정 protocol v4와 실행 메모

- v4 `v4_unit_isolated`: unit별 `extracted_answer`를 먼저 뽑고 다른 unit 내용은 판정에 쓰지 않는다. 날짜 표기 차이·설명 누락은 벌점하지 않는다.
- Llama-70B judge가 2-unit instance에서 결과를 1개만 돌려주는 경우(약 6%)가 있어, 개수 불일치 시 재시도 후 unit별 개별 호출로 fallback하도록 judge를 수정했다.
- 실행기의 직렬화 throttle을 로컬 vLLM에서는 해제했다(16 동시). 생성 오류는 Qwen 통제군 1건(JSON 잘림, omission으로 분모 유지), 나머지 0.
- I-1 gold는 첫 판정 후 "질문이 묻는 필드"로 한정했다. record 전체 dict를 gold로 두면 소득·배우자 생일까지 요구해 정답을 incomplete로 처리했기 때문이다. 입력은 불변이라 생성 출력은 재사용하고 판정만 다시 했다.

## J-2. No-conflict 통제군 (Qwen3-8B 생성, Llama-70B v4 judge)

| cell | n unit | atomic | in-composite (worst) | gap (worst) | gap (order별) | 상한(all atomic ok) | 관측 worst / best |
|---|---:|---:|---:|---:|---|---:|---:|
| K2_C0 | 60 | 0.967 | 0.700 | +0.267 [0.15, 0.38] | +0.15 / +0.22 / +0.11 | 0.933 | 0.433 / 0.867 |
| K3_C0 | 90 | 0.978 | 0.667 | +0.311 [0.21, 0.43] | | 0.933 | 0.333 / 0.800 |

**conflict가 없어도 Qwen3-8B는 유의한 gap을 보인다.** 오답 83 unit 중 타인 record 값 혼입(owner contamination) 13, 미응답 8, 나머지는 judge 엄격성("Free → 무직으로 해석"을 오답 처리)과 실제 누락("Status: No"를 "정보 없음"으로 답함)이 섞여 있다. conflict cell과의 공정 비교(둘 다 v4 judge, `results/pilot2_memory/stage_j_controls/excess/`):

| 비교 | gap conflict | gap control | excess (worst) | CI95 | excess original / reverse / interleaved |
|---|---:|---:|---:|---|---|
| K2 conflict 전체 vs K2_C0 | +0.350 | +0.267 | +0.083 | [−0.07, +0.23] | +0.11 / +0.04 / +0.07 |
| K3 conflict 전체 vs K3_C0 | +0.367 | +0.311 | +0.056 | [−0.08, +0.19] | +0.09 / −0.07 / +0.13 |
| K2_H2 vs K2_H1 | +0.333 | +0.367 | −0.033 | [−0.22, +0.15] | |
| K3_H3 vs K3_H1 | +0.289 | +0.433 | −0.144 | [−0.32, +0.03] | |

**Qwen3-8B에서 conflict 고유의 초과 gap은 작고 유의하지 않다.** policy 이질성(H)은 gap을 줄이는 방향이다. v4로 다시 본 Stage G 전체 gap은 worst +0.36(v3 +0.52), order별 +0.20~0.24(v3 +0.28~0.36)였다. v3→v4 교체로 composite unit 168건이 오답→정답, 34건이 정답→오답으로 바뀌었다(κ 0.65). v3가 composite에 과도하게 엄격했다는 뜻이다.

v4에서 policy별 gap: VERIFY_PREFER +0.53(atomic 0.59 → composite 0.06), CONDITION +0.39, SUPERSEDE +0.16. SUPERSEDE의 heterogeneous 짝 gap(+0.11)이 homogeneous(+0.24)보다 작아, v3에서 본 "SUPERSEDE가 heterogeneous에서 무너진다"는 v3 judge artifact였다.

## J-3. Anchor 짝 (Qwen3-8B 생성, Llama-70B v4 judge)

같은 anchor unit을 same-policy 짝과 different-policy 짝에 넣었다. 60 anchor(policy당 20), atomic 정답 anchor 57.

| subset | pairs | anchor atomic | SAME (worst) | DIFF (worst) | p | SAME (best) | DIFF (best) | p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.95 | 0.53 | 0.57 | 0.63 | 0.80 | 0.82 | 1.0 |
| SUPERSEDE | 20 | 1.00 | 0.75 | 0.70 | 1.0 | 1.00 | 0.85 | 0.25 |
| VERIFY_PREFER | 20 | 0.85 | 0.05 | 0.10 | 1.0 | 0.45 | 0.65 | 0.22 |
| CONDITION | 20 | 1.00 | 0.80 | 0.90 | 0.5 | 0.95 | 0.95 | 1.0 |

**Qwen3-8B에서는 짝 unit의 policy가 같든 다르든 anchor 정확도가 같다.** order별로도 same 0.62~0.72 vs diff 0.68~0.73으로 차이가 없다. 즉 J-1의 policy별 표에서 본 "SUPERSEDE unit이 heterogeneous 짝에서 무너진다"는 현상은 짝 policy 때문이 아니라 표본 구성(heterogeneous cell의 다른 특성) 때문일 가능성이 크다. H-C는 Qwen에서 기각 방향이며 Mistral·Llama 복제 결과를 기다린다.

반면 atomic 0.95 → composite worst 0.55, best 0.81의 gap은 짝 policy와 무관하게 존재한다. 특히 VERIFY_PREFER anchor는 단독 0.85인데 composite에서는 0.05~0.10(worst)까지 떨어진다. 즉 "다른 unit이 있으면 verified value 대신 다른 값을 고른다"는 현상은 partner의 종류가 아니라 **partner의 존재** 자체와 연결된다.

## Mistral-24B 복제 (Llama-70B v4 judge)

- J-2 통제군: atomic 0.960 → composite worst 0.593, gap +0.367 [0.27, 0.46]; order별 +0.18 / +0.27 / +0.24. Qwen과 같이 conflict 없이도 큰 gap.
- J-3 anchor: SAME 0.68 vs DIFF 0.78 (worst, p=0.031, discordant 0 vs 6), best 0.85 vs 0.87. **different-policy 짝이 오히려 유리**하며, 이는 VERIFY_PREFER anchor(SAME 0.40 vs DIFF 0.65)가 만든다. 같은 VERIFY_PREFER unit 둘이 있을 때 verified value를 놓치는 경향이 Qwen J-4의 "homogeneous에서 latest_applied가 더 높다"와 일치한다.
- 두 모델에서 H-C(이질성이 anchor를 더 틀리게 함)는 기각이고, 방향은 반대다.

## Mistral-24B: J-1·J-2 (v4)

- Stage G conflict cell gap: worst +0.20 [0.15, 0.25], order별 +0.07~0.10 (v3는 +0.37 / +0.18~0.23; v3→v4 κ 0.56).
- 통제군 gap worst +0.37, order별 +0.18~0.27. **excess = 음수**: K2 −0.21 [−0.37, −0.06], K3 −0.14 [−0.29, −0.00]. K2_H2−K2_H1 = −0.12, K3_H3−K3_H1 = +0.03.

## Llama-70B 판정자 문제

Llama-70B 생성분은 self-judge를 피하려고 Qwen3-8B가 판정했다. 통제군 v4 결과가 atomic 0.63 < composite 0.77로 역전됐고, atomic 오답 샘플에서 "The user's work state was Busy"(gold: Busy)를 `wrong_temporal_state`로, "does not have children"(gold: No)를 오답으로 처리하는 등 명백한 오판이 확인됐다. **Qwen3-8B는 judge로 부적합**하며, Stage G에서 Qwen3-8B가 판정한 Llama 결과(v3·v4)도 같은 이유로 신뢰할 수 없다. Llama 생성분 전체(Stage G 840, Stage I 821)는 Qwen3-32B(thinking off) v4로 재판정한다. 이전 판정 파일은 보존한다.

Qwen3-32B로 재판정해도 Llama 통제군의 atomic 정확도는 0.67(composite order별 0.77~0.81보다 낮음)이다. 오답 49건 중 22건은 "not explicitly stated as of {target date}" 류의 hedging(다른 모델은 0~5%, Llama는 15%)이고, 나머지 27건은 값은 맞게 말하면서("work state as of 2022-01-17 was Normal") 끝에 "inconclusive"를 붙여 target date 시점의 확정을 거부한 경우다. 즉 **Llama는 record가 하나뿐이고 target date가 record 날짜보다 뒤이면 abstain에 가깝게 행동**한다. 이 행동은 atomic(단일 record)에서 더 자주 나타나 Llama의 C0 gap을 음수로 만든다. Llama에서는 atomic-composite gap 대신 composite 정확도 자체와 anchor 짝 비교를 본다.

Llama 자체의 특징 하나는 기록해 둔다: "as of 2022-02-08 is not explicitly stated, but as of 2022-01-01 the user was dating …"처럼 target date와 record 날짜가 다르면 확정을 피하는 date-strict 응답이 잦다.

## Llama-70B: J-2·J-3 (Qwen3-32B v4 judge)

- J-2 통제군: atomic 0.673, composite worst 0.640, order별 0.77~0.81. gap +0.03 [−0.09, +0.15], order별 −0.09~−0.14. 위의 abstain 행동 때문에 atomic이 낮아 gap 해석 불가. composite 정확도 자체는 세 order 모두 0.77 이상이다.
- J-3 anchor: SAME 0.62 vs DIFF 0.72 (worst, p=0.11), 0.93 vs 0.85 (best, p=0.13). order별로는 original 0.80/0.78, reverse 0.65/0.77, interleaved 0.88/0.78로 방향이 엇갈린다. **이질성 효과 없음.** CONDITION anchor 20/20 모두 두 조건에서 정답, SUPERSEDE 0.85/0.90, VERIFY_PREFER는 atomic 0.50 → composite 0.00/0.25.

세 생성 모델(8B, 24B, 70B)에서 anchor 짝 비교는 일관되게 H-C를 지지하지 않는다.

- J-1 Stage G (Qwen3-32B v4 judge): atomic 0.761, composite worst 0.644, **order별 0.77 / 0.72 / 0.79로 gap ≈ 0**(−0.01 / +0.05 / −0.03). worst-order gap +0.12 [0.07, 0.17]은 순서 민감성(base flip 시 worst 0.39 vs best 0.74)에서 온다. homogeneous gap +0.18 > heterogeneous +0.08, K2_H2 +0.02 vs K2_H1 +0.15, K3_H3 +0.08 vs K3_H1 +0.20.
- J-2 excess: K2 −0.02 [−0.21, +0.18], K3 +0.14 [−0.04, +0.33]. K3_H1(homogeneous)만 +0.21 [0.01, 0.42].
- J-4: 오답 281 unit-trial 중 VERIFY_PREFER 238(85%). VERIFY_PREFER 오답의 `latest_applied`는 homogeneous 46% vs heterogeneous 27%. SUPERSEDE 25, CONDITION 18로 적다.

**70B에서는 "atomic이 풀리면 composite도 풀린다"가 order별로 거의 성립한다.** 남는 실패는 (1) evidence order flip, (2) VERIFY_PREFER, 특히 같은 VERIFY_PREFER unit 둘이 함께 있을 때 나중 거짓 값을 채택하는 경향이다.

## VERIFY_PREFER 판정의 신뢰도

VERIFY_PREFER unit의 상당수는 "아버지/어머니가 있는가" 같은 Yes/No 질문이다(anchor set 84 trial, Stage G Qwen 72 trial). 결정론적 극성 규칙과 v4 judge를 비교하면 "극성이 gold와 같은데 judge가 오답 처리"가 anchor Llama 10/84, anchor Qwen 3/84, Stage G Qwen 4/72로 약 4~12%다. 나머지 오답은 극성이 실제로 반대(23~28/84)이거나 "conflicting information"으로 확정을 회피(12~26/84)한 경우다. 따라서 VERIFY_PREFER의 composite 붕괴는 대체로 실제 현상이며, judge 오판은 절대값을 수 %p 낮추는 정도다. 문자열 귀인에서 Yes/No 값은 잡히지 않으므로 `unattributed`에 들어간다.

## 같은 유형 unit 둘의 간섭: VERIFY_PREFER `latest_applied` (v4)

| 생성 모델 | homogeneous 짝 (VERIFY_PREFER+VERIFY_PREFER) | heterogeneous 짝 |
|---|---:|---:|
| Qwen3-8B | 0.50 (n=119) | 0.48 (n=183) |
| Mistral-24B | 0.48 (n=100) | 0.33 (n=129) |
| Llama-70B | 0.46 (n=103) | 0.27 (n=135) |

24B·70B에서는 같은 VERIFY_PREFER unit이 둘 있을 때 "나중의 거짓 값"을 답으로 내는 비율이 heterogeneous보다 15~19%p 높다. H 가설과 반대로, **같은 유형의 conflict가 여럿이면 하나의 규칙(recency)을 전체에 적용하는 경향**이 강해진다. 이는 global-policy collapse의 한 형태이지만 정책 이질성이 아니라 정책 동질성에서 나타난다.

## 오답 귀인으로 본 공통 메커니즘 (v4, 토큰 겹침 매칭)

| 조건 | unit | 오답 trial | 주된 귀인 |
|---|---|---:|---|
| 통제군 LOOKUP | Qwen / Mistral | 83 / 122 | **타인 record 혼입** 35% / 53% (이웃·친구의 직장·근무 상태를 사용자 것으로 답함), gold 포함인데 오답 39% / 16% |
| conflict VERIFY_PREFER | Qwen / Mistral | 302 / 229 | **나중의 거짓 값 채택** 49% / 39%, 타인 값 6% / 3% |
| conflict CONDITION | Qwen / Mistral | 79 / 45 | **다른 조건의 item** 76% / 27%, 타인 값 13% / 4% |
| conflict SUPERSEDE | Qwen / Mistral | 51 / 49 | gold 값 포함(세부 누락 또는 judge 엄격) 94% / 96% |

통제군 attribute별로는 Career_Status(worst gap +0.52 / +0.45)와 Work_Status(+0.48 / +0.52)가 gap을 만들고, 단일 필드 Residence·Marital·Health는 +0.15~0.35다. 타인 record(`Others_Dynamic_Information`)가 같은 attribute로 붙는 것이 통제군의 주된 실패 원인이다.

### 잠정 해석 (Qwen3-8B, Mistral-24B 기준)

1. atomic-to-composite gap은 conflict 유무와 무관하게 존재하고, 통제군이 conflict cell보다 작지 않다. **H-B 미지지.**
2. anchor 짝에서 policy 이질성 효과는 없거나 반대 방향이다. **H-C 기각.** Mistral·Qwen 모두 같은 VERIFY_PREFER unit이 둘 있을 때 recency를 더 자주 적용한다.
3. 세 조건의 오답은 공통적으로 **slot에 잘못된 record를 묶는 실패**다: 다른 소유자의 record, 같은 attribute의 나중 거짓 record, 조건이 다른 preference record. 짝 unit의 policy 종류가 아니라 **동일 attribute 후보 record가 여러 개 있고 slot이 여러 개**라는 사실이 실패를 만든다.
4. 따라서 "heterogeneous policy composition"이 아니라 **multi-slot evidence binding**이 현상의 이름에 가깝다. Stage H에서 owner/target filter와 grouping이 Qwen을 회복시킨 것과 일치한다.

Llama-70B와 Qwen3-32B(thinking off/on) 복제 후 최종 판정한다.

## Qwen3-32B: 같은 계열 크기 확장과 thinking (Llama-70B v4 judge)

| 조건 | atomic | composite worst | gap worst | gap order별 | base worst / best |
|---|---:|---:|---:|---|---:|
| 32B thinking off | 0.756 | 0.551 | +0.21 [0.16, 0.25] | +0.10 / +0.11 / +0.07 | 0.27 / 0.56 |
| 32B thinking on | 0.854 | 0.582 | +0.27 | +0.13 / +0.16 / +0.07 | 0.35 / 0.79 |
| (8B thinking off) | 0.849 | 0.487 | +0.36 | +0.24 / +0.20 / +0.21 | 0.23 / 0.50 |

- 8B → 32B로 order별 gap이 +0.20~0.24에서 +0.07~0.11로 줄었다. 크기가 gap을 줄이지만 없애지는 않는다.
- thinking은 atomic(0.76 → 0.85)과 best-order(0.56 → 0.79)를 올리지만 worst-order는 0.35에 머물고 gap은 줄지 않는다. **reasoning은 최선의 경우를 좋게 만들 뿐 순서 취약성을 없애지 못한다.**
- 통제군 C0: atomic 0.98, composite order별 0.94 / 0.85 / 0.85, gap worst +0.21, original +0.04. excess K2 −0.08 [−0.23, +0.06], K3 +0.03 [−0.07, +0.14].
- anchor: SAME 0.58 vs DIFF 0.72 (worst, p=0.039), best 0.83 vs 0.90. **different-policy 짝이 유리**(Mistral과 같은 방향). interleaved order에서 0.70 vs 0.88 (p=0.007).
- 이질성: hom gap +0.25 > het +0.18 (off), thinking on에서는 +0.25 vs +0.29로 유일하게 het가 크지만 차이가 작다.
- VERIFY_PREFER `latest_applied`: hom 0.58 vs het 0.59로 32B에서는 동질성 효과가 없다(24B·70B에서만 관측).
- 통제군 오답 53건 중 타인 record 혼입 17%.

## 종합: 모델 4종 요약 (v4 judge, `results/pilot2_memory/stage_j_summary.md`)

| 생성 / judge | conflict gap worst / orig | C0 gap worst / orig | excess K2 [CI] | excess K3 [CI] | anchor SAME / DIFF worst (p) |
|---|---|---|---|---|---|
| Qwen3-8B / Llama-70B | +0.36 / +0.24 | +0.29 / +0.15 | +0.08 [−0.07, +0.23] | +0.06 [−0.08, +0.19] | 0.53 / 0.57 (0.62) |
| Qwen3-32B / Llama-70B | +0.21 / +0.10 | +0.21 / +0.04 | −0.08 [−0.23, +0.06] | +0.03 [−0.07, +0.14] | 0.58 / 0.72 (0.039) |
| Mistral-24B / Llama-70B | +0.20 / +0.08 | +0.37 / +0.18 | −0.21 [−0.37, −0.06] | −0.14 [−0.29, −0.00] | 0.68 / 0.78 (0.031) |
| Llama-70B / Qwen3-32B | +0.12 / −0.01 | +0.03 / −0.09 | −0.02 [−0.21, +0.17] | +0.14 [−0.04, +0.33] | 0.62 / 0.72 (0.11) |

### 가설별 판정

| 가설 | 판정 | 근거 |
|---|---|---|
| H-A interference beyond independence | **부분 지지** | order별 gap은 8B·32B·24B에서 유의(+0.08~+0.24), 70B에서는 ≈0. worst-order gap은 4종 모두 유의하나 이는 순서 민감성이다 |
| H-B conflict-specific | **기각** | 통제군 judge를 완화해 재판정한 뒤에도 conflict 초과분은 8B +0.07 / 32B 0.00 / 70B −0.05 (K2, 모두 ns), Mistral −0.21 (유의하게 음수). conflict 없는 lookup 여러 개도 같은 크기로 떨어진다 |
| H-C policy 이질성 | **기각(반대 방향)** | anchor 짝에서 different-policy가 같거나 더 낫다(32B·24B 유의). cell별 gap도 heterogeneous가 작다 |
| H-D policy leakage | **부분 지지, 방향 반대** | VERIFY_PREFER 오답의 27~59%가 나중 거짓 값 채택. 24B·70B에서는 **같은 VERIFY_PREFER 둘**일 때 15~19%p 더 높다 |
| H-E cross-unit order | 미실행 | I-5 미생성. 단, base의 order flip은 4종 모두 20~50% |
| H-F global-policy prompt | 미실행 | |

### 결론

1. "여러 memory conflict를 한 요청에서 서로 다른 policy로 해결·합성하는 것이 고유하게 어렵다"는 주장은 **네 모델에서 지지되지 않는다.** judge를 보정한 뒤에도 conflict 없는 다중 slot query가 같은 크기로 떨어지고(H-B 기각), policy 이질성은 오히려 완화 요인이다(H-C 기각).
2. 실제로 관측된 것은 세 가지다: (a) 작은 모델(8B~32B)의 다중 slot query 일반 저하, 주된 실패는 slot에 잘못된 record를 묶는 것(타인 record, 나중 거짓 값, 다른 조건), (b) 모델 크기·reasoning과 무관한 **evidence order 취약성**(70B도 worst 0.39 vs best 0.74; 32B thinking on도 0.35 vs 0.79), (c) **같은 유형의 conflict가 여럿이면 recency를 전체에 적용**하는 동질성 간섭(24B·70B).
3. 따라서 Compositional Memory Conflict의 `H` 축은 폐기한다. 살릴 수 있는 것은 (b)와 (c)이며, 둘 다 "정책 이질성"이 아니라 **다중 slot에서의 evidence binding과 order robustness** 문제다.

### 한계

- judge: v4로도 Yes/No VERIFY_PREFER에서 4~12% 오판 추정, 통제군 dict 값 판정 엄격. J-8 표본 168 trial(`results/pilot2_memory/stage_j_human/`)의 인간 주석이 필요하다.
- Llama-70B는 단일 record·target date 불일치에서 abstain 행동이 있어 atomic 기준선이 낮다.
- 통제군의 attribute 구성(Career/Work 중심)이 conflict cell과 완전히 같지 않다.
- frontier API 모델 미검증.
- I-3 대화형 context, I-4 goal-framed query, I-5 cross-unit order, J-7 global-policy prompt는 미실행.

### J-8 대체 검증: 독립 LLM 주석 (Claude, blind)

인간 주석 전 단계로, 다른 계열 모델(Claude)이 `_machine` 필드를 제거한 blind 표본 168 trial(420 unit)을 [지침](stage_j_annotation_guideline.md)에 따라 직접 읽고 unit별 정오·오류 유형을 기록했다(`results/pilot2_memory/stage_j_human/claude_annotations.jsonl`). 기계 v4 judge와의 비교는 `claude_vs_machine/comparison.md`에 있다. 이는 인간 검증을 대체하지 않으며, 제3의 독립 judge이자 인간 검토용 pre-adjudication이다.

| 집단 | n unit | 일치율 | κ | 기계 정확도 | 주석 정확도 | 기계 ok / 주석 wrong | 기계 wrong / 주석 ok |
|---|---:|---:|---:|---:|---:|---:|---:|
| 전체 | 420 | 0.931 | 0.82 | 0.714 | 0.769 | 3 | 26 |
| conflict cell (K2_H1~K3_H3) | 312 | 0.94~0.97 | 0.75~0.94 | | | 2 | 15 |
| anchor (A_SAME, A_DIFF) | 48 | 0.96~1.00 | 0.78~1.00 | | | 1 | 1 |
| **통제군 K2_C0 / K3_C0** | 24 / 36 | 0.75 / 0.89 | 0.39 / 0.65 | 0.625 / 0.750 | **0.875 / 0.861** | 0 / 0 | 6 / 4 |
| policy LOOKUP | 60 | 0.833 | 0.53 | 0.700 | 0.867 | 0 | 10 |
| policy VERIFY_PREFER | 133 | 0.910 | 0.81 | 0.353 | 0.398 | 3 | 9 |
| policy SUPERSEDE | 109 | 0.963 | | 0.963 | 1.000 | 0 | 4 |
| policy CONDITION | 118 | 0.975 | 0.84 | 0.898 | 0.924 | 0 | 3 |

관찰:

1. conflict cell과 anchor 짝에서는 기계 judge와 주석이 κ 0.75~1.0으로 잘 맞는다. **J-1의 conflict gap과 J-3의 anchor 결론은 판정자 노이즈로 설명되지 않는다.**
2. 불일치 29건 중 26건은 기계가 정답을 오답 처리한 경우이며 **통제군 LOOKUP에 집중**된다(10/60). 다필드 gold("고용 상태·회사·직함·업종")에서 한 필드를 빼거나 소득을 덧붙이면 기계가 `omission`·`unsupported_extra`로 처리했다. 주석 기준 통제군 정확도는 K2_C0 0.875, K3_C0 0.861로 기계(0.625, 0.750)보다 0.11~0.25 높다.
3. 따라서 기계 judge는 통제군 gap을 과대평가했다. 이를 고친 재판정 결과는 다음 절(J-2 재계산)에 있으며, 보정 후에도 초과분은 0이다.
4. 기계가 정답 처리했는데 주석이 오답으로 본 3건은 모두 VERIFY_PREFER에서 "양쪽 값을 나열하고 확정하지 않은" 답이며 경계 사례다.
5. 주석의 오류 유형: VERIFY_PREFER `latest_applied` 69, `abstain` 11; LOOKUP `wrong_owner` 7, `partial` 1; CONDITION `wrong_condition` 9; SUPERSEDE 0. 문자열 귀인(J-4)과 같은 그림이다.

불일치 29건은 `claude_vs_machine/disagreements.jsonl`에 기계 사유·주석 사유와 함께 있어 인간 검토자는 이 29건만 보면 된다.

### J-2 재계산: 통제군 judge 완화 (`v4_lookup_lenient`)

J-8에서 드러난 통제군 LOOKUP 과잉 엄격성을 고치기 위해 v4에서 LOOKUP 규칙만 바꿨다: "질문이 묻는 핵심 필드가 맞으면 정답. 부가 필드 생략·같은 record의 추가 필드는 감점 없음. 타인 값·확정 거부는 오답." 통제군 4세트(1,320 call)만 재판정했고 conflict cell 판정은 v4 그대로다. 제 주석과의 통제군 일치율은 Qwen3-32B 0.77 → 0.90, Llama 0.90 → 0.90이다. Qwen3-8B 통제군은 거의 변하지 않았고(600 판정 중 ±10), Mistral도 변하지 않았다(오답이 타인 record 혼입이라 완화 대상이 아님).

| 생성 / judge | C0 gap worst / orig (lenient) | excess K2 worst [CI] | excess K2 order별 | excess K3 worst [CI] | excess K3 order별 |
|---|---|---|---|---|---|
| Qwen3-8B / Llama-70B | +0.29 / +0.13 | +0.07 [-0.08, +0.21] | +0.11 / +0.01 / +0.05 | +0.07 [-0.06, +0.20] | +0.11 / -0.04 / +0.13 |
| Qwen3-32B / Llama-70B | +0.17 / +0.03 | +0.00 [-0.13, +0.12] | +0.05 / -0.02 / -0.05 | +0.06 [-0.05, +0.15] | +0.07 / +0.04 / -0.02 |
| Mistral-24B / Llama-70B | +0.37 / +0.20 | -0.21 [-0.36, -0.06] | -0.11 / -0.17 / -0.21 | -0.16 [-0.29, -0.01] | -0.13 / -0.23 / -0.10 |
| Llama-70B / Qwen3-32B | +0.05 / -0.08 | -0.05 [-0.25, +0.14] | -0.06 / +0.12 / -0.05 | +0.13 [-0.04, +0.31] | +0.14 / +0.15 / +0.11 |

**judge를 보정해도 conflict 고유 초과분은 0이거나 음수다.** 4 모델 모두 K2·K3 CI가 0을 포함하거나(8B, 32B, 70B) 음수(Mistral)다. H-B는 **기각**으로 확정한다. 산출물: `results/pilot2_memory/stage_j_controls/excess/*_v4_lookup_lenient.*`.

### 연구 방향 결정 (제안)

- `docs/pilot3_cmcr/plan.md`의 CMCR-Linear(unit별 policy 추론·합성)는 **진입 조건 미충족**으로 시작하지 않는다.
- 후보 A: **order-robust multi-slot memory answering.** 4종 모두에서 order flip이 20~50%이고 thinking으로도 안 없어진다. Stage H에서 grouping이 Llama의 flip을 30% → 14%로 줄인 결과와 연결된다. 방법 기여가 가능하고 문헌(2605.14115, 2606.26079)은 단일 conflict 순서만 다룬다.
- 후보 B: **benchmark·분석 논문.** "단일 slot conflict benchmark 점수는 다중 slot 요청 성능을 과대평가하며, 실패는 conflict 유형이 아니라 evidence binding에서 온다"를 4 모델·통제군·anchor 짝 설계로 보인다. 동질성 간섭(c)이 새 관찰이다.
- 후보 A를 main으로, B의 분석을 동기 섹션으로 쓰는 구성이 가장 방어 가능하다. 단 I-3(대화형 context)와 frontier 모델 확인이 선행돼야 한다.
