# Memory conflict 관련 연구 조사: 2025-06 ~ 2026-08

> 작성일: 2026-08-28
> 범위: LLM agent의 장기 memory conflict 벤치마크, 해결 방법·시스템, 인접 연구(다중 질문 저하, 제약 합성, 순서 민감성)
> 검증: arXiv abstract/HTML, GitHub README, 공식 docs 기준. `[미확인]`은 2차 자료만 있는 항목
> 선행 문서: [dataset_evidence.md Part II](dataset_evidence.md#part-ii-장기-메모리-conflict)는 MemConflict, TANGLE, STALE, Memora, HaluMem, LongMemEval, MemoryAgentBench, Mem2ActBench를 다룬다. 이 문서는 그 이후·그 외 논문과 방법론을 보강한다.

---

## 0. 결론

우리 각도는 다음이다.

> 하나의 사용자 요청이 여러 개의 독립 memory conflict unit을 요구하고, unit마다 서로 다른 resolution policy(latest-wins / conditionalize / verify-prefer / ask)를 적용해 하나의 응답으로 합성해야 한다.

조사 결과 **이 각도를 그대로 다룬 논문은 없다.** 기존 연구는 두 부류로 나뉜다.

1. conflict를 유형화하되 **query당 하나씩** 평가: MemConflict, TANGLE, STALE, Selective-QA, MemSyco-Bench, A-TMA, HorizonBench, MCB
2. 여러 memory를 한 답으로 합성하되 **policy는 하나**(latest-wins 또는 obsolete 배제): Memora, MemoryAgentBench FC-MH, Mem2ActBench, IBA-Bench, CAR

그러나 2026년 5~8월에 인접 논문이 집중적으로 나왔고, 다음 넷이 결합되면 공백이 닫힌다.

| 위험 | 논문 | 이미 한 것 | 아직 안 한 것 |
|---|---|---|---|
| 높음 | CAR / Deterministic Recipe 2606.01435 | 분해 → hop별 해결 → chaining. future work에 "question-type별 handler routing" 명시 | policy가 freshness 하나. unit별 policy 선택 없음 |
| 높음 | IBA-Bench 2608.02171 | instance의 80%가 제약 3개 이상, 장기·단기 state 모순 포함 | conflict 유형·policy 없음, 해결은 암묵적 recency |
| 중간 | CAAP (TANGLE) 2608.13921 | conflict 유형 → action 6종 routing | instance당 conflict 1개, action 1개 |
| 중간 | StateMemBench 2608.19652 | 한 대화에 서로 다른 mode의 trap 3개(compound) | query 하나가 여러 thread를 걸치는지 미확인, policy는 supersession 하나 |
| 중간 | CUPMem (STALE) 2605.06527 | item마다 KEEP/STALE/REPLACE/UNKNOWN 판정 후 status별 readout | write-time, schema 의존, label은 validity이지 resolution strategy가 아님 |

우리가 지켜야 할 차별점은 **read-time, query-conditioned, per-conflict-unit policy 선택과 합성**, 그리고 **한 query에 서로 다른 유형의 conflict가 섞인 benchmark**다.

---

## 1. 유형화된 conflict 벤치마크: query당 conflict 하나

### 1.1 MemConflict (2605.20926, 2026-05)

- 유형: Dynamic(나중 true update가 이전 state를 대체), Static(나중 false contradiction이 안정된 사실을 덮어쓰면 안 됨), Conditional(조건별로 서로 다른 memory가 유효)
- 데이터: Persona Hub → LLM profile → 48개월 timeline → conflict 삽입 → distractor → 대화 생성 + 인간 검증. instance 12개, instance당 약 52 session, 2,349 turn, 204K token, 124 query
- query 형태: **conflict 하나, attribute 하나.** 본문: "guarantees a unique maximizer for each query"
- 시스템 결과(answer accuracy): LangMem dynamic 0.50 / static 0.19 / conditional 0.16, Memobase 0.41 / 0.42 / 0.24, MemOS 0.38 / 0.44 / 0.84, Mem0 0.12 / 0.19 / 0.77, Letta 0.40 / 0.22 / 0.84, A-Mem 0.36 / 0.26 / 0.71
- 발견: retrieval 성공과 answer 정확도가 자주 어긋남. history 길이, distractor, implicit query, conflict distance가 성능을 낮춤
- 우리와의 관계: taxonomy가 우리 세 policy와 1:1 대응. **시스템별 강점이 유형마다 반대**라는 점이 global-policy collapse의 시스템 수준 증거다. 어떤 시스템도 세 유형을 동시에 잘하지 못한다.

### 1.2 TANGLE (2608.13921, 2026-08)

- 유형: CPC(context-partitioned), BOC(behavior-oscillation), SCC(source-contradiction). 모두 단일 정답으로 환원 불가
- 데이터: 541 instance, 40 persona, 46 life aspect, instance당 core conflict memory 8~11개 + distractor 6개. pipeline track 2,580 multi-session 대화
- query 형태: **instance당 conflict 하나.** "Entangled"는 하나의 conflict 안의 context·time·source 얽힘을 뜻하고 multi-conflict가 아님
- action: commit, conditionalize, clarify, verify, defer, reversible_trial. 0~4점 5차원 평가
- 발견: 최고 모델도 20점 만점에 15점 미만. 인식(perception)은 되는데 action calibration과 clarification이 약함. write-time 시스템이 conflict를 보존하는 비율: Letta 91.7%, Mem0 69.1%, A-Mem 47.0%, MemOS 46.2%
- 우리와의 관계: policy 어휘(conditionalize / clarify / verify / defer)를 빌려 쓴다. "write-time pipeline이 conflict를 파괴한다"는 수치가 read-time resolver의 근거다.

### 1.3 STALE (2605.06527, 2026-05)

- 유형: Type I co-referential(같은 attribute의 암시적 갱신), Type II propagated(관련 attribute 변화가 다른 belief를 무효화)
- 데이터: 400 expert-validated scenario, 1,200 query, 최대 150K token
- query 형태: **scenario당 conflict pair 하나**, probe 3개(state resolution, premise resistance, implicit policy adaptation)
- 결과: Gemini-3.1-pro 55.2%, 대부분의 memory framework 10% 미만. CUPMem 8.7% → 68.0%
- 우리와의 관계: `D>0` 축. 단 2026년 8월에 StateMem, HiGram, StateAuditor가 propagation을 채웠으므로 `D` 방향은 더 이상 공백이 아니다.

### 1.4 Selective QA over Conflicting Multi-Source Personal Memory (2605.30087, 2026-05)

- 5개 evidence stream(stale profile, optimistic planner, biased self-report, sparse objective log, noisy device log)의 신뢰도 상충. 34,560 instance
- query 형태: latent attribute 하나를 여러 source로 관측. slot 하나
- 결과: 학습된 fusion resolver 80.3% vs 최고 LLM 70.0%. abstain 포함 selective accuracy 85.3% at 78.3% coverage
- 관계: "unreliable memory"를 source-conditioned reliability + abstain으로 정의한 인용처

### 1.5 MemSyco-Bench (2607.01071, 2026-07)

- memory 유발 sycophancy. task 5종: Objective Fact Judgment(preference memory 억제), Contextual Scope Control(적용 범위 준수), Memory-Evidence Conflict(verified evidence 우선), Valid Memory Selection(갱신된 preference 중 현재 유효값), Personalized Memory Use
- query 형태: task당 policy 하나, task 분리
- 결과: memory 추가 시 Qwen3-8B 사실 판단 49.1% → 26~36%. 오류의 61~62%가 retrieval 성공 후 발생. **caution 지시가 conflict task는 +31.6%, personalization은 −13~−21%**
- 관계: prompt 수준 global policy가 다른 task를 망치는 직접 증거

### 1.6 그 외 단일 slot 벤치마크

| 논문 | ID | 시기 | 핵심 | query 형태 |
|---|---|---|---|---|
| A-TMA / LTP | 2607.01935 | 26.07 | old/current/transition "ghost memory" 혼입. 800 probe. 질문이 요구하는 state를 따라야 함 | state pair 하나 |
| HorizonBench | 2604.17283 | 26.04 | life-event 의존 그래프로 preference 변화. 4,245 item. 최고 Claude-opus-4.5 52.8%, 오답의 38.2%가 pre-evolution 값 | preference 하나 |
| DynamicMem | 2606.22877 | 26.06 | 15개월 multi-app 활동, 3,634 task. 실패의 93% 이상이 retrieval | field별 독립 채점 |
| BEAM | 2510.27246 | 25.10, ICLR'26 | 10M token, contradiction resolution 평균 약 0.03으로 최저 | revision pair 하나 |
| MemTrace | 2606.17328 | 26.06 | HaluMem을 835 knowledge point로 변환, 15,422 row. 실패 시 evidence는 retrievable이었던 경우가 10배 | point 하나 |
| Supersede | 2606.27472 | 26.06 | LongMemEval KU: full-context 92% vs self-maintained 77%. 대화 24배 길어지면 68% → 28% | fact 하나 |
| PersonaMem-v3 | 2608.21381 | 26.07 | 실제 engagement history 1M+, 언제 personalization을 자제할지 | `[미확인]` |
| AlpsBench | 2603.26680 | 26.03 | WildChat 2,500 sequence, extraction/updating/retrieval/utilization | update 하나 |
| BenchPreS | 2603.16557 | 26.03 | 저장된 preference의 조건부 적용. Misapplication Rate. "모델은 preference를 전역 규칙처럼 취급" | preference 하나 |
| MCB: Remember/Verify/Ask | 2608.19564 | 26.08 | write 결정 persist/ephemeral/verify/clarify. 모델은 verify는 하지만 ask는 거의 안 함 | scenario당 action 하나 |
| BeliefShift | 2603.23848 | 26.03 | 사용자 입장 변화 추적 | belief 하나 |
| RPEval, OP-Bench, HUSH-Bench | 2601.16621, 2601.13722, 2606.06055 | 26.01~06 | memory를 쓰지 말아야 할 때 | memory 하나 |

---

## 2. 여러 memory를 합성하지만 policy가 하나인 벤치마크

| 논문 | ID | 시기 | 합성 규모 | policy | 우리와의 차이 |
|---|---|---|---|---|---|
| Memora | 2604.20006 | 26.04, ACL'26 Findings | quarterly 질문이 평균 28.4 session(최대 309) 통합. FAMA로 obsolete 재사용 벌점 17.8~29.5% | obsolete 배제 하나 | 유형 없음 |
| MemoryAgentBench FC-MH | 2507.05257 | ICLR'26 | 여러 updated fact를 chaining. 기존 최고 7%, CAR 27~41% | latest by serial | 백과사전 사실, policy 하나 |
| Mem2ActBench | 2601.19935 | 26.01 | 여러 fact를 tool argument로 합성. 91.3%가 memory 없이는 불가 | latest | conflict 구축 중 해소 |
| IBA-Bench | 2608.02171 | 26.08 | 6,962 instance, 80%가 제약 3개 이상. 장기 attribute와 단기 state가 모순 가능 | 암묵적 recency | **유형·policy 없음. 가장 가까운 구조** |
| CIMemories | 2511.14937 | 25.11 | attribute 100개 이상에 각각 다른 disclosure policy. GPT-5 위반 0.1%(1 task) → 9.6%(40 task) | attribute별 disclosure | privacy. "slot마다 다른 policy 합성"의 구조적 선례 |
| RECON | 2607.16716 | 26.07 | case file에서 cascading invalidation + source conflict. 최고 22.4% | | 문서, 개인 memory 아님 |

---

## 3. 해결 방법과 시스템

### 3.1 Write-time: production 시스템

| 시스템 | ID / 출처 | conflict 처리 | policy | item별 | 비고 |
|---|---|---|---|---|---|
| Mem0 / Mem0^g | 2504.19413 | fact별 ADD/UPDATE/DELETE/NOOP를 LLM이 선택. graph는 invalid 표시 | latest-wins | 예 | 2026-04 알고리즘은 ADD-only로 전환 `[docs와 논문 불일치]` |
| MemOS | 2507.03724 | version chain, 의미 중복 시 merge | merge | MemCube별 | read-time version 선택 없음 |
| A-MEM | 2502.12110 | memory evolution(기존 note 속성 재작성) | 없음 | note별 | contradiction 처리 없음 |
| Letta / MemGPT | docs, 2504.13171 | agent가 block 재작성, sleep-time consolidation | prompt 정의 | block별 | TANGLE conflict 보존 91.7% |
| LangMem | docs | "reconcile: delete/invalidate or update/consolidate" | LLM 결정, recency 편향 | memory별 | MemConflict conditional 0.16 |
| Zep / Graphiti | 2501.13956 | 같은 entity pair edge와 비교, `t_invalid` 설정, 이력 보존 | bitemporal latest | edge별 | STALE 6.0%, FC 7% |
| Memobase | docs | 기본 replace. **slot별 `update_description`으로 keep-oldest/replace/merge 지정 가능** | 정적, 개발자 지정 | slot별 | per-slot policy의 production 선례 |
| Supermemory | docs | contradiction 자동 해소, static/dynamic 구분, expiry | latest + expiry | `[미확인]` | |

### 3.2 Write-time: 연구 방법

| 방법 | ID | 시기 | 핵심 | policy |
|---|---|---|---|---|
| CUPMem (STALE) | 2605.06527 | 26.05 | 이전 memory마다 KEEP/STALE/REPLACE/UNKNOWN 판정, topology 기반 propagation, status별 readout. 8.7% → 68.0%. "manually constructed state schema" 의존 | validity label + propagation |
| StateMem | 2608.19652 | 26.08 | state unit(priority, source, deps), supersession 결정론 적용, dependency graph 순회 후 `needs_recheck`. 기존 시스템에 얹어 +32~67pt | supersession 하나 |
| HiGram | 2608.05095 | 26.08 | 계층 그래프, support subgraph 국소화 후 joint rewrite, active/superseded/outdated/pending. MemConflict dynamic 44.8 / static 68.8 / conditional 90.0 | invalidation 하나 |
| TOKI | 2606.06240 | 26.06 | **last-writer-wins / evidence-weighted merge / await-confirmation / per-rule policy**를 bitemporal operator 4종으로 형식화. loser를 audit row에 보존 | rule별 고정 |
| TEPA | 2608.07429 | 26.08 | key별 Beta-Bernoulli posterior로 revocation. reversal 직후 order 민감 | key별 동일 규칙 |
| GPM | 2608.12476 | 26.08 | bitemporal ledger, conflict isolation, non-revival, fail-closed | isolate |
| MemTX | 2607.23929 | 26.07 | transactional commit, retract 시 cascading repair | |
| User as Code | 2606.16707 | 26.06 | append-only log → typed code checkpoint, rule을 함수로 | field별 결정론 |
| Control-Plane Placement | 2606.15903 | 26.06 | write vs mutation-time vs read 비교. mutation-time LLM hook 최고(91.7~93.2%) | |
| Dependency-guided rollback | 2608.10502 | 26.08 | dependency graph로 unsupported memory 비활성화 후 replay | |
| LatticeMind | 2608.08236 | 26.08 | symbolic conflict check 후 미해결만 LLM reconciliation | |

### 3.3 Read-time

| 방법 | ID | 시기 | 핵심 | policy | 우리와의 차이 |
|---|---|---|---|---|---|
| **CAR / Deterministic Recipe** | 2606.01435 | 26.05, v2 26.08 | LLM은 candidate 추출만, Python `max(serial)`. multi-hop은 Self-Ask 분해 → hop별 해결 → chaining. FC-SH 82/93%, FC-MH 27/41%. LongMemEval KU는 유의차 없음(26/45 vs 29/45, p=.45). future work: question-type별 handler routing | freshness 하나 | **분해·합성 구조가 같다.** 우리는 unit별 policy가 다르고 policy 자체를 추론 |
| CAAP (TANGLE) | 2608.13921 | 26.08 | 6 action 중 "evidence가 정당화하는 가장 덜 보수적인 action" 선택. BOC → reversible trial, CPC → conditionalize/clarify, SCC → verify | 유형 → action | instance당 action 하나 |
| StateAuditor | 2608.01619 | 26.08 | draft에서 old→new transition 후보를 LLM이 제안, 결정론 검증 후 repair. STALE VTA 0.686 → 0.736 | recency | transition 여러 개 가능하나 규칙 하나 |
| Selective-QA fusion | 2605.30087 | 26.05 | 학습된 source fusion + abstain | reliability | instance별 |
| MemGate | 2606.06054 | 26.06 | 9M gate로 query-conditioned admission | leakage 방지 | contradiction 아님 |
| AdaptiveMem | 2608.20202 | 26.08 | memory trap 회피 prompt | | work in progress |
| Stale constraints / verification budget | 2608.25553 | 26.08 | verification slot을 provenance path에 재배정 +61~74pt | | |

### 3.4 RL 학습 memory manager

| 방법 | ID | 시기 | 핵심 | conflict 처리 |
|---|---|---|---|---|
| Memory-R1 | 2508.19828 | 25.08 | fact별 ADD/UPDATE/DELETE/NOOP를 PPO/GRPO로 학습, 152 QA pair | op 하나, 유형 없음 |
| Mem-α | 2509.25911 | 25.09 | core/episodic/semantic 편집 RL | **"conflict resolution은 현실적 벤치마크 부재로 제외"** 명시 |
| AgeMem | 2601.01885 | ACL'26 | store/retrieve/update/summarize/discard tool RL | 유형 없음 |
| Supersede | 2606.27472 | 26.06 | 현재값 답변 보상, stale 벌점. Qwen2.5-3B 9.0% → 16.7% | latest 하나 |
| Dual-Layer Agentic Memory | 2608.22215 | 26.08 | non-write / write-new / write-update router + SFT consolidation | update 하나 |

---

## 4. 인접 연구: "여러 개면 당연히 어렵다"의 실제 근거

### 4.1 다중 질문·batch prompting

| 논문 | ID | 시기 | 결과 | 함의 |
|---|---|---|---|---|
| ZeMPE | 2406.10786 | v3 25.06 | 53,100 prompt, 2~100 문제. batch 분류는 단일 대비 −3.2pt. **same-source는 거의 동일**, mixed-source는 2~4개에서도 −13.5pt(81.7% 조합). 위치 편향 없음 | 우리는 same-source(한 memory store)이지만 rule이 heterogeneous. rule 이질성이 source 이질성처럼 작용하는지는 미답 |
| MTI-Bench | 2402.11597 | ACL'24 | 2~3 sub-task를 한 번에 주면 Llama-2-70B +7.3%, GPT-4 **+12.4%** | 2~3개 수준에서는 어렵지 않다는 반증 |
| Multi-instance degradation | 2603.22608 | 26.03 | 20~100개부터 완만 하락, 그 이상 급락. count가 length보다 중요 | 2~4개에서는 generic 저하 예상 안 됨 |
| **Constraint Saturation** | 2608.12426 | 26.08 | 15 model, 36 constraint type, k=1~12. 5~6개부터 all-pass 급락. **제약 실패는 거의 독립적**, all-pass ≈ 개별 통과율의 곱. "직접 간섭 아님" | **가장 중요한 null model.** 우리는 곱보다 유의하게 낮음을 보여야 함 |
| Prior context sensitivity | 2506.00069 | 25.05 | cross-domain 선행 context가 최대 73% 상대 하락 | turn 간, domain 간. 우리 설정과 다름 |
| Multi-question on transcripts | 2509.21732 | 25.09 | 공유 대화 context에 여러 질문. 급락 없음 | 공유 context 다중 질문은 본질적으로 깨지지 않음 |
| Compound-QA | 2411.10163 | 24.11 | 상호 연관 sub-question. 단일 대비 하락 | chaining, aggregation 아님 |
| Batch Prompting Attack | 2503.15551 | 25.03 | 한 query의 주입 지시가 batch 내 다른 query로 전파(GPT-4 90%+) | 한 slot 내용이 다른 slot 행동을 바꾸는 가장 명확한 기존 증거 |

### 4.2 다중 제약 personalization·planning

| 논문 | ID | 시기 | 결과 | 관계 |
|---|---|---|---|---|
| PrefEval | 2502.09597 | ICLR'25 | 10 turn에서 zero-shot preference following 10% 미만 | preference 하나. "conflicting preference에 안 흔들린다" 주장은 `[본문 확인 필요]` |
| PersonaMem | 2504.14225 | COLM'25 | preference evolution 추적, frontier 약 50% | slot 하나 |
| RealPref | 2603.04191 | 26.03 | 1,300 preference, implicit일수록 어려움 | query당 하나 |
| CUPID | 2508.01674 | 25.08 | contextual preference 추론 precision 50% 미만 | conditional 단독도 어렵다는 baseline |
| Order Matters | 2502.17204 | 25.02 | 제약 순서로 최대 약 25% 변동 | 제약 순서. 우리는 evidence 순서 |
| AdaPlanBench | 2606.05622 | 26.06 | 제약 누적 시 하락, 최고 67.75% | 비충돌 제약 |
| PERMA | 2603.23231 | 26.03 | "cross-domain interference"를 시간 축 consistency로 측정 | prompt 내 간섭 아님 |
| MemoryArena | 2602.16313 | 26.02 | 상호의존 multi-session task | chaining |

### 4.3 evidence 순서 민감성

| 논문 | ID | 시기 | 결과 |
|---|---|---|---|
| When Evidence Conflicts (BioNLP'26) | 2605.14115 | 26.05 | 상충 문서 2개의 순서만 바꿔도 모든 모델 하락, 11.4~25.2% flip |
| Same Evidence, Different Answer | 2606.26079 | 26.06 | 18 model, 5 ordering facet. facet별 flip 24~50%, 최고 모델도 13.4% |
| Do RAG Systems Really Suffer From Positional Bias? | 2505.15561 | 25.05 | 노이즈 많은 RAG에서는 위치 효과가 2차적 |
| Lost in the Evidence? (재현 연구) | 2605.27105 | 26.05 | topic 표집이 큰 분산원. 순서 효과 주장에는 많은 instance와 permutation seed 필요 |
| Whose Facts Win? | 2601.03746 | 26.01 | 기관 source 선호가 반복 노출로 역전. 완화 시 79.2% 감소 |

함의: **단일 conflict의 순서 flip은 이미 알려져 있다.** 새로운 것은 cross-unit order effect(unit A의 evidence 순서만 바꿨는데 unit B의 답이 바뀜)뿐이다.

### 4.4 rule 간 간섭·과잉 적용

| 논문 | ID | 시기 | 결과 |
|---|---|---|---|
| In-context superposition (COLM'26) | 2604.09670 | 26.04 | 동시 활성 item이 얽힌 표현으로 경쟁, load 증가 시 하락, recency bias. 경쟁 item 억제 개입이 성능 향상 |
| Everything Everywhere All at Once (ICLR'25) | 2410.05603 | 24.10 | 여러 ICL task를 superposition으로 동시 수행 가능 |
| BenchPreS | 2603.16557 | 26.03 | preference를 전역 규칙처럼 과잉 적용. reasoning으로 안 고쳐짐 |
| The Past Is Prologue | 2606.31121 | 26.06 | 순차 memory update가 over-specific rule·recency 편향 유발. write-time |
| OverEdit / MO-IKE | 2503.11895, 2608.25100 | 25.03, 26.08 | 한 fact의 in-context 편집이 무관한 fact로 유출(specificity 손실) |
| Instruction hierarchy conflict | 2606.10860, 2604.09075 | 26.06, 26.04 | 상충 지시에서 성능 절반 |

"rule R1을 item A에 적용하면 item B 처리가 편향된다"를 agent memory에서 직접 검증한 논문은 **없다.** 가장 가까운 기계적 설명은 2604.09670이다.

---

## 5. RAG conflict 2026 추가분 (간략)

- ConflictRAG 2605.17301: detect-classify-resolve, 탐지 F1 88.7%
- ConflictQA + XoT 2604.11209 (SIGIR'26): text vs KG evidence
- ArbGraph 2604.18362: claim graph의 support/contradiction edge
- EvidentialRAG 2607.10491: Dirichlet + Dempster-Shafer로 direct / conflict-aware / abstain routing
- EvoTrustRAG 2608.07933: conflict를 evolution / malicious / uncertainty로 귀인 후 답변
- ConflictScore 2606.26437: claim 수준 metric

모두 문서 conflict이며 query당 conflict 하나다. EvidentialRAG의 3-way routing은 per-conflict policy 선택의 유사 구조로 인용 가능하다.

---

## 6. query 형태 요약표

| 논문 | query당 conflict | policy 집합 | 한 답으로 합성 |
|---|---|---|---|
| MemConflict | 1 | dynamic/static/conditional, query당 하나 | 아니오 |
| TANGLE | 1 | 6 action | 아니오 |
| STALE | pair 1 | supersede + propagate | 아니오 |
| A-TMA/LTP | slot 1 | 질문이 요구하는 state | 아니오 |
| Selective-QA | slot 1, source 여러 | reliability / abstain | 아니오 |
| HorizonBench | 1 | latest | 아니오 |
| MemSyco-Bench | 1 | task별 5 policy | 아니오 |
| MCB | 1 | persist/verify/clarify | 아니오 |
| MemoryAgentBench FC-MH | 여러 fact | latest | 예, policy 하나 |
| Memora | 여러 session | obsolete 배제 | 예, policy 하나 |
| Mem2ActBench | 여러 fact | latest | 예, policy 하나 |
| IBA-Bench | 제약 3개 이상 | 암묵적 | 예, policy 없음 |
| CIMemories | attribute 여러 | attribute별 disclosure | 예 (privacy) |
| **본 연구** | **K≥2** | **unit별 서로 다른 policy** | **예** |

---

## 7. 우리 연구에 대한 함의

### 7.1 유리한 점

1. 공백은 아직 비어 있다. read-time per-unit heterogeneous policy composition과 그 benchmark가 없다.
2. "여러 개면 당연히 어렵다"는 문헌상 약하다. MTI-Bench, ZeMPE same-source, 2603.22608 모두 2~4개 수준에서는 하락이 없거나 작다. 우리 composite는 unit 2~3개, record 5~9개다.
3. global-policy collapse의 외부 증거가 있다. MemConflict 시스템별 점수가 유형 간 반대이고, MemSyco-Bench에서 caution 지시가 task 간 trade-off를 만든다.
4. write-time pipeline이 conflict를 파괴한다(TANGLE 46~92%). read-time resolver의 근거다.

### 7.2 불리한 점

1. 2608.12426의 독립 실패 null model. composite 성공률 ≈ atomic 성공률의 곱이면 간섭이 아니다.
2. 순서 flip 단독은 novelty가 아니다.
3. CAR + CAAP + IBA-Bench가 2026년 5~8월에 나왔다. 결합되면 끝난다.
4. 강한 모델 결과가 없다. 인용된 논문 전부 "reasoning·scale이 줄이지만 없애지는 못한다"고 보고하므로 반드시 frontier 모델을 포함해야 한다.

### 7.3 위치 문장 초안

> 기존 memory-conflict 연구는 conflict를 유형화하되 query당 하나씩 평가하거나(MemConflict, TANGLE, STALE), 여러 memory를 하나의 규칙으로 합성한다(Memora, CAR). 우리는 한 요청 안에서 서로 다른 유형의 conflict unit에 서로 다른 policy를 적용해 합성해야 하는 설정을 정의하고, atomic 해결 성공이 composite 성공을 보장하지 않으며 실패가 독립 누적보다 크고 policy 유출로 설명됨을 보인다.

---

## 8. 리뷰어가 요구할 통제

문헌이 실제로 한 것에 근거한 목록이다.

1. **독립 null model** (2608.12426): composite all-unit success를 atomic 성공률의 곱과 비교. composite 안의 unit별 정확도도 함께 보고
2. **count-matched no-conflict 통제** (2603.22608, ZeMPE): 같은 수의 질문, 같은 memory store, conflict 없음
3. **same-rule vs mixed-rule at equal K** (ZeMPE same/mixed-source, MemoryAgentBench FC-MH)
4. **context 고정 분해** (2606.01435, MTI-Bench Multi-Part): 모든 record를 두고 질문 수만 바꿈. (a) 다른 conflict가 context에 있기만 함 (b) 모두 물음 (c) 순차 turn
5. **cross-unit order test** (2605.14115, 2606.26079 확장): A의 evidence만 permute, A 답은 그대로인데 B가 flip하는 비율. 2605.27105에 따라 instance·seed를 충분히
6. **오류 귀인** (BenchPreS, OverEdit): 틀린 값이 어느 policy가 골랐을 값인지. intended × applied policy 혼동행렬
7. **slot 위치 × conflict 유형 교차** (ZeMPE, 2502.17204)
8. **retrieval vs use 분리** (MemTrace): oracle context로 retrieval 실패 배제
9. **모델 급 sweep**: reasoning model과 frontier API 포함
10. **길이 맞춘 distractor** (MemConflict): 단일 conflict prompt에 filler를 넣어 token·record 수 일치

---

## 9. 참고 ID 색인

벤치마크: 2605.20926, 2608.13921, 2605.06527, 2605.30087, 2607.01935, 2604.17283, 2606.22877, 2607.01071, 2606.17328, 2510.27246, 2410.10813, 2606.27472, 2601.19935, 2504.14225, 2608.21381, 2603.26680, 2608.04095, 2603.23231, 2603.16557, 2601.16621, 2601.13722, 2606.06055, 2511.14937, 2608.02171, 2607.16716, 2603.23848, 2604.20006, 2507.05257, 2511.03506, 2602.01313, 2606.01223, 2605.14498, 2605.12978, 2602.16313, 2603.25973, 2605.25535

방법·시스템: 2504.19413, 2507.03724, 2502.12110, 2504.13171, 2501.13956, 2512.12818, 2510.18866, 2508.19828, 2509.25911, 2601.01885, 2507.02259, 2606.27472, 2601.07468, 2512.20237, 2603.11768, 2605.06527, 2606.01435, 2606.06240, 2606.15903, 2606.06054, 2606.16707, 2607.23929, 2608.01619, 2608.05095, 2608.07429, 2608.08236, 2608.10502, 2608.12476, 2608.19652, 2608.19564, 2608.20202, 2608.22215, 2608.25553, 2606.29279, 2606.22030, 2606.02976, 2605.30771, 2606.29914

인접: 2406.10786, 2402.11597, 2603.22608, 2608.12426, 2506.00069, 2411.10163, 2509.21732, 2503.15551, 2502.09597, 2603.04191, 2508.01674, 2502.17204, 2606.05622, 2605.14115, 2606.26079, 2505.15561, 2605.27105, 2601.03746, 2502.08662, 2604.09670, 2410.05603, 2606.31121, 2503.11895, 2608.25100, 2606.10860, 2604.09075

RAG conflict 2026: 2605.17301, 2604.11209, 2604.18362, 2607.10491, 2608.07933, 2606.26437
