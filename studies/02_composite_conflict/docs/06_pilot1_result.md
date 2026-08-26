# 파일럿 1 결과: 자연 검색 문서의 strict `K/H` 분석

> 실행일: 2026-08-26
> 상태: 완료 — exploratory go/no-go pilot
> 상세 판정표: [final_llm_judgment_table.md](../results/pilot1/final_llm_judgment_table.md)
> 구조화 결과: [final_llm_judgments.jsonl](../data/pilot1/final_llm_judgments.jsonl)

## 0. 결론

ConfRAG, NatConfQA, QACC의 202건을 strict `K/H` 기준으로 판정한 결과 `K>1,H>1` 복합 충돌은 한 건도 관측되지 않았다. 따라서 “자연 검색 문서에서 query-level 복합 충돌이 충분히 자주 발생한다”는 주장은 현재 자료로 지지되지 않는다.

기존 파일럿 2였던 자연 `H=1/H>1` matched comparison은 필요한 treatment 사례가 없어 중단한다. 후속 파일럿은 `K/H`를 유지하되 장기 사용자 메모리에서 query-level composition의 현실성과 독립 난이도를 검증하는 [Compositional Memory Conflict 계획](05_pilot2_compositional_memory_plan.md)으로 변경한다.

## 1. 표본과 결과

| 데이터셋 | 표집 | N | `K=0` | `K=1` | `K>1,H>1` |
|---|---|---:|---:|---:|---:|
| ConfRAG | 무작위 | 120 | 67 | 53 | 0 |
| NatConfQA | strict WH-mix 전수 | 22 | 2 | 20 | 0 |
| QACC | 무작위 대조 | 60 | 28 | 32 | 0 |
| **전체** |  | **202** | **97** | **105** | **0** |

ConfRAG에서 0/120이므로 양측 95% Wilson 구간의 상한은 약 3.1%다. 이 값은 ConfRAG 표집 범위의 희귀성 근거일 뿐 일반 웹 검색 prevalence 추정치가 아니다.

## 2. 관측된 단일-unit 해결 연산

복합 사례는 없었지만 atomic conflict의 해결 연산 자체는 다양하게 관측됐다.

| Operator | ConfRAG | NatConfQA | QACC | 합계 |
|---|---:|---:|---:|---:|
| `CONDITION` | 20 | 10 | 21 | 51 |
| `KEEP_BOTH` | 17 | 0 | 0 | 17 |
| `VERIFY_PREFER` | 9 | 7 | 4 | 20 |
| `SUPERSEDE` | 3 | 3 | 6 | 12 |
| `ABSTAIN_QUALIFY` | 4 | 0 | 1 | 5 |

이는 서로 다른 해결 정책이 실제 conflict unit에 필요하다는 점은 보여주지만, 한 query 안에서 정책을 합성해야 한다는 근거는 아니다.

## 3. 판정 기준

- `K`: 동시에 참일 수 없는 독립 atomic conflict unit 수
- `H`: 해당 unit들을 해결하는 데 필요한 서로 다른 core operator 수
- 여러 문서, 답 후보, stance, 반복 인용을 그대로 `K`로 세지 않음
- 같은 answer slot의 일반 주장과 세부 수치를 별도 unit으로 과분해하지 않음
- 보완 관계, 단순 정보 부족, 관련 없음, 중복은 core conflict에서 제외
- `H`는 확정된 unit의 operator set에서 파생하고 `H≤K`를 강제

## 4. 실제 실행 방식과 계획 대비 변경

원 계획은 LLM 초벌, 인간 A 전수 검토, 인간 B blind audit과 adjudication을 상정했다. 시간 제약에 따라 실제 파일럿은 다음처럼 축소했다.

- 판정자: OpenAI Codex interactive agent, GPT-5 기반
- 정확한 내부 deployment checkpoint: 제공되지 않음
- protocol: `strict-kh-direct-v1`
- 질문, answer cluster, 연결 evidence snippet을 직접 읽어 판정
- 인간 검토와 human-human IAA 없음
- local open-source model 결과를 최종 판정에 사용하지 않음

따라서 결과는 연구 방향을 결정하는 exploratory evidence이며, gold annotation이나 재현 가능한 benchmark 판정으로 주장하지 않는다.

## 5. 품질 확인과 수정 사례

초기 NatConfQA 한 사례를 `K=2,H=2` 후보로 보았으나 원 evidence를 재검토한 결과 동일한 temperature–transmission answer slot의 중첩 설명이었다. 독립 unit이 아니므로 `K=1,H=1, CONDITION`으로 수정했다. 이 사례는 strict atomicity가 없으면 복합 충돌을 쉽게 과대계상할 수 있음을 보여준다.

최종 산출물에 대해 다음을 확인했다.

- 202개 unique instance, 누락·중복 없음
- `H≤K` 및 operator-set–`H` 일치
- 최종 표와 JSONL의 수량 일치
- 전체 연구 테스트 107개 통과

## 6. 해석

### 지지되는 주장

1. 기존 자연 conflict QA 데이터는 대부분 하나의 answer slot을 중심으로 구성된다.
2. atomic conflict 자체에는 여러 해결 연산이 존재한다.
3. strict `K/H` 주석에서는 answer cluster 수나 문서 수를 conflict 수로 사용할 수 없다.
4. 기존 검색 자료만으로 query-level operator composition의 자연 prevalence를 주장하기 어렵다.

### 지지되지 않는 주장

1. 자연 검색에서 `K>1,H>1`이 흔하다.
2. 같은 `K`에서 `H` 증가가 기존 모델 성능을 낮춘다.
3. PCCR 같은 조합적 해결 파이프라인이 현재 데이터에서 필요하다.

## 7. 연구 결정

- 검색 문서 prevalence를 중심 주장으로 사용하지 않는다.
- 기존 검색 기반 파일럿 2는 실행하지 않는다.
- `K/H` formulation은 폐기하지 않고 더 자연스러운 누적 conflict 환경인 long-term memory로 적용 가능성을 검증한다.
- memory로 이동해도 multi-slot query를 인공적으로 붙인다는 비판은 남으므로, 같은 persona·하나의 사용자 목표·원 memory 보존을 구성 기준으로 둔다.
- memory 파일럿에서도 자연 후보와 `H` 효과가 확보되지 않으면 compositional conflict 주장을 중단하거나 benchmark coverage study로 축소한다.
