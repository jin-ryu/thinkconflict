# 03 · Query-Conditioned Global Conflict from Documents

실제 RAG 문서에서 질문 관련 claim, 개체, 시간, 조건과 예외를 복원하는 **semantic compilation**의 불확실성이 고차 충돌 추론에 어떻게 전파되는지 분석하고, 여러 가능한 의미 구조를 공동 추론하는 source-grounded conflict reasoning 방법을 연구한다.

작성일: 2026-08-31  
상태: ACL main 연구 방향 재구성 / ProofWriter NatLang dry run 구조 검증 PASSㆍ의미 검수 전

문서가 많아졌으므로 먼저 [문서 안내](docs/README.md)를 본다. 현재 판단에 필요한 핵심은 [Pilot A 계획서](docs/pilot_a_plan.md)와 [데이터셋 선택 요약](docs/dataset_decision.md) 두 개다.

Pilot A의 ProofWriter 도입 가능성은 [feasibility audit](docs/proofwriter_feasibility.md), 20개 변환 결과는 [NatLang dry-run report](data/pilot_a/proofwriter_natlang_dry_run_report.md), 재현 절차와 공개 제한은 [data README](data/README.md)에 기록한다. 기존 MAGIC 구성 결과는 감사 이력으로만 보존한다.

데이터 품질 감사에서 MAGIC의 relation path와 본 연구의 엄격한 proof certificate 사이의 불일치가 발견됐다. 이에 Pilot A의 controlled diagnostic core는 ProofWriter의 검증된 multi-hop proof를 문서 간 충돌로 변환하는 방식으로 바꾸고, MAGIC은 외부 전이ㆍ선행연구 비교용으로만 사용한다. ProofWriter는 원래 충돌 데이터셋이 아니라는 점과 구체적인 변환ㆍ검증 규칙은 [Pilot A 계획서](docs/pilot_a_plan.md)를 따른다. 기존 감사의 상세 내용은 [MAGIC data quality audit findings](docs/data_quality_audit_findings.md)에 보존한다.

## 1. 최종 연구 방향

### 가제

**From Documents to Global Conflict: Query-Conditioned Reasoning under Semantic Compilation Uncertainty**

대안 제목:

- **When Conflict Is Lost in Translation: Source-Grounded Higher-Order Reasoning for RAG**
- **Beyond Atomic Facts: Query-Conditioned Global Consistency over Retrieved Documents**
- **Compiling Evidence without Losing Conflict: Joint Semantic and Consistency Reasoning for RAG**

### 한 줄 주장

> 기존 전역 일관성 방법은 비교할 사실 단위가 이미 주어졌다고 가정하지만, 실제 RAG에서는 원문을 claimㆍ시간ㆍ조건ㆍ개체 관계로 변환하는 semantic compilation 오류가 고차 충돌을 먼저 지운다. 우리는 이 오류를 계층별로 측정하는 벤치마크와 단일 hard graph 대신 복수의 의미 해석을 보존하며 충돌 proof를 공동 탐색하는 방법을 제안한다.

## 2. 왜 기존 03 계획을 그대로 사용하지 않는가

기존 계획의 중심이었던 다음 주장은 이미 직접 선행연구와 크게 겹친다.

- pairwise 검사는 global consistency를 보장하지 못한다.
- 자연어 fact 집합에서 minimal inconsistent/unsatisfiable subset(MIS/MUS)을 찾는다.
- noisy LLM oracle을 이용해 효율적으로 불일치 부분집합을 탐색한다.

[Foundations of Global Consistency Checking with Noisy LLM Oracles](https://arxiv.org/abs/2601.13600)는 이 문제를 형식화하고 adaptive divide-and-conquer MUS 탐색과 hitting-set repair를 제안한다. 따라서 MIES/MUS 자체를 핵심 신규성으로 주장하지 않는다.

또한 다음 인접 연구를 명시적으로 인정한다.

| 연구 | 선점한 부분 | 본 연구에 남은 경계 |
|---|---|---|
| [MAGIC](https://aclanthology.org/2025.findings-emnlp.466/) | KG 기반 멀티홉 문맥 간 충돌, IDㆍLOC 평가 | 실제 문서에서 의미 구조를 복원하는 오류와 query-conditioned proof는 다루지 않음 |
| [Contradiction Detection in RAG Systems](https://arxiv.org/abs/2504.00180) | 세 문서 조건부 모순 | 합성 유형 평가 중심이며 source-grounded semantic compilation은 없음 |
| [Global Consistency with Noisy LLM Oracles](https://arxiv.org/abs/2601.13600) | 자연어 fact 집합의 global consistency, MUS와 repair | 입력 fact unit이 주어진 뒤의 subset search가 중심; 원문 문서→claim/조건 복원은 범위 밖 |
| [ArbGraph](https://arxiv.org/abs/2604.18362) | 원자 claim support/contradiction graph와 중재 | hard claimㆍpairwise edge 오류의 전파와 복수 semantic parse 공동 추론은 없음 |
| [Claim-Selective Certification](https://arxiv.org/abs/2605.21949) | 의료 RAG의 claim별 certificate와 행동 선택 | 특정 도메인ㆍclaim action 중심; higher-order proof 및 compilation uncertainty와 다름 |
| HyperRAGㆍOKH-RAGㆍHyCE-RAGㆍMEGRAG | hypergraph와 멀티홉 evidence path | 보완 증거 기반 QA가 중심이며 conflict-specific semantic uncertainty는 다루지 않음 |

## 3. ACL main 수준의 핵심 문제

### 3.1 Atomic-fact assumption

기존 global consistency 알고리즘에 다음과 같은 사실 집합이 정확히 주어지면 MUS 탐색은 잘 정의된다.

```text
c1: Service S is available only to EU residents unless an exemption applies.
c2: Mina legally uses Service S.
c3: Mina is not an EU resident.
c4: Mina has no exemption.
```

하지만 실제 RAG 입력은 다음과 같은 원문 문서다.

- 조건이 여러 문장에 흩어져 있다.
- “only”, “unless”, “as of”, “subsidiary”, “formerly” 같은 scope가 관계 의미를 바꾼다.
- 서로 다른 표기가 같은 개체인지 판단해야 한다.
- 질문과 무관한 불일치는 답변에 영향을 주지 않을 수 있다.
- 한 문장을 여러 방식으로 원자화할 수 있다.

즉 실제 병목은 MUS 탐색 이전의 `documents → semantic facts` 변환일 수 있다.

### 3.2 Query-conditioned conflict

문서 집합의 전역 모순 여부와 RAG 질문에 대한 답변 관련 충돌은 다르다.

- 질문과 무관한 주제의 모순은 현재 답변에 영향을 주지 않는다.
- 동일 문서도 `현재 시점` 질문과 `2022년 당시` 질문에서 충돌 여부가 다르다.
- 조건이나 관할을 묻는 질문은 단순 사실 질문보다 다른 증거 조합을 필요로 한다.

본 연구는 `Consistent(D)`가 아니라 `Conflict(D, q, t, scope)`를 예측한다.

### 3.3 Higher-order conflict as a test bed, not the sole novelty

고차 충돌은 semantic compilation 오류를 드러내기 좋은 시험대다. 하나의 조건ㆍ정렬ㆍ중간 claim이 빠지면 전체 충돌이 사라지기 때문이다. 그러나 “고차 충돌을 처음 제안했다”거나 “MUS를 처음 찾았다”는 주장은 하지 않는다.

## 4. 연구 질문

### RQ1. 실제 병목은 subset search인가 semantic compilation인가?

- 동일한 알고리즘에 raw documents, predicted claims, gold claims, gold proof graph를 단계적으로 제공한다.
- 성능 회복량으로 document understanding, claim compilation, proof search의 오류를 분해한다.

**H1:** 고차 충돌의 end-to-end 오류 중 가장 큰 비중은 MUS 탐색보다 claimㆍconditionㆍalignment compilation에서 발생한다.

### RQ2. 질문 조건화가 불필요한 충돌과 답변 관련 충돌을 구분하는가?

**H2:** query-agnostic global consistency 방법은 동일 문서의 질문 twin에서 과잉 탐지하거나 필요한 충돌을 누락하며, query-conditioned 모델은 이 오류를 줄인다.

### RQ3. 하나의 hard semantic graph가 오류를 증폭하는가?

**H3:** top-1 claim parse와 hard NLI edge를 사용하는 파이프라인보다 복수 semantic hypothesis를 보존하는 공동 추론이 entity/time/condition ambiguity 아래에서 높은 proof recall과 calibration을 보인다.

### RQ4. Source-grounded proof가 정확도 이상의 신뢰성을 제공하는가?

**H4:** 원문 span에서 각 중간 claim까지 역추적 가능한 proof 제약은 ID 성능을 유지하면서 invalid rationale과 unsupported conflict를 감소시킨다.

## 5. 과제 정의

입력은 질문 `q`, 검색 문서 집합 `D={d_1,...,d_n}`, 선택적 질의 시점 `t_q`다.

출력은 다음과 같다.

```json
{
  "answer_relevant_conflict": true,
  "conflict_type": "higher_order_conditional",
  "answer_space": ["claim_a", "claim_not_a"],
  "evidence_set": ["d1:s2", "d2:s1", "d3:s4"],
  "semantic_claims": [],
  "proof_steps": [],
  "assumptions": {
    "entity_links": [],
    "time_scope": null,
    "conditions": []
  },
  "confidence": 0.0,
  "recommended_action": "surface_conflict"
}
```

### Gold representation의 네 계층

1. **Source layer**: 문서와 근거 span
2. **Semantic layer**: 정규화 claim, entity, time, modality, condition, exception
3. **Proof layer**: 중간 결론과 hyper-relational inference step
4. **Decision layer**: 질문 관련 충돌, 답변 후보, 표출ㆍ추가 검색ㆍ기권 행동

이 계층 구조를 이용해 단일 end-to-end 점수뿐 아니라 오류가 처음 발생한 지점을 평가한다.

## 6. 데이터셋: Q-GloCo

잠정 이름은 **Q-GloCo(Query-conditioned Global Conflict)**다.

### 6.1 최종 목표 규모

| 구성 | 목표 수량 | 목적 |
|---|---:|---|
| controlled source-grounded instances | 1,200 | factor별 인과적 비교 |
| 신규 natural multi-hop conflict | TBD | 수집·주석 타당성 확인 후 외적 타당성 평가 |
| hard no-conflict controls | 500 | 과잉 탐지 측정 |
| 합계 | 1,700 + TBD | ACL 본실험 |

최종 수량은 파일럿의 주석 합의도와 효과 크기에 따라 조정한다.

### 6.2 충돌 구조

- direct pairwise
- implicit multi-hop pairwise
- pairwise-consistent higher-order
- temporal/scope-conditioned
- apparent conflict resolved by condition or entity distinction
- irrelevant global conflict but answer-relevant consistency
- fully consistent hard negative

### 6.3 독립 조작 요인

- semantic arity
- proof hop
- source 문서 수
- 문맥 길이
- distractor 수
- entity alias ambiguity
- temporal distance와 validity interval
- condition/exception depth
- evidence order

hop과 길이, arity와 문서 수를 가능한 한 독립적으로 조작한다.

### 6.4 Query twins

동일한 문서 집합에 서로 다른 질문을 붙여 conflict label이 바뀌는 twin을 만든다.

```text
Documents: 과거 정책, 개정 정책, 지역별 예외 조항
q1: 2021년 지역 A에서 적용된 규정은?       → conflict 없음
q2: 현재 모든 지역에 적용되는 규정은?      → answer-relevant conflict
q3: 정책 담당자의 이름은?                  → 문서에 충돌이 있어도 질문과 무관
```

이 설계가 query-agnostic global consistency 연구와의 가장 중요한 차별점이다.

### 6.5 데이터 원천

- ProofWriter의 검증된 proof를 multi-document conflict로 변환한 통제 사례
- 엄격한 proof audit를 통과한 MAGIC 사례는 외부 전이ㆍ선행연구 비교에만 사용
- WikiContradict는 자연 충돌 calibration 후보일 뿐 multi-hop conflict 데이터로 세지 않음
- ConfRAG는 자연 상충 답변 calibration 후보일 뿐 multi-hop proof를 보장하지 않음
- 신규 자연 사례는 최소 두 문서, 2개 이상 추론 step, single-document insufficiency와 전체 source-grounded proof를 독립 주석
- 자연 multi-hop 후보 원천은 별도 수집 타당성 파일럿에서 결정

실제 웹 사례는 자동 생성 결과를 그대로 사용하지 않고 독립 주석자가 source span과 proof를 확인한다.

### 6.6 Split

- entity-disjoint
- source-domain-disjoint
- relation-composition-disjoint
- template-disjoint
- temporal extrapolation
- arity/hop extrapolation
- source/evidence-novel split

## 7. 제안 방법: LatticeConf

잠정 방법명은 **LatticeConf**다. 핵심은 문서를 한 개의 확정된 claim graph로 변환하지 않고, 질문과 관련된 복수 semantic compilation을 lattice로 유지한 채 source-grounded conflict proof를 공동 탐색하는 것이다.

### 7.1 Semantic hypothesis lattice

각 source span `x_i`에 대해 하나의 claim만 고르는 대신 상위 `K`개의 구조화 해석을 유지한다.

```text
z_i = (subject, relation, object, time, modality, condition, exception)
Z_i = {z_i^1, ..., z_i^K}
```

서로 다른 span의 entity alignment와 time/scope compatibility도 확률 변수로 둔다.

### 7.2 Query-conditioned pruning

질문에서 필요한 answer variable, 시간, 대상과 관할을 추출하고, 관련 없는 semantic branch를 제거한다. 단순 relevance score가 아니라 해당 branch가 가능한 answer proof에 참여할 수 있는지를 기준으로 한다.

### 7.3 Joint proof search

후보 proof `P`는 source span, semantic hypothesis, inference hyperedge를 연결하고 마지막에 양립 불가능한 결론 쌍으로 끝난다.

개념적인 점수는 다음과 같다.

```text
Score(P, Z | D, q)
  = grounding(Z, D)
  + query_relevance(Z, q)
  + step_validity(P, Z)
  + terminal_conflict(P)
  - complexity(P)
  - unsupported_assumption(P)
```

top-1 graph에서 proof를 찾는 대신 상위 semantic parse와 proof를 함께 탐색한다. 실제 구현은 constrained beam search 또는 A* 형태를 우선 검토한다.

### 7.4 Source-grounded verifier

각 proof step을 독립적으로 검사한다.

- source span이 semantic claim을 지지하는가?
- entityㆍtimeㆍcondition alignment가 허용되는가?
- 전제에서 중간 결론이 도출되는가?
- 최종 결론들이 같은 질문 조건 아래 실제로 양립 불가능한가?

최종 설명의 유창성을 LLM judge 하나로 평가하지 않는다.

### 7.5 Uncertainty-aware decision

상위 proof들이 동일한 결론에 수렴하는지, semantic branch마다 판단이 달라지는지를 이용해 다음 행동을 선택한다.

- answer normally
- surface conflict with attributed alternatives
- retrieve missing condition
- ask for temporal/scope clarification
- abstain

certificate나 abstention 자체를 신규성으로 주장하지 않고, **semantic compilation uncertainty가 행동 결정까지 보존되는 것**을 기여로 둔다.

## 8. 학습 목표

전체 손실은 다음 구성으로 설계한다.

```text
L = L_span
  + λ1 L_semantic_claim
  + λ2 L_alignment
  + λ3 L_proof_step
  + λ4 L_conflict
  + λ5 L_action
```

- `L_span`: 근거 span 선택
- `L_semantic_claim`: 구조화 claim 복원
- `L_alignment`: entity/time/condition 정렬
- `L_proof_step`: gold proof edge와 중간 결론
- `L_conflict`: answer-relevant conflict 판정
- `L_action`: 답변ㆍ표출ㆍ검색ㆍ명료화ㆍ기권

모든 요소를 처음부터 학습하지 않는다. 파일럿 이후 가장 큰 오류 구간에 모델링 기여를 집중한다.

## 9. 필수 기준선

### 충돌 탐지

1. pairwise NLI + OR aggregation
2. pairwise LLM judge + aggregation
3. full-context direct prompt
4. full-context chain-of-thought
5. claim extraction → hard pairwise graph
6. ArbGraph 계열 atomic-claim graph

### Global consistency

7. exhaustive subset consistency search(작은 arity oracle)
8. Foundations adaptive divide-and-conquer MUS
9. hitting-set repair 기반 판정

### 구조화ㆍoracle 진단

10. predicted claims
11. gold claims
12. gold entity/time/condition alignment
13. gold proof graph

### 제안 방법 ablation

14. top-1 semantic graph
15. hypothesis lattice without joint search
16. joint search without verifier
17. joint search without query conditioning
18. full LatticeConf

## 10. 평가

### 10.1 최종 과제

- answer-relevant conflict macro F1와 AUPRC
- answer accuracy / attributed multi-answer quality
- no-conflict false positive rate
- 행동 결정 utility와 risk--coverage

### 10.2 Sourceㆍsemantic 계층

- evidence span F1
- claim tuple exact/slot F1
- entity alignment F1
- time/scope/condition accuracy
- semantic compilation calibration

### 10.3 Proof 계층

- proof edge F1
- intermediate conclusion accuracy
- fully valid proof rate
- unsupported-assumption rate
- 최소/충분 evidence-set F1

MUS/MIES 지표는 포함하지만 논문의 유일한 중심 지표로 사용하지 않는다.

### 10.4 강건성과 효율

- evidence-order flip
- hop/arity/condition depth curve
- semantic edge corruption curve
- source/evidence-novel generalization
- 동일 전체 토큰ㆍ호출ㆍ지연ㆍGPU 예산

## 11. 핵심 분석: Semantic Compilation Gap

본 논문의 중심 분석값은 다음 단계별 성능 차이다.

```text
Raw documents
  → Gold spans
    → Gold semantic claims
      → Gold alignments
        → Gold proof graph
```

- `span gap`: gold span 제공으로 회복되는 성능
- `claim gap`: gold claim 제공으로 회복되는 성능
- `alignment gap`: gold entity/time/condition 정렬로 회복되는 성능
- `search gap`: gold proof graph로 회복되는 성능

H1이 맞다면 claim/alignment gap이 search gap보다 커야 한다. 이 결과가 확인되어야 LatticeConf의 설계가 경험적 근거를 갖는다.

## 12. ACL main의 예상 기여

1. **새 문제 설정**: 문서 집합의 일반 일관성이 아닌 query-conditioned answer-relevant global conflict
2. **계층적 벤치마크**: source → semantic claim → proof → decision의 gold 구조와 query twin
3. **새 진단 결과**: 고차 충돌 실패를 subset search와 semantic compilation 오류로 계층적으로 분해
4. **새 방법**: 하나의 hard graph 대신 복수 semantic compilation과 conflict proof를 공동 탐색
5. **신뢰성 평가**: source-grounded proof validity, calibration, selective action, 동일 예산 비교

다섯 기여를 독립적으로 나열하지 않고 다음 하나의 서사로 통합한다.

```text
기존 MUS/graph 방법은 atomic-fact assumption에 의존한다
→ 실제 문서에서는 semantic compilation이 충돌 구조를 먼저 손상한다
→ Q-GloCo가 오류 계층과 질문 조건화를 측정한다
→ LatticeConf가 복수 해석과 proof를 공동 추론해 이 병목을 완화한다
```

## 13. ACL main이 되기 위한 성공 조건

- 기존 Foundations MUS 기준선보다 raw-document 조건에서 명확한 개선
- gold-claim oracle에서는 기존 MUS가 강하지만 raw-document에서 붕괴한다는 진단 결과
- query twin에서 query-agnostic 방법의 체계적 실패
- 별도 구축·검증한 natural multi-hop conflict subset에서도 controlled 결과의 방향 재현
- proof validity와 calibration 개선이 단순 추가 토큰으로 설명되지 않음
- 최소 두 모델 계열 또는 encoder/LLM 조합에서 방법 효과 재현
- 높은 사람 주석 합의와 source-grounded proof 공개

단순 ID 정확도 1~2%p 개선만으로는 성공으로 보지 않는다.

## 14. 주요 리스크

| 리스크 | 치명도 | 대응 |
|---|---:|---|
| Foundations의 RAG 응용으로만 보임 | 매우 높음 | query twin, document semantic compilation, 계층별 oracle gap, joint lattice를 중심에 둠 |
| 데이터가 합성 논리 퍼즐처럼 보임 | 매우 높음 | 실제 웹 300개, source-domain OOD, 사람 proof 검증을 필수화 |
| 방법이 복잡한 파이프라인에 그침 | 높음 | top-1 graph가 아닌 latent semantic/proof joint inference를 기술적 중심으로 고정 |
| gold proof 비용이 과도함 | 높음 | 파일럿 IAA 통과 후 관계 범위를 제한하고 active review 사용 |
| 자연어 논리의 모호성 | 높음 | 시간ㆍ조건ㆍ개체 전제를 명시하고 adjudication 가능한 사례만 포함 |
| 강한 long-context 모델이 이미 해결 | 중간 | 파일럿 go/no-go 조건으로 조기 검증 |
| 추가 연산이 성능 원인 | 높음 | 동일 토큰ㆍ호출ㆍ지연 예산 통제 |
| 연구 범위 과대 | 높음 | 파일럿에서 가장 큰 gap 하나에 최종 방법을 집중 |

## 15. 명시적으로 하지 않을 주장

- 멀티홉 충돌을 처음 연구했다.
- pairwise 검사의 전역 한계를 처음 밝혔다.
- 자연어에서 MUS/MIES를 처음 탐색했다.
- conflict certificate 또는 abstention을 처음 제안했다.
- hypergraph를 사용했다는 사실만으로 신규성이 있다.
- 통제 데이터의 빈도가 실제 웹 prevalence를 나타낸다.
- 알고리즘 수렴성이 자연어 사실성을 보장한다.

## 16. 파일럿과 본연구의 분리

파일럿은 논문의 축소판이 아니라 다음 네 가지를 결정하는 go/no-go 실험이다.

1. raw-document와 gold-claim 사이에 충분한 compilation gap이 존재하는가?
2. query twin에서 질문 조건화 효과가 존재하는가?
3. 사람 주석자가 semantic claim과 proof에 안정적으로 합의하는가?
4. 강한 long-context 모델도 고차 충돌에서 실패하는가?

세부 사전 계획은 [Pilot A 계획서](docs/pilot_a_plan.md)에 분리한다.

## 17. 본연구 진행 단계

### Phase 1 · Pilot decision

- 별도 Pilot A 실행
- 데이터ㆍ모델ㆍ방법 구현 확대 여부 결정

### Phase 2 · Benchmark construction

- Q-GloCo 2,000개 구축
- 독립 주석과 adjudication
- artifactㆍleakageㆍOOD audit

### Phase 3 · Diagnostic paper core

- semantic compilation gap 분석
- query-conditioning과 higher-order factor 분석
- 강한 기존 MUS/graph/long-context 기준선 비교

### Phase 4 · Method

- 파일럿에서 확인된 최대 병목에 맞춰 LatticeConf 구현
- lattice, joint proof search, verifier ablation

### Phase 5 · ACL package

- 자연 웹 일반화
- 동일 예산ㆍ강건성ㆍcalibration 실험
- 데이터ㆍ코드ㆍ주석 지침 공개

## 18. 예상 논문 구성

1. Introduction
2. Related Work
   - RAG knowledge conflict
   - global consistency and MUS
   - semantic parsing/claim extraction uncertainty
   - graph and hypergraph RAG
3. Query-Conditioned Global Conflict
4. Q-GloCo Benchmark
5. Where Does Global Conflict Reasoning Fail?
6. LatticeConf
7. Experiments
8. Semantic Compilation and Robustness Analysis
9. Limitations and Ethics
10. Conclusion

## 19. 관련 문서

- [Pilot A 사전 계획](docs/pilot_a_plan.md)
- [기존 연구로 검증된 사실과 남은 공백](docs/prior_validated_findings.md)
- [멀티홉 충돌 연구 지형](../../literature/analysis/09_multihop_conflict_landscape.md)
- [문헌 분석 종합](../../literature/analysis/README.md)
- [MAGIC 한국어 LaTeX](<../../literature/papers/MAGIC; A Multi-Hop and Graph-Based Benchmark for Inter-Context Conflicts in Retrieval-Augmented Generation/main_ko.tex>)
- [Contradiction Detection in RAG Systems 한국어 LaTeX](<../../literature/papers/Contradiction Detection in RAG Systems Evaluating LLMs as Context Validators for Improved Information Consistency/acl_latex_ko.tex>)
