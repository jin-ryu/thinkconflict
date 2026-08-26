# Pilot 1 `K/H` annotation guideline

> 상태: calibration v1. 20개 독립 주석 후 불일치 사례를 반영해 v2로 동결한다.

> 빠른 go/no-go용 LLM 초벌 + 연구자 1인 전수 검토는 `data/pilot1/REVIEW_GUIDE.md`를 따른다. 이는 아래의 논문용 독립 주석을 대체하지 않는다.

## 1. Hybrid 주석과 독립성 원칙

### Calibration과 blind audit

주석자 A와 B는 같은 `calibration_view.jsonl`을 받되 상대방의 annotation과 LLM 초벌을 보지 않는다. 두 파일을 제출한 뒤에만 agreement와 불일치 사례를 논의한다. LLM 초벌을 두 사람에게 함께 보여주면 같은 anchoring error를 공유해 human-human IAA가 인위적으로 높아질 수 있으므로 calibration과 B의 random audit에는 제공하지 않는다.

### 전체 표본

동결된 guideline 이후에는 LLM이 claim group, relation, operator, 근거 span을 초벌 생성한다. 인간 A는 모든 초벌을 확인해 `accept`, `edit`, `reject`로 판정하고 최종 unit을 확정한다. 인간 B는 사전 고정된 random 20%와 별도 `H>1` 감사 표본을 LLM/A 답을 보지 않고 독립 처리한다.

LLM 출력은 gold가 아니며 모델·prompt·temperature·raw response를 보존한다. 최종 `K/H`는 인간이 확정한 unit·operator에서 자동 계산한다.

## 2. 주석 단위

질문에 답하기 위해 별도로 해결해야 하는 최소 atomic proposition을 하나의 conflict unit으로 정의한다. 문서 수나 answer cluster 수를 그대로 unit 수로 세지 않는다.

- 같은 주장을 여러 문서가 반복: unit 1개
- 서로 다른 두 answer slot이 각각 충돌: unit 2개
- 한 주장에 세 후보 답이 경쟁: 대체로 unit 1개
- 한 문서 안의 서로 독립적인 두 주장에 각각 충돌: unit 2개

충돌이 없으면 `conflict_units=[]`, `K=0`, `H=0`으로 완료한다.

## 3. Core relation과 operator

| Relation | 기본 operator | 판정 질문 |
|---|---|---|
| `COMPLEMENT` | `MERGE` | 두 주장이 함께 참이며 합쳐야 완전한가? |
| `TEMPORAL_UPDATE` | `SUPERSEDE` | 동일 대상·범위에서 시점 때문에 구정보를 대체해야 하는가? |
| `SCOPE_CONDITIONED` | `CONDITION` | 대상·지역·조건·정의·시점을 명시하면 양립하는가? |
| `PERSPECTIVE_DISAGREEMENT` | `KEEP_BOTH` | 사실 선택이 아니라 정당한 관점 차이를 보존해야 하는가? |
| `CONTRADICT_FACT` | `VERIFY_PREFER` | 동일 범위의 양립 불가능한 사실 주장 중 근거를 검증해 선택해야 하는가? |
| `UNRESOLVED` | `ABSTAIN_QUALIFY` | 문맥만으로 우선 주장을 정당화할 수 없는가? |

relation 이름만 보고 operator를 자동 결정하지 않는다. 예를 들어 시간 표현이 있어도 질문이 역사적 시점을 묻는다면 무조건 `SUPERSEDE`하지 않는다. `operator_precondition`에 선택 근거를 적는다.

## 4. H에서 제외하는 evidence condition

다음은 core operator 종류 수 `H`에 포함하지 않고 별도로 기록한다.

- `IRRELEVANT`: 질문과 무관
- `INSUFFICIENT`: 관련은 있지만 답하기 불충분
- `DEPENDENT_DUPLICATE`: 동일 출처·재인용·주장 반복
- `LOW_CREDIBILITY`: 별도 반대 claim 없이 신뢰도만 낮음

## 5. 작성 절차

1. 질문을 atomic answer slot으로 나눈다.
2. 각 문서 또는 제공 answer/reason에서 질문 관련 claim을 찾는다.
3. 동일 proposition을 다루는 claim을 한 unit으로 묶는다.
4. 최소 두 claim group과 근거 `doc_ids`를 기록한다.
5. relation, operator, operator precondition을 판정한다.
6. evidence condition을 core conflict와 분리한다.
7. `status`를 `complete`로 바꾸고 `K`, `H`, `operator_set`을 unit에서 다시 계산한다.

## 6. 경계 사례 기록

확신이 낮아도 임의의 새 label을 만들지 않는다. 가장 가까운 relation/operator를 선택하고 `notes`에 다음 중 하나를 적는다.

- `atomicity_uncertain`
- `relation_uncertain`
- `operator_uncertain`
- `full_document_needed`
- `source_dependency_uncertain`

두 주석자가 반복적으로 같은 경계에서 불일치하면 calibration 후 guideline을 개정한다. 전체 단계에서는 LLM 초벌의 accept/edit/reject와 오류 원인을 함께 기록한다.
