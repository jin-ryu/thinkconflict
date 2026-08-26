# 파일럿 2: `K` 고정 조건에서 `H`의 독립 난이도 검증 계획

> 작성일: 2026-08-26
> 목적: 충돌 수 `K`가 같아도 resolution heterogeneity `H`가 증가하면 기존 RAG·CoT·단일 유형 접근의 성능이 하락하는지 검증한다.
> 선행 조건: [파일럿 1](04_pilot1_prevalence_plan.md)의 이중 주석과 adjudication이 완료되어야 한다.
> 관련 본문: [복합 충돌 문제 정의와 방법](01_problem_and_method.md)

## 0. 핵심 결정

파일럿 2의 주 데이터는 새 데이터셋이나 DRAGged가 아니라 **파일럿 1에서 전처리·판정한 동일한 자연 검색 사례**다. 원문 문서, atomic conflict unit, relation, operator, `K`, `H` sidecar를 그대로 이어받는다.

주 비교는 동일한 `K` 안에서 자연 `H=1`과 `H>1` 사례를 matching하는 관찰 비교다. 자연 사례가 부족할 때만 파일럿 1의 판정 완료 atomic unit으로 통제형 counterfactual pair를 만든다. ConflictBank는 이마저 불가능할 때의 fallback이고, DRAGged는 파일럿 단계에서 제외한다.

검증할 최소 주장은 다음과 같다.

> 문서 수, 입력 길이, 답 cluster 수, evidence sufficiency 등을 맞춘 같은 `K` 조건에서도 `H`가 증가하면 기존 방법의 모든-unit 해결률이 낮아진다.

이 주장이 지지되어야 `H`를 `K`와 구별되는 난이도 축으로 제안하고 operator-composition 파이프라인을 개발할 근거가 생긴다.

---

## 1. 왜 필요한가

`K`가 커지면 처리할 충돌이 많아져 성능이 떨어지는 것은 비교적 예상 가능하다. 그러나 `H`의 필요성은 별도 검증이 필요하다. 예를 들어 `K=2`인 두 사례라도 다음은 요구 계산이 다르다.

- `H=1`: 두 unit 모두 `VERIFY_PREFER`
- `H=2`: 한 unit은 `VERIFY_PREFER`, 다른 unit은 `SUPERSEDE`

두 조건의 차이가 없다면 복합 operator를 합성하는 PCCR은 불필요하게 복잡할 수 있다. 반대로 같은 `K`에서도 `H` 효과가 있고 gold plan을 제공했을 때 회복된다면, 병목이 단순 문서 수가 아니라 해결 연산의 선택·합성에 있다는 근거가 된다.

서로 다른 데이터셋의 점수를 직접 비교하지 않는다. 데이터셋, 문서 수, 토큰 길이, 도메인 등이 함께 달라져 `H`의 효과를 분리할 수 없기 때문이다.

---

## 2. 파일럿 1에서 넘겨받는 데이터

### 2.1 정본 입력

- `data/pilot1/sample_manifest.json`
- `data/pilot1/adjudicated.jsonl`
- 원 데이터셋의 고정된 retrieval documents
- unit별 claim/evidence span, relation, operator
- instance별 `K`, `H`, evidence condition
- 주석 불일치와 adjudication 기록

파일럿 2에서 `K/H`를 다시 자동 추정해 표본을 만들지 않는다. 파일럿 1의 사람 판정본만 gold strata로 사용한다.

### 2.2 진입 기준

- `H>1` 주석 kappa ≥ 0.70
- operator macro-F1 ≥ 0.75
- adjudicated `H>1` 자연 사례 10개 이상

일치도 기준을 충족하지 못하면 파일럿 2를 실행하지 않고 taxonomy를 먼저 수정한다.

### 2.3 자연 사례 수에 따른 설계

| 파일럿 1의 자연 `H>1` 수 | 파일럿 2 설계 |
|---:|---|
| 20개 이상 | 같은 `K`의 `H=1` 대조를 1:1 이상 matching한 자연 주 분석 |
| 10~19개 | 모든 `H>1`에 `H=1` 대조를 최대 1:2 matching; 자연 분석은 효과 방향 중심 |
| 10개 미만 | 자연 비교는 사례 분석으로 축소; 판정된 unit 기반 통제형 pair를 주 분석 |

---

## 3. 주 분석: 자연 matched comparison

### 3.1 비교 단위

가능하면 `K=2`를 주 strata로 사용한다. 표본이 충분하면 `K=3+`를 보조 strata로 추가한다.

- Treatment: `H>1`
- Control: 같은 `K`의 `H=1`
- 주 outcome: all-unit resolution accuracy

### 3.2 Matching 변수

각 `H>1` 사례에 다음 조건이 가장 가까운 `H=1` 사례를 매칭한다.

- 원 데이터셋과 source distribution
- `K`
- retrieval document 수
- 전체 입력 토큰 수
- answer/reason cluster 수
- conflict evidence와 supporting evidence 수
- evidence sufficiency
- 질문 길이와 답 형식
- 날짜·출처 등 metadata 가용성

동일한 질문을 유지하는 완전한 인과 pair가 아니므로 이를 `H`의 순수 인과효과라고 부르지 않는다. 자연 데이터에서 confound를 줄인 **matched observational evidence**로 보고한다.

### 3.3 표본 품질 보고

- matching 전후 standardized mean difference
- 매칭되지 않아 제외된 `H>1` 사례 수와 이유
- 데이터셋·operator combination별 분포
- propensity/matching specification 변화에 대한 민감도

---

## 4. 보조 분석: 파일럿 1 unit 기반 통제형 pair

자연 표본만으로 `H`와 표면 난이도를 충분히 분리하기 어려우므로, 판정 완료 unit을 재조합한 최소 통제 실험을 보조로 둔다.

### 4.1 구성 원칙

서로 독립적인 두 atomic unit을 하나의 두-slot 질문으로 구성한다. 모든 조건에서 `K=2`를 유지하고 두 번째 unit의 operator만 바꾼다.

| 조건 | Unit A | Unit B | `K` | `H` |
|---|---|---|---:|---:|
| Homogeneous | `VERIFY_PREFER` | `VERIFY_PREFER` | 2 | 1 |
| Heterogeneous | `VERIFY_PREFER` | `SUPERSEDE` | 2 | 2 |

추가 조합은 파일럿 1에서 실제 관측되고 판정된 operator만 사용한다. 합성만을 위해 존재하지 않는 relation을 만들지 않는다.

### 4.2 통제 규칙

- 두 조건의 document 수와 evidence 역할 수 동일
- 입력 토큰 길이 차이 10% 이내
- 같은 답 slot 구조와 동일한 metadata 형식
- 한 unit의 해결이 다른 unit의 gold를 바꾸지 않음
- 문서 순서 permutation 동일
- 두 명이 자연성, unit 독립성, operator 차이를 확인

### 4.3 외부 데이터 fallback

파일럿 1에서 필요한 operator 조합을 만들 수 없을 때만 ConflictBank를 후보 pool로 검토한다. 원 논문의 evidence type을 gold operator로 자동 변환하지 않고 사람 검증을 거친다. 이 fallback 결과는 자연 주 분석과 분리 보고한다.

---

## 5. 비교 방법

PCCR 전체는 아직 구현하지 않는다. 기존 접근이 `H`에 취약한지 최소 비용으로 확인한다.

1. **Vanilla RAG**: 문서와 질문만 주고 직접 답변
2. **One-shot CoT**: 주장을 비교하고 충돌을 해결한 뒤 답하라는 일반 지시
3. **Taxonomy-aware CoT**: relation/operator 정의만 제공
4. **Single-global-operator pipeline**: instance에 하나의 대표 operator를 선택해 모든 unit에 적용
5. **Oracle-Global-Operator**: gold 대표 type을 제공해 탐지 오류를 제거
6. **Oracle-Units**: gold unit과 연결 evidence 제공
7. **Oracle-Plan**: unit별 gold operator까지 제공

`Oracle-Plan`도 실패하면 operator composition보다 답 생성이나 데이터 자체가 병목이다. `Oracle-Plan`은 성공하지만 baseline이 실패할 때 PCCR 개발의 여지가 확인된다.

---

## 6. 모델과 실행 설정

- 주 모델: `Qwen/Qwen3.6-27B`, bf16, 기존 vLLM 환경
- 주 결과: thinking on; 동일 가중치 thinking off 보조 비교
- deterministic generation이 가능한 설정을 우선 사용
- 자연 문서 순서 seed 3개
- 조건별 동일 max output token과 stop condition
- 1개 모델에서 가설 확인 후 Gemma 3 27B로 계열 외 재현

모든 방법에는 같은 문서와 metadata를 제공한다. 일반 baseline에는 gold `H`, unit, operator를 노출하지 않는다. 실제 prompt 길이, 생성 토큰, 호출 수, latency를 기록한다.

---

## 7. 평가

### 7.1 주 지표

- **All-unit resolution accuracy**: 모든 unit이 각 gold behavior를 만족한 비율
- **Per-unit behavior accuracy**
- **Answer-set correctness**
- **Invalid collapse rate**: 보존·조건화할 답을 하나로 잘못 축약
- **Invalid preservation rate**: 대체·배제할 답을 함께 정답처럼 보존

주 지표는 all-unit resolution accuracy다. 단순 평균 per-unit accuracy는 일부 unit의 지속적 누락을 숨길 수 있다.

### 7.2 보조 지표

- citation support와 잘못된 evidence 채택률
- operator prediction macro-F1와 `H` 추정 정확도
- 답변 completeness
- 생성 토큰, wall-clock latency, model call 수
- 문서 순서 seed 간 일관성

규칙 기반 채점이 어려운 `KEEP_BOTH`, `CONDITION`, `ABSTAIN_QUALIFY`는 blind human evaluation을 주 판정으로 한다. LLM judge는 사람 판정과의 일치도를 검증한 뒤 보조 집계에만 사용한다.

---

## 8. 분석과 결정 기준

### 8.1 자연 비교

같은 `K` strata에서 다음을 추정한다.

```text
Delta_H = score(H>1) - score(H=1)
```

matched bootstrap 95% 신뢰구간과 all-unit success의 조건부 비교를 보고한다. 표본이 허용하면 dataset, token length, document count를 공변량으로 포함한 mixed-effects logistic regression을 보조로 사용한다.

### 8.2 통제형 pair

pair별 `H=2 - H=1` 차이, paired bootstrap, McNemar 검정을 사용한다. 핵심은 p-value 하나보다 효과 방향, operator 조합 간 재현성, 오류 메커니즘이다.

### 8.3 PCCR 개발 gate

다음을 만족하면 PCCR 최소 구현으로 진행한다.

1. 자연 matched comparison에서 최선 일반 baseline의 `Delta_H`가 음수
2. 통제형 pair의 Vanilla/CoT 중 2개 이상에서 `Delta_H≤-8%p`
3. `H>1`에서 operator 일괄 적용, unit 누락, 잘못된 보존·축약이 증가
4. `Oracle-Plan`이 최선 일반 baseline보다 10%p 이상 높음
5. 효과가 최소 2개 operator 조합에서 같은 방향

자연 표본이 20개 미만이면 1번은 통계적 확증이 아닌 방향성 조건으로 해석한다.

### 8.4 반대 결과의 해석

- CoT가 Oracle-Plan에 근접: 복잡한 graph/agent 대신 저비용 structured prompt를 최종 방법 후보로 검토
- baseline과 Oracle-Plan 모두 하락: composite 입력 길이·답 생성·데이터 설계 병목
- single-global 방식만 하락: 단일 routing 비판은 가능하지만 새 파이프라인 필요성은 약함
- `H` 차이 없음: `H` 독립 난이도 주장을 보류하고 PCCR 구현을 확대하지 않음

---

## 9. 산출물

- `data/pilot2/natural_matches.jsonl`
- `data/pilot2/controlled_pairs.jsonl`
- `data/pilot2/human_validation.jsonl`
- `results/pilot2/raw/<method>.jsonl`
- `results/pilot2/metrics.json`
- `results/pilot2/error_analysis.jsonl`
- `docs/07_pilot2_result.md`

PCCR graph, plan search, multi-agent, verifier는 이 파일럿 범위에서 구현하지 않는다.

## 10. 실행 체크리스트

- [ ] 파일럿 1의 guideline과 adjudicated sidecar를 동결한다.
- [ ] 주석 일치도와 자연 `H>1` 수로 설계 branch를 결정한다.
- [ ] 같은 `K`의 자연 `H=1/H>1` 사례를 matching한다.
- [ ] 필요한 경우 파일럿 1 atomic unit으로 통제형 pair를 만든다.
- [ ] 네 baseline과 세 oracle을 동일 모델·문서 조건에서 실행한다.
- [ ] all-unit success와 composition 오류를 blind 평가한다.
- [ ] gate에 따라 PCCR 개발, 데이터 설계 수정, 주장 보류 중 하나를 결정한다.
