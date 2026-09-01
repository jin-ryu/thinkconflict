# 파일럿 1: 자연 검색 문서의 복합 충돌 존재·분포 검증 계획

> **실행 상태: 완료.** 실제 실행은 시간 제약으로 독립 인간 주석 대신 Codex 직접 판정으로 축소되었다. 202건에서 strict `K>1,H>1`은 0건이었으며, 상세 결과와 계획 대비 변경은 [파일럿 1 결과](result.md)를 따른다. 이 문서의 나머지 내용은 사전 계획으로 보존한다.

> 작성일: 2026-08-26
> 목적: 본 데이터셋 구축 전에 `K>1,H>1` 사례의 존재, 분석 가능성, 제한된 target distribution 내 분포를 검증한다.
> 관련 본문: [복합 충돌 문제 정의·관련 연구·해결 방법](../background/problem_and_method.md)

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
| `TEMPORAL_UPDATE` | `SUPERSEDE` | 최신 정보로 대체 |
| `SCOPE_CONDITIONED` | `CONDITION` | 시점·대상·범위를 명시해 조건화 |
| `PERSPECTIVE_DISAGREEMENT` | `KEEP_BOTH` | 정당한 관점을 함께 보존 |
| `CONTRADICT_FACT` | `VERIFY_PREFER` | 근거·출처를 검증해 우선 claim 선택 |
| `UNRESOLVED` | `ABSTAIN_QUALIFY` | 판정 유보 또는 불확실성 표시 |

`COMPLEMENT`는 양립 불가능한 claim이 아니므로 strict pilot에서는 core conflict에서 제외하고 보조 evidence relation으로만 기록한다. 동일 relation도 metadata와 evidence sufficiency에 따라 operator가 달라질 수 있으므로 relation label 수가 아니라 **확정 operator 종류 수**로 `H`를 계산한다.

---

# 3. 데이터셋 조사 결과와 활용 결정

## 3.0 공식 논문·데이터 주소

| 데이터셋 | 논문 | 공식 데이터·코드 | 파일럿 역할 |
|---|---|---|---|
| ConfRAG | [ACL 2026](https://aclanthology.org/2026.acl-long.11/) | [OracleY/ConfRAG (Hugging Face)](https://huggingface.co/datasets/OracleY/ConfRAG) — 저자가 공개한 데이터 위치이며 별도 공식 GitHub는 확인되지 않음 | 주 자연 원자료 |
| NatConfQA | [UncertaiNLP 2025](https://aclanthology.org/2025.uncertainlp-main.13/) | [EN555/ContraQA](https://github.com/EN555/ContraQA) | `K`·answer-pair graph 구조 검증 |
| QACC | [Findings of NAACL 2025](https://aclanthology.org/2025.findings-naacl.99/) | [amazon-science/qa-with-conflicting-context](https://github.com/amazon-science/qa-with-conflicting-context) | factual `H=1` 대조군 |
| ConflictingQA | [ACL 2024](https://aclanthology.org/2024.acl-long.403/) | [AlexWan0/rag-convincingness](https://github.com/AlexWan0/rag-convincingness) | 희귀 operator 발견 표본 |

파일럿에서 제외하거나 통과 후 검토할 자료의 주소는 다음과 같다.

| 데이터셋 | 논문 | 데이터·코드 |
|---|---|---|
| DRAGged/CONFLICTS | [arXiv:2506.08500](https://arxiv.org/abs/2506.08500) | [google-research-datasets/rag_conflicts](https://github.com/google-research-datasets/rag_conflicts) |
| RAMDocs | [arXiv:2504.13079](https://arxiv.org/abs/2504.13079) | [HanNight/RAMDocs](https://github.com/HanNight/RAMDocs) |
| ConflictBank | [arXiv:2408.12076](https://arxiv.org/abs/2408.12076) | [zhaochen0110/conflictbank](https://github.com/zhaochen0110/conflictbank) |
| MAGIC | [Findings of EMNLP 2025](https://aclanthology.org/2025.findings-emnlp.466/) | 공식 논문 페이지 참조 |

## 3.1 ConfRAG — 주 자연 원자료

- ACL 2026 Long Paper
- 전체 원본은 1,814개이며, 본 파일럿이 사용하는 권장판 `ConfRAGsuggested.jsonl`은 공개 revision에서 1,098개
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
- 공개 v1.0에서 conflict WH 문항은 89개이며, conflicting/non-conflicting answer pair가 실제로 함께 있는 strict WH-mix는 22개

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

- 공개 v1.0 strict WH-mix 22개 전수 분석
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

## 5.3 주석 품질 — LLM 초벌 + 인간 검토 + 독립 감사

비용과 재현성을 함께 확보하기 위해 다음 hybrid protocol을 사용한다.

1. **Blind calibration:** 20개를 인간 A와 B가 LLM 초벌을 보지 않고 독립 처리한다.
2. calibration에서 `H>1` kappa와 operator agreement를 확인하고 guideline v2를 동결한다.
3. **LLM pre-annotation:** 동결된 schema로 전체 표본의 unit·relation·operator 후보와 근거 span을 생성한다. 모델·prompt·temperature·출력 원문을 보존한다.
4. **Human A full verification:** A가 LLM 초벌을 전수 검토해 accept, edit, reject 중 하나로 확정한다. `K/H`는 확정 unit에서 자동 파생한다.
5. **Human B blind audit:** B는 LLM과 A의 답을 보지 않고, 사전 고정한 데이터셋별 무작위 20%를 독립 주석한다. 희귀 `H>1`의 오류 분석을 위해 A가 판정한 `H>1` 전수를 추가 감사하되 무작위 IAA와 분리 보고한다.
6. audit 불일치는 reconciliation 후 필요할 때 제3 adjudicator가 확정한다. LLM 원안, A 수정본, B 독립본, adjudicated gold를 모두 보존한다.

측정 지표:

- calibration 및 blind random audit의 `H>1` Cohen's kappa
- `K/H` exact agreement와 weighted kappa
- conflict-unit localization F1
- matched unit의 relation/operator macro-F1
- LLM draft의 unit/operator precision·recall, 인간 accept/edit/reject 비율
- instance당 인간 검토 시간과 full manual annotation 대비 절감량

진행 기준은 calibration의 `H>1` kappa ≥ 0.70, operator macro-F1 ≥ 0.75다. 미달하면 LLM 초벌을 확대하지 않고 taxonomy와 unit atomicity 지침을 먼저 수정한다. blind random audit에서도 같은 기준을 목표로 하며, 미달하면 audit 비율을 늘리거나 전체 이중 주석으로 전환한다.

인간 B 없이 **LLM 초벌 + 인간 A 한 명**만 사용하는 설계도 탐색적 파일럿에는 가능하다. 그러나 이 경우 human-human IAA를 보고할 수 없으므로 결과를 gold benchmark나 재현 가능한 새 taxonomy로 강하게 주장하지 않고, 후속 논문 단계에서 독립 인간 감사를 추가해야 한다.

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

- `data/pilot1_search/sample_manifest.json`
- `data/pilot1_search/llm_drafts.jsonl`
- `data/pilot1_search/human_A_verified.jsonl`
- `data/pilot1_search/human_B_random_audit.jsonl`
- `data/pilot1_search/human_B_h_gt1_audit.jsonl`
- `data/pilot1_search/adjudicated.jsonl`
- `docs/pilot1_search/annotation_guideline.md`
- `results/pilot1_search/prevalence_summary.json`
- `docs/pilot1_search/result.md`

## 7.2 예상 작업량

- 데이터 확보·변환과 calibration: 1~2일
- 전체 표본 LLM 초벌 + 인간 A 전수 검토: 모델 비용과 검토 속도에 따라 2~4인일
- 인간 B calibration 20개 + 무작위 20% blind audit + `H>1` 추가 감사: 1~3인일
- reconciliation·adjudication: 1~2인일
- 집계·오류 분석: 1일

LLM은 claim·span 후보를 미리 표시하는 보조 도구로만 사용한다. `K`, relation, operator, `H`의 gold는 사람이 확정한다.

---

# 8. 실행 체크리스트

- [ ] ConfRAG와 NatConfQA 원자료·라이선스를 확인하고 snapshot을 고정한다.
- [ ] ConfRAG 대표 표본과 ConflictingQA 발견 표본을 분리한다.
- [ ] 원 conflict label을 숨긴 annotation view를 만든다.
- [ ] 20개 calibration에서 unit atomicity와 operator 경계를 합의한다.
- [ ] calibration 20개는 인간 A/B가 LLM 없이 독립 주석하고 agreement를 계산한다.
- [ ] guideline 동결 후 LLM 초벌과 인간 A 전수 검토를 수행한다.
- [ ] 인간 B가 사전 고정 random 20%를 blind audit하고, `H>1` 추가 감사는 별도로 보고한다.
- [ ] ConfRAG 대표 표본에서만 feasibility 비율을 계산한다.
- [ ] 일반 prevalence를 주장하려면 unfiltered `Fresh-Retrieval`을 추가한다.
- [ ] 사전 기준에 따라 본 구축·범위 축소·중단 중 하나를 기록한다.
