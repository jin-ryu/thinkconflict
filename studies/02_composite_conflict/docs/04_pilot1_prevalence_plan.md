# 파일럿 1: 자연 검색 문서의 복합 충돌 존재·분포 검증 계획

> 작성일: 2026-08-26
> 목적: 본 데이터셋 구축 전에 `K>1,H>1` 사례의 존재, 분석 가능성, 제한된 target distribution 내 분포를 검증한다.
> 관련 본문: [복합 충돌 문제 정의·관련 연구·해결 방법](./01_problem_and_method.md)

## 0. 결론

DRAGged는 instance마다 하나의 `conflict_type`과 expected behavior가 부여된 데이터이므로 **복합 충돌 발생률의 주 자료로 사용하지 않는다**. 공식 라벨 기준으로는 `H=1`이며, 우연한 이차 충돌을 찾더라도 유형별로 선별된 데이터라는 선택 편향이 있다.

확인된 자료 중 복합 충돌을 분석하기 가장 좋은 조합은 다음과 같다.

1. **ConfRAG**: 실제 web 원문과 2~8개 answer/reason cluster를 이용한 `H` 재주석의 주 자료
2. **NatConfQA**: answer-pair conflict graph를 이용한 `K`와 혼합 relation 구조 검증
3. **QACC**: 자연 factual conflict가 주로 `H=1`로 수렴하는지 보는 대조군
4. **ConflictingQA**: 논쟁적 web 원문에서 희귀 relation/operator를 찾는 발견 표본
5. **DRAGged**: 후속 방법 평가의 single-type expected-behavior 대조군

완성된 자연 `H` gold 데이터셋은 확인되지 않았다. 따라서 이 파일럿은 기존 원자료에 conflict unit과 resolution operator를 붙여 `K/H` 주석의 가능성을 검증한다.

---

# 1. 연구 질문

- **RQ1:** 자연 web evidence에서 독립적인 conflict unit이 둘 이상인 `K>1` 사례가 존재하는가?
- **RQ2:** 그중 서로 다른 core resolution operator가 필요한 `H>1` 사례가 존재하는가?
- **RQ3:** `K`와 `H`를 두 사람이 재현성 있게 주석할 수 있는가?
- **RQ4:** 관측된 `H>1`이 noise·중복·불충분성을 conflict type으로 잘못 센 결과는 아닌가?

핵심 추정치는 다음과 같다.

```text
P(K>1,H>1)
P(H>1 | K>1)
operator-pair distribution
```

단, ConfRAG와 NatConfQA는 conflict-rich 질문을 선별한 데이터이므로 이 수치를 일반 웹 검색의 보편적 prevalence로 해석하지 않는다.

---

# 2. 사전 정의

## 2.1 `K`와 `H`

- **Conflict unit**: 하나의 atomic answer slot 또는 proposition을 둘러싼 양립 불가능한 claim group
- **`K`**: 서로 독립적인 conflict unit의 수
- **다중 충돌**: `K>1`
- **`H`**: gold plan에 필요한 서로 다른 core resolution operator의 수
- **복합 충돌**: `H>1`; 일반적으로 `H≤K`

같은 잘못된 주장을 여러 문서가 반복해도 `K=1`이다. 문서 수, 반대 문서 수, answer cluster 수를 그대로 `K`로 쓰지 않고 atomic proposition 기준으로 병합한다.

## 2.2 Core conflict와 evidence condition

다음은 core conflict unit과 `H` 계산에서 제외한다.

- 질문과 무관한 문서: `IRRELEVANT`
- 답하기에 불충분한 문서: `INSUFFICIENT`
- 같은 출처·주장의 반복: `DEPENDENT_DUPLICATE`
- 별도 반대 claim 없이 신뢰도만 낮음: `LOW_CREDIBILITY`

이들은 evidence condition으로 별도 기록한다. `FILTER`와 `COLLAPSE_DUPLICATES`는 운영 연산일 수 있지만 strict `H`에는 포함하지 않는다.

## 2.3 Relation과 core operator

| Relation | Core operator | 의미 |
|---|---|---|
| `COMPLEMENT` | `MERGE` | 양립하는 부분 정보를 결합 |
| `TEMPORAL_UPDATE` | `SUPERSEDE` | 최신 정보로 대체 |
| `SCOPE_CONDITIONED` | `CONDITION` | 시점·대상·범위를 명시해 조건화 |
| `PERSPECTIVE_DISAGREEMENT` | `KEEP_BOTH` | 정당한 관점을 함께 보존 |
| `CONTRADICT_FACT` | `VERIFY_PREFER` | 근거·출처를 검증해 우선 claim 선택 |
| `UNRESOLVED` | `ABSTAIN_QUALIFY` | 판정 유보 또는 불확실성 표시 |

동일 relation도 metadata와 evidence sufficiency에 따라 operator가 달라질 수 있으므로 relation label 수가 아니라 **확정 operator 종류 수**로 `H`를 계산한다.

---

# 3. 데이터셋 조사 결과와 활용 결정

## 3.1 ConfRAG — 주 자연 원자료

- ACL 2026 Long Paper
- 1,814개 실제 질문, 평균 9.58개 web document
- 57.2%가 explicit contradiction
- 질문마다 2~8개 answer cluster
- full markdown webpage, 문서별 implied answer·reason·trust score 보존
- cluster별 supporting document와 reason 연결
- CC BY 4.0 공개

여러 answer와 reason을 atomic proposition으로 분해할 수 있어 `K/H` 재주석에 가장 적합하다. 다만 controversial question을 선별했으므로 일반 검색 prevalence가 아니라 **conflict-rich natural setting에서의 feasibility**를 측정한다.

## 3.2 NatConfQA — K와 mixed relation 구조

- UncertaiNLP 2025
- 269 conflicting instance, 408 non-conflicting instance
- conflicting instance당 평균 5.6 passage, 평균 1.3 conflict pair
- answer별 evidence link와 conflicting answer-pair gold
- 62개 WH-mix instance에 conflicting/non-conflicting answer pair가 함께 존재

answer-pair graph가 있어 `K` 후보를 만들기 좋다. 그러나 fact-checking의 support/refute evidence에서 만들었고 resolution type은 주석되지 않았으므로, `H` 다양성보다 unit graph와 혼합 relation 검증에 사용한다.

## 3.3 QACC — factual `H=1` 대조군

실제 Google context의 factual answer disagreement를 제공한다. 여러 반대 답이 있어도 대부분 `VERIFY_PREFER` 하나로 해결될 가능성이 크다. ConfRAG에서 관측되는 `H>1`이 단순한 과분해인지 확인하는 negative/control distribution으로 사용한다.

## 3.4 ConflictingQA — 발견 표본

- ACL 2024 Long Paper
- 논쟁적 질문과 4,002개 실제 webpage row
- full raw text, 512-token relevant window, yes/no stance 제공
- MIT license repository 공개

기본 질문 구조는 binary stance라 `K=1,H=1`이 많을 것으로 예상한다. 그러나 long webpage의 reason·scope·source 차이에서 `CONDITION`, `KEEP_BOTH`, `VERIFY_PREFER` 조합 후보를 찾는 discovery source로 사용할 수 있다.

## 3.5 제외·보조 자료

- **DRAGged**: instance-level 단일 type; prevalence 제외, single-type 행동 평가만
- **RAMDocs**: ambiguity·misinformation·noise를 의도적으로 혼합; 자연 prevalence 제외
- **ConflictBank**: synthetic conflict; 통제형 `H` 실험에만 사용
- **MAGIC**: `K` count/localization 평가; `H` prevalence에는 부적합

---

# 4. 표집 설계

## 4.1 ConfRAG 대표 표본

- `ConfRAGsuggested.jsonl` 전체에서 120개 단순 무작위 추출
- `contradicts`, source, cluster 수에 따른 사후 분포는 보고하되 표집에는 사용하지 않음
- seed와 item ID를 사전 고정
- answer/reason cluster를 먼저 검토하고, 불명확할 때만 연결된 full webpage 확인

120개는 feasibility pilot 규모다. 최종 benchmark 크기는 관측된 `H>1` 비율과 annotation cost를 이용한 power analysis 후 정한다.

## 4.2 NatConfQA 구조 표본

- WH-mix 62개 전수 분석
- 각 answer pair를 unit 후보로 변환
- 같은 proposition의 여러 pair를 하나의 conflict unit으로 병합
- conflict와 non-conflict relation이 섞인 상황에서 `K` 일치도 측정

이 표본은 선별 데이터이므로 prevalence 분모에 넣지 않는다.

## 4.3 QACC 대조 표본

- 로컬 전처리 자료에서 60개 단순 무작위 추출
- strict `H`를 계산하고 factual conflict가 `VERIFY_PREFER`로 수렴하는지 확인
- ConfRAG와 비율을 단순 pooling하지 않고 분리 보고

## 4.4 ConflictingQA 발견 표본

- 질문 40개 이내
- stance 균형은 맞추되 prevalence를 계산하지 않음
- 희귀 operator 조합과 annotation guideline의 누락 범주 탐색에만 사용

## 4.5 일반 검색 prevalence 확장

최종 논문에서 일반 QA retrieval의 prevalence를 주장하려면 별도 `Fresh-Retrieval`을 구성한다.

1. NQ·ELI5·Yahoo에서 controversial filter 없이 질문 100~200개 무작위 추출
2. ConfRAG 공개 pipeline으로 동일 검색기와 top-k 적용
3. 검색 날짜, query, rank, crawl failure를 기록
4. ConfRAG와 같은 schema로 이중 주석
5. `P(K>1,H>1)`를 source dataset별로 보고

이 확장을 하지 않으면 논문의 주장은 “자연 conflict-rich benchmark에서 복합 충돌이 존재한다”로 한정한다.

---

# 5. 주석 스키마와 절차

## 5.1 Sidecar schema

AIR 연구의 스키마는 수정하지 않는다. 복합 충돌 연구는 독립적인 sidecar 스키마를 사용한다. `question_id`로 연결되는 sidecar JSONL을 사용한다.

```json
{
  "question_id": "confrag-0042",
  "annotation_version": "kh-pilot-v2",
  "conflict_units": [
    {
      "unit_id": "u1",
      "question_slot": "암 위험의 방향",
      "claim_groups": [
        {"claim": "위험 감소", "doc_ids": [1, 3]},
        {"claim": "위험 증가", "doc_ids": [2, 4]}
      ],
      "relation": "SCOPE_CONDITIONED",
      "operator": "CONDITION",
      "operator_precondition": "암 종류와 섭취량을 구분",
      "evidence_conditions": []
    }
  ],
  "K": 1,
  "operator_set": ["CONDITION"],
  "H": 1,
  "annotator_id": "A"
}
```

`K`와 `H`는 unit·operator에서 자동 파생하고 사람이 별도로 입력하지 않는다.

## 5.2 주석 순서

1. 질문을 atomic answer slot으로 분해한다.
2. answer/reason cluster에서 proposition과 evidence span을 찾는다.
3. 동일 proposition의 claim group을 하나의 unit으로 묶는다.
4. relation과 core operator를 판정한다.
5. noise·insufficiency·duplicate·credibility는 condition으로 분리한다.
6. full webpage가 필요한지 표시하고 최소 범위만 확인한다.
7. unit·operator 확정 후 `K/H`를 자동 계산한다.

## 5.3 주석 품질

1. 20개 calibration set을 두 주석자가 독립 처리
2. guideline v2 동결
3. 전체 표본 이중 독립 주석
4. reconciliation 후 남은 불일치는 제3 adjudicator 처리
5. 원 annotation과 adjudicated gold 모두 보존

측정 지표:

- `H>1` Cohen's kappa
- `K/H` exact agreement와 weighted kappa
- conflict-unit localization F1
- matched unit의 relation/operator macro-F1

진행 기준은 `H>1` kappa ≥ 0.70, operator macro-F1 ≥ 0.75다. 미달하면 데이터 규모를 늘리지 않고 taxonomy와 unit atomicity 지침을 먼저 수정한다.

---

# 6. 분석과 의사결정 기준

## 6.1 보고값

ConfRAG 대표 표본에서 Wilson 95% 신뢰구간과 함께 다음을 보고한다.

```text
P(K=0), P(K=1), P(K>1)
P(H>1)
P(K>1,H>1)
P(H>1 | K>1)
```

NatConfQA에서는 unit graph 통계와 `K` 일치도를, QACC에서는 strict `H=1` 비율을 보고한다. 발견 표본은 빈도가 아니라 새로운 operator 조합만 보고한다.

## 6.2 Main claim 유지

다음을 모두 만족하면 `Natural-Composite` 본 구축을 진행한다.

1. ConfRAG 120개에서 adjudicated `K>1,H>1` 사례 15개 이상
2. ConfRAG의 `P(H>1 | K>1)` 점추정치 10% 이상
3. `H>1` kappa ≥ 0.70, operator macro-F1 ≥ 0.75
4. 최소 3개 서로 다른 operator pair 관측
5. QACC보다 ConfRAG의 strict `H>1` 비율이 높고, 차이가 과분해 오류로 설명되지 않음

## 6.3 축소·중단

- ConfRAG 복합 사례가 8~14개 또는 조건부 비율 5~10%: rare-but-important stress test로 범위 축소
- 8개 미만 또는 조건부 비율 5% 미만: 자연 prevalence를 주요 기여로 주장하지 않음
- 주석 일치도 미달: taxonomy를 한 번 수정해 재파일럿; 다시 미달하면 `H` annotation 기여 중단
- 관측된 operator가 사실상 하나뿐이면 `K` 연구만 유지하고 복합 충돌 주장은 중단

---

# 7. 산출물과 작업량

## 7.1 산출물

- `data/pilot1/sample_manifest.json`
- `data/pilot1/annotations_A.jsonl`
- `data/pilot1/annotations_B.jsonl`
- `data/pilot1/adjudicated.jsonl`
- `data/pilot1/guideline.md`
- `results/pilot1/prevalence_summary.json`
- `docs/06_pilot1_result.md`

## 7.2 예상 작업량

- 데이터 확보·변환과 calibration: 1~2일
- ConfRAG 120개·NatConfQA 62개·QACC 60개 이중 주석: cluster/reason 선검토 기준 3~6인일
- reconciliation·adjudication: 1~2인일
- 집계·오류 분석: 1일

LLM은 claim·span 후보를 미리 표시하는 보조 도구로만 사용한다. `K`, relation, operator, `H`의 gold는 사람이 확정한다.

---

# 8. 실행 체크리스트

- [ ] ConfRAG와 NatConfQA 원자료·라이선스를 확인하고 snapshot을 고정한다.
- [ ] ConfRAG 대표 표본과 ConflictingQA 발견 표본을 분리한다.
- [ ] 원 conflict label을 숨긴 annotation view를 만든다.
- [ ] 20개 calibration에서 unit atomicity와 operator 경계를 합의한다.
- [ ] 두 주석자가 독립 주석하고 agreement를 계산한다.
- [ ] ConfRAG 대표 표본에서만 feasibility 비율을 계산한다.
- [ ] 일반 prevalence를 주장하려면 unfiltered `Fresh-Retrieval`을 추가한다.
- [ ] 사전 기준에 따라 본 구축·범위 축소·중단 중 하나를 기록한다.
