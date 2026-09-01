# 외부 문서 충돌 연구 지형과 우선순위

> 부제: 단순 충돌에서 다중ㆍ메모리ㆍ멀티홉 충돌까지, 무엇이 실제 연구 공백인가
>
> 조사 기준일: 2026-08-31  
> 범위: 검색ㆍRAG 시스템이 입력으로 받은 외부 문서 사이의 충돌을 중심으로 하되, 비교를 위해 context–memory conflict, 장기 메모리, 멀티모달, 보안 연구를 포함한다. 2024년 EMNLP 서베이 이후의 2024–2026 연구를 중점 조사했다. 동료심사 논문과 공개 벤치마크를 우선하고, 2026년 최신 arXiv 연구는 출판 상태를 구분해 해석한다.

## 0. 결론부터

### 분야 전체에서 가장 시급한 문제

현재 가장 시급한 문제는 충돌 유형을 하나 더 만들거나 충돌 탐지 정확도를 조금 높이는 것이 아니다. **실제 다중 출처 문서에서 모델이 충돌을 발견하고, 근거를 국소화하고, 그 충돌이 해결 가능한지 판단한 뒤, 질문에 맞는 행동을 끝까지 일관되게 수행하는가**가 핵심이다.

이를 이 문서에서는 **탐지-행동 간극(detection-to-action gap)** 이라고 부른다.

~~~text
외부 문서
  → 관련 claim 복원
  → 충돌 탐지ㆍ국소화
  → 충돌 원인ㆍ해결 가능성 판단
  → 행동 선택(답변/양측 병기/추가 검색/명료화/기권)
  → 최종 답변과 출처 귀속
~~~

앞 단계의 성공이 뒤 단계의 성공을 보장하지 않는다.

- [Ragability](https://aclanthology.org/2026.lrec-1.182/)에서는 모델이 이진 충돌 여부는 비교적 알아내면서도 내용 질문에는 어려움을 보였다.
- [When Facts Change](https://aclanthology.org/2026.findings-acl.103/)에서는 큰 모델이 시간 충돌을 언어화해도 그 판단이 최종 예측에 거의 반영되지 않았다.
- [GroupQA](https://aclanthology.org/2026.findings-acl.2003/)에서는 반복ㆍ순서 휴리스틱과 함께 모델 설명의 비충실성이 관측됐다.
- 현재 01_air_trace 파일럿에서도 reflection은 충돌 언어화를 크게 늘렸지만 정확도는 2–4%p만 상승했고, 올바르게 해소한 뒤 최종 답에서 뒤집히는 AIR이 남았다. standard 정답의 42–52%는 충돌을 언어화하지 않은 blind hit이었다.

서로 다른 데이터와 연구가 같은 병목을 가리킨다는 점에서, 이는 단일 벤치마크의 특이 현상보다 강한 연구 근거다.

### 이 프로젝트에서 가장 가능성 높은 첫 논문

**최우선 추천은 기존 AIR 연구를 확장한 인과적ㆍ행동적 감사 논문**이다.

> **가제:** *From Detection to Action: A Causal Audit of Conflict Handling in Retrieval-Augmented Language Models*

핵심 질문은 다음과 같다.

> 모델이 충돌 상황에서 정답을 맞혔을 때, 실제로 충돌 근거를 식별하고 적절한 해소 정책을 적용해서 맞힌 것인가, 아니면 문서 순서ㆍ반복ㆍ파라메트릭 기억ㆍ표면 단서에 의존해 우연히 맞힌 것인가?

단, 자유형 Chain-of-Thought를 모델의 실제 내부 추론으로 간주하면 안 된다. 논문의 중심을 사고 내용 해석에서 **관측 가능한 단계별 과제와 개입에 대한 행동 변화**로 옮겨야 한다.

### 가장 높은 상한을 가진 후속 방법론

고위험ㆍ고수익 방향은 03_multihop_conflict의 재구성안이다.

> 실제 문서에서 질문 관련 claimㆍ조건ㆍ시간ㆍ개체를 복원하는 semantic compilation 오류가 멀티홉ㆍ고차 충돌을 어떻게 지우거나 만들어 내는지 분석하고, 복수 의미 해석을 보존하며 source-grounded proof를 찾는 방법

이 방향은 ACL main급 상한이 높지만 데이터 주석과 방법 구현 비용도 가장 크다. AIR의 진단 결과로 어느 단계가 실제 병목인지 먼저 확인한 뒤 착수하는 편이 안전하다.

### 현재 독립 주제로 비추천하는 방향

1. **충돌 유형×개수의 단순 상관분석**: MAGIC이 hop×1–4 conflicts를 이미 분석했다. 더 많은 충돌은 식별을 쉽게 하지만 정확한 국소화는 어렵게 만든다. 상관표만 추가하면 신규성이 약하다.
2. **자연 검색 문서의 복합 충돌 K>1,H>1**: 현재 프로젝트의 무작위ㆍstrict 표본 202건에서 0건이었다. 자연 발생의 중요성을 주장하기 어렵고, 합성으로 만들면 현실성이 약해진다.
3. **일반적인 메모리 충돌 벤치마크**: 2026년에 MemConflict, STALE, TANGLE, selective personal-memory QA가 연달아 등장했다. 현재 프로젝트에서도 이질 정책 자체의 고유 난이도 가설이 기각됐다.
4. **그래프 충돌 해결기 하나 더 만들기**: ArbGraph, KCR, ConflictRAG와 직접 경쟁한다. 그래프 입력의 추출ㆍ정렬ㆍedge 오류를 다루지 않으면 기여가 얕다.

---

## 1. 문제 범위를 다시 정의하기

### 1.1 충돌 위치

[Knowledge Conflicts for LLMs: A Survey](https://aclanthology.org/2024.emnlp-main.486/)는 지식 충돌을 세 위치로 구분한다.

| 위치 | 정의 | 대표 질문 |
|---|---|---|
| context–memory | 외부 문서와 모델 파라메트릭 기억의 충돌 | 문서가 모델 기억과 다를 때 무엇을 따르는가? |
| inter-context | 여러 외부 문서 사이의 충돌 | 검색 결과 A와 B가 다르면 어떻게 하는가? |
| intra-memory | 모델 내부에 함께 학습된 지식의 충돌 | 질문 표현에 따라 기억 답변이 왜 달라지는가? |

이 프로젝트의 핵심 범위는 **inter-context conflict**다. 장기 사용자 메모리는 외부 저장소에서 검색된다는 점에서는 context지만, 개인화ㆍ시간 상태ㆍprivacyㆍ대화 세션이라는 별도의 해결 규칙을 가지므로 독립 응용 도메인으로 취급해야 한다.

### 1.2 서로 혼동하면 안 되는 네 가지 복잡도

| 축 | 정의 | 예시 |
|---|---|---|
| 충돌 개수 K | 질문과 관련된 독립 충돌 단위의 수 | 가격과 출시일이 각각 충돌 |
| 정책 다양성 H | 필요한 서로 다른 해소 규칙의 수 | 최신 정보 선택 + 지역 조건 보존 |
| 추론 hop | 충돌을 도출하는 데 필요한 연결 단계 수 | A의 소유자가 B이고 B가 금지 목록에 있음 |
| 논리 arity | 충돌을 성립시키는 데 공동으로 필요한 전제 수 | 어느 두 문서도 직접 모순이 아니지만 세 문서를 함께 보면 불일치 |

문서 수가 많다고 멀티홉인 것은 아니고, 충돌이 여러 개라고 복합 정책이 필요한 것도 아니다. 이 네 축을 분리하지 않으면 “충돌이 많아서 어렵다”와 “추론 구조가 어려워서 어렵다”를 구별할 수 없다.

### 1.3 충돌과 다답성도 다르다

외부 문서의 차이는 모두 오류가 아니다.

- factual contradiction: 동일 조건에서 양립 불가능한 사실
- temporal update: 서로 다른 시점에 각각 참
- scope/condition difference: 지역ㆍ대상ㆍ조건이 달라 함께 참
- ambiguous entity: 동명이인 또는 질문의 지시 대상 불명확
- opinion disagreement: 단일 정답으로 제거하면 안 되는 견해 차이
- complementary evidence: 서로 다르지만 함께 답을 완성
- misinformation/poisoning: 잘못된 또는 의도적으로 조작된 증거
- insufficient evidence: 충돌이 아니라 판단 근거 부족

[DRAGged into Conflicts / CONFLICTS](https://arxiv.org/abs/2506.08500)는 현실적 RAG 설정에서 이러한 유형과 유형별 기대 행동을 함께 제시했다. 따라서 “충돌 탐지 후 항상 하나를 선택한다”는 시스템은 문제 정의부터 잘못됐다.

---

## 2. 연구 지형: 데이터에서 행동까지

### 2.1 실세계 외부 문서 충돌의 존재와 규모

초기 연구는 합성 entity swap에 크게 의존했지만, 이제 자연 충돌 자체의 존재는 충분히 입증됐다.

| 자원 | 현실성ㆍ규모 | 주로 평가하는 것 | 남은 한계 |
|---|---|---|---|
| [WikiContradict](https://proceedings.neurips.cc/paper_files/paper/2024/hash/c63819755591ea972f8570beffca6b1b-Abstract-Datasets_and_Benchmarks_Track.html) | Wikipedia 실제 contradiction tag의 253개 인간 검증 사례 | 두 passage의 명시적ㆍ암묵적 충돌 대응 | 작고 동일 출처 중심 |
| [ConflictingQA](https://aclanthology.org/2024.acl-long.403/) | 논쟁적 질문과 실제 웹 증거 | 어떤 증거 특성이 모델을 설득하는가 | 이진 관점 질문 중심 |
| [WhoQA](https://aclanthology.org/2024.findings-emnlp.593/) | 5K 질문, 최대 8개 답, 150K Wikipedia entity | 동명이인과 복수답 표출 | 엄밀한 사실 모순보다 entity ambiguity 중심 |
| [QACC](https://aclanthology.org/2025.findings-naacl.99/) | 사람이 주석한 검색 문맥; 조사 표본의 최대 25%에서 충돌 문맥 | 단일 정답 ODQA의 선택과 설명 | 짧은 검색 snippetㆍ사실 질문 중심 |
| [CONFLICTS](https://arxiv.org/abs/2506.08500) | 전문가 주석의 현실적 검색 결과 | 충돌 유형별 적절한 응답 | LLM judge 의존, 논리 구조 주석 부족 |
| [ConfRAG](https://aclanthology.org/2026.acl-long.11/) | 1,814 실제 질문, 질문당 평균 9.58 web paragraph, 57.2% explicit contradiction | answer clusteringㆍanswer/reason coverage | hopㆍ최소 근거ㆍ해결 가능성 주석 없음 |
| [WIKICOLLIDE](https://arxiv.org/abs/2509.23233) | corpus-level Wikipedia inconsistency | 대규모 corpus 내 실제 불일치 탐색 | QA 행동ㆍ해소와는 별도 문제 |

**판단:** “실세계 외부 문서 충돌 데이터가 없다”는 주장은 더 이상 성립하지 않는다. 남은 문제는 자연 충돌의 존재 증명이 아니라, 그 충돌의 원인ㆍ질문 관련성ㆍ해결 가능성ㆍ근거 경로를 주석하고 행동까지 평가하는 것이다.

### 2.2 충돌 유형

유형 연구는 필요한 이유가 분명하다. 유형에 따라 올바른 행동이 달라지기 때문이다.

~~~text
outdated          → 현재 질문이면 최신값, 과거 질문이면 당시 값
misinformation    → 신뢰 가능한 반증을 근거로 배제
opinion           → 관점과 출처를 구분해 병기
ambiguity         → 가능한 대상을 나누거나 사용자에게 확인
scope difference  → 조건부 답변
complementary     → 통합
~~~

그러나 유형 분류 자체는 CONFLICTS, [ECON](https://aclanthology.org/2024.emnlp-main.447/), WikiContradict, ConflictBench 등으로 빠르게 채워졌다. 새 taxonomy보다 다음이 중요하다.

1. 유형 라벨이 실제 최적 행동을 예측하는가?
2. 한 사례에 여러 관계가 함께 있을 때 단일 유형 라벨이 충분한가?
3. 모델이 유형 이름은 맞히지만 근거와 행동은 틀리는가?
4. 질문 시점ㆍ관할ㆍ사용자 비용이 달라지면 같은 충돌의 행동이 바뀌는가?

즉 유형은 **설명 변수이자 정책 조건**으로 유용하지만 독립 논문의 종착점으로는 약하다.

### 2.3 충돌 개수와 증거 비율

[MAGIC](https://aclanthology.org/2025.findings-emnlp.466/)은 single/multi-hop과 1–4개 충돌을 교차해 분석했다. 충돌 수가 늘수록 identification은 쉬워지지만 localization은 어려워지는 경향을 보고했다. 이는 개수가 난이도를 단조롭게 높인다는 직관을 반박한다.

[RAMDocs/MADAM-RAG](https://arxiv.org/abs/2504.13079)는 ambiguityㆍmisinformationㆍnoise와 증거 불균형을 함께 다루며, misinformation 비율이 커질 때 어려움이 증가함을 보였다. [Whose Facts Win?](https://arxiv.org/abs/2601.03746)는 낮은 신뢰 출처도 반복되면 기관 출처 선호를 뒤집을 수 있음을 보였고, [GroupQA](https://aclanthology.org/2026.findings-acl.2003/)는 동일 주장의 paraphrase가 독립된 지지 증거보다 더 설득력 있게 작동할 수 있음을 보였다.

따라서 연구해야 할 것은 단순 개수-정확도 상관이 아니다.

> 모델은 문서 수를 세는가, 독립적인 증거의 수를 세는가, 아니면 반복된 문자열과 위치를 세는가?

좋은 설계는 총 문서 수, 독립 출처 수, 같은 원문의 복제ㆍ요약 수, 찬반 비율, K, 문서 길이ㆍ위치, authority와 정확성을 독립 조작해야 한다. 이 축은 모든 충돌 연구의 필수 통제이며, source-lineage 연구로 발전시킬 때만 강한 독립 주제가 된다.

### 2.4 명시적 pairwise 탐지와 국소화

[ECON](https://aclanthology.org/2024.emnlp-main.447/)은 NLIㆍfactual consistency modelㆍLLM을 충돌 탐지기로 비교했다. [Contradiction Detection in RAG Systems](https://arxiv.org/abs/2504.00180)는 self, pair, conditional contradiction에 대해 탐지ㆍ유형ㆍ문서 segmentation을 평가했고, MAGIC은 identification과 localization을 분리했다.

이제 “충돌 탐지기가 평가되지 않았다”는 표현은 부정확하다. 하지만 탐지 점수가 contradiction, novelty, irrelevance, lexical overlap, negation cue, 길이, entity ambiguity 중 무엇에 반응하는지는 불명확하다. 사람 검증 real seed와 한 요인만 바꾼 counterfactual twin을 결합해 NLI, PPL gap, entropy shift, hidden-state probe, LLM judge를 같은 claim 단위에서 비교하는 **충돌 신호의 인과적 타당성 감사**는 여전히 유망하다.

### 2.5 탐지-행동 간극과 과정 진단

이 축은 현재 가장 강한 교차 연구 공백이다. 기존 평가는 최종 accuracy, 이진 탐지, localization, 설명 적절성, context faithfulness 중 하나만 보는 경우가 많다. 실제 실패는 relevance, recognition, localization, interpretation, arbitration, action selection, realization, attribution 사이에서 생긴다.

현재 AIR의 장점은 정확도를 단계 전환으로 분해하려는 데 있다. 다만 다음 비판을 해결해야 한다.

1. 자유형 reasoning trace는 내부 인과 과정의 증거가 아니다.
2. 충돌을 언어화하지 않았다고 인지하지 못했다고 단정할 수 없다.
3. reflection으로 언어화를 강제하면 stage denominator가 달라진다.
4. 정답을 안다고 올바른 근거를 사용한 것은 아니며, 적절한 충돌 표출이 exact match에서는 오답일 수 있다.

따라서 본실험은 stage별 독립 행동 probe와 인과 개입을 사용해야 한다.

- conflict-bearing span 삭제
- 정답을 유지한 문서 순서 교환
- 동일 주장의 복제 수 변경
- source labelㆍpublication time swap
- 질문 시점ㆍ대상ㆍscope만 바꾼 query twin
- 선택 근거만 남긴 sufficiency test
- 선택하지 않은 근거 제거 comprehensiveness test
- 중간 구조화 판정을 고정하고 최종 생성만 재표집

이렇게 해야 “모델이 생각했다고 말했다”가 아니라 “특정 근거와 판정이 답을 실제로 움직였는가”를 평가할 수 있다.

### 2.6 행동 정책ㆍ불확실성ㆍ기권

[ConflictScore](https://arxiv.org/abs/2606.26437)는 답변 claim이 지지와 반박 증거의 공존을 얼마나 반영하는지 측정한다. [When Evidence Conflicts](https://arxiv.org/abs/2605.14115)는 생의학 충돌에서 문서 순서를 뒤집을 때 11.4–25.2%의 예측이 바뀌며 conflict-aware abstention이 selective accuracy를 개선할 수 있음을 보였다. [EvidentialRAG](https://arxiv.org/abs/2607.10491)과 [SABER](https://arxiv.org/abs/2605.18792)는 답변ㆍ충돌 인지 답변ㆍ기권 또는 PK/CK 신뢰 선택을 불확실성에 따라 라우팅한다.

따라서 “답변/양측 병기/기권을 처음 통합한다”는 신규성은 없다. 남은 질문은 행동의 효용이다. 추가 검색과 명료화는 언제 기권보다 나은지, 해결 가능한 충돌과 본질적으로 미결정인 충돌을 구분하는지, 도메인별 오류 비용과 domain shift 아래 위험을 통제하는지가 핵심이다.

### 2.7 시간ㆍ출처ㆍprovenance

외부 문서 충돌에서 가장 실용적인 축이지만 최신ㆍ권위ㆍ다수결은 모두 불완전한 휴리스틱이다.

- [Do Metadata and Appearance Affect RAG?](https://aclanthology.org/2024.blackboxnlp-1.24/)는 publication time과 appearance가 답에 인과적 영향을 줄 수 있음을 보였다.
- [When Facts Change](https://aclanthology.org/2026.findings-acl.103/)는 temporal conflict 인식과 최종 행동의 분리를 보였다.
- [FRESCO](https://arxiv.org/abs/2604.14227)는 reranker가 오래됐지만 의미적으로 풍부한 문서를 선호하는 실패를 다뤘다.
- [Whose Facts Win?](https://arxiv.org/abs/2601.03746)는 authority preference가 반복에 의해 뒤집힘을 보였다.
- [RA-RAG](https://openreview.net/pdf?id=J3xRByRqOz)는 source reliability를 반복 추정해 가중 집계했다.

유망한 세부 공백은 두 가지다.

**Bitemporal semantic relation:** publication time과 fact validity time을 분리하고 correction, retraction, supersession, 시점별 공존, jurisdiction/scope difference, 진정한 미해결 충돌을 판별한다. 단순 recency보다 강하지만 실제 개정 이력 gold 구축 비용이 크다.

**Evidence lineage와 독립성:** derived-from, cites, near-duplicate, independently corroborates 관계를 복원해 복제된 다수와 독립 합의를 구별한다. GroupQA와 Whose Facts Win?이 반복 편향을 이미 보였으므로, 실제 lineage gold와 복제 개입, dependency-aware aggregation이 있어야 신규성이 생긴다.

### 2.8 멀티홉ㆍ고차ㆍ전역 충돌

이 축은 어렵고 중요하지만 아무도 하지 않았다는 주장은 틀리다.

- [MAGIC](https://aclanthology.org/2025.findings-emnlp.466/)은 KG 기반 멀티홉 inter-context conflict를 벤치마킹했다.
- [Contradiction Detection in RAG Systems](https://arxiv.org/abs/2504.00180)는 세 번째 문서가 앞의 두 문서를 양립 불가능하게 만드는 conditional contradiction을 포함한다.
- [Global Consistency Checking with Noisy LLM Oracles](https://arxiv.org/abs/2601.13600)는 pairwise 검사의 한계를 형식화하고 minimal inconsistent subset과 repair를 다룬다.
- [ArbGraph](https://arxiv.org/abs/2604.18362)는 atomic claim support/contradiction graph를 만든다.
- [KCR](https://aclanthology.org/2026.acl-long.1451/)은 textㆍgraph reasoning trace로 명시적 충돌을 해소한다.

남은 핵심은 raw document에서 논리 입력을 만드는 과정이다. 기존 전역 알고리즘은 비교할 fact나 graph edge가 주어졌다고 가정하지만 실제 문서에서는 entity alignment, time scope, modality, condition, exception을 복원해야 한다. 작은 오류 하나가 고차 충돌 전체를 없앨 수 있다.

따라서 03의 타당한 프레이밍은 “멀티홉 충돌을 새로 만든다”가 아니라 **질문 조건부 고차 충돌에서 semantic compilation uncertainty가 proof와 최종 행동에 어떻게 전파되는가**다. ACL main 상한은 높지만 gold spanㆍclaimㆍalignmentㆍproof graph가 모두 필요해 가장 비싸다.

### 2.9 다중ㆍ복합 충돌

현재 프로젝트의 K/H 파일럿은 중요한 부정 결과를 냈다.

- ConfRAG 120, NatConfQA 22, QACC 60의 strict 자연 검색 표본 총 202건에서 K>1,H>1은 0건이었다.
- ConfRAG 0/120의 양측 95% Wilson 상한은 약 3.1%다.
- 장기 메모리 Stage I–J에서도 H=2가 고유하게 어렵다는 가설이 기각됐다.
- conflict 없는 multi-slot control도 비슷하게 하락해 상당 부분은 일반적인 selectionㆍbinding 문제였다.

**판단:** K와 H는 stress factor로 유지하되, 자연 외부 문서에서의 독립 연구 주제로는 중단하는 편이 맞다. 실제 enterprise long-form corpus에서 prevalence가 확인될 때 재개할 수 있다.

### 2.10 장기 사용자 메모리 충돌

실제 agent 제품에는 시급하지만 2026년에 경쟁이 매우 빠르게 증가했다.

| 연구 | 선점한 부분 |
|---|---|
| [MemConflict](https://arxiv.org/abs/2605.20926) | dynamic/static/conditional conflict, retrievalㆍrankingㆍanswer 진단 |
| [STALE](https://arxiv.org/abs/2605.06527) | 명시적 부정 없이 이전 상태가 무효화되는 implicit conflict |
| [Selective QA over Conflicting Personal Memory](https://arxiv.org/abs/2605.30087) | 34,560 controlled instance, fusion과 selective QA |
| [TANGLE](https://arxiv.org/abs/2608.13921) | 단일 정답이 없는 genuine conflict, clarificationㆍcalibrationㆍfaithfulness |

진행한다면 order-robust multi-slot memory application, extraction 단계의 conflict relation 소실, tool action에서의 state conflict 전파 중 하나로 좁혀야 한다. 외부 문서 충돌 연구의 주축과는 분리된 연구 프로그램으로 관리하는 것이 좋다.

### 2.11 그래프ㆍ논증ㆍ전역 중재

그래프는 주류 표현으로 자리잡고 있지만 그래프라는 이유만으로 해법이 되지는 않는다.

~~~text
raw document
  → claim extraction
  → entity/time/scope alignment
  → support/contradiction edge prediction
  → graph optimization
  → response
~~~

마지막 최적화가 수렴해도 앞의 node와 edge가 틀리면 사실성은 보장되지 않는다. [HiGoE](https://aclanthology.org/2026.acl-long.902/)도 LLM 생성물로 그래프를 만들 때 hallucination을 재도입하는 일반적 construction 위험을 지적한다.

유망한 방법론은 clean graph optimizer가 아니라 nodeㆍedge uncertainty, extraction 오류 전파, source dependence, higher-order hyperedge, source-grounded certificate, corruption 아래 risk를 다뤄야 한다.

### 2.12 적대적 충돌ㆍpoisoning

[PoisonedRAG](https://www.usenix.org/conference/usenixsecurity25/presentation/zou-poisonedrag)는 수백만 문서 DB에 질문당 악성 문서 5개를 넣어 90% 공격 성공률을 보고했다. [PURPOSE](https://arxiv.org/abs/2608.04756)는 정면 모순을 피하고 신뢰된 사실의 업데이트처럼 보이는 문서로 conflict resolver를 우회한다.

실제 위험은 높지만 공격 경쟁이 빠르고, 보안 venue의 threat model과 adaptive attacker 평가가 별도로 필요하다. AIR 또는 provenance 연구의 robustness section에는 유익하지만 독립 전환에는 보안 실험 역량이 필요하다.

### 2.13 멀티모달ㆍ다국어 충돌

- [MMIR](https://aclanthology.org/2025.findings-acl.964/)은 layout-rich 문서의 visual-text inconsistency를 평가한다.
- [VLM-DeflectionBench](https://aclanthology.org/2026.acl-long.1307/)는 conflict/insufficient evidence 아래 deflection을 평가한다.
- [CMC-Bench](https://aclanthology.org/volumes/2026.magmar-main/)는 3,768개 text-image conflict 사례와 modality lean을 보고했다.

다국어는 번역 과정이 scopeㆍmodalityㆍ수치ㆍ시제 충돌을 만들거나 지우는 cross-lingual semantic compilation으로 연결할 때 의미가 있다. 현재 자산과의 연속성이 낮으므로 최우선은 아니다.

---

## 3. 후보 방향 비교 평가

점수는 절대 채택 확률이 아니라 문헌과 현재 자산을 기준으로 한 상대 평가다. 시급성, 미해결성, 6–9개월 실현성, 현재 자산 적합성, ACL 기여 상한을 각각 5점으로 평가했다.

| 순위 | 방향 | 시급성 | 미해결성 | 실현성 | 자산 적합성 | ACL 상한 | 종합 판단 |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | 탐지-행동 간극의 인과적 감사 | 5 | 4 | 5 | 5 | 4 | **즉시 진행** |
| 2 | 충돌 신호의 인과적 타당성 | 5 | 5 | 4 | 4 | 5 | **1번과 통합 권장** |
| 3 | query-conditioned semantic compilation + 고차 충돌 | 5 | 5 | 2 | 3 | 5 | **고위험 후속 main** |
| 4 | source lineageㆍ독립성 인지 집계 | 5 | 4 | 3 | 3 | 5 | **유망한 대안** |
| 5 | bitemporal correction/supersession | 5 | 4 | 2 | 3 | 5 | 데이터 확보 시 진행 |
| 6 | 비용 민감형 selective action | 5 | 3 | 3 | 3 | 4 | 경쟁 심함; 1번 후속 |
| 7 | 적대적 resolver 방어 | 5 | 4 | 2 | 1 | 5 | 별도 보안 트랙 |
| 8 | 멀티모달ㆍ다국어 충돌 | 4 | 3 | 3 | 1 | 4 | 장기 확장 |
| 9 | 메모리 충돌 일반론 | 5 | 2 | 3 | 4 | 3 | 경쟁 과밀ㆍ가설 약화 |
| 10 | 유형×개수 상관 | 3 | 1 | 5 | 4 | 2 | 보조 분석으로 흡수 |
| 11 | 자연 검색의 복합 K/H 충돌 | 2 | 3 | 1 | 4 | 2 | 현재 evidence로 중단 |
| 12 | clean conflict graph resolver | 4 | 2 | 3 | 2 | 3 | 그래프 오류 없이는 비추천 |

### 왜 1번과 2번을 결합해야 하는가

탐지-행동 간극만 연구하면 평가 taxonomy에 머물 수 있고, 충돌 신호 감사만 연구하면 detector AUC 비교로 보일 수 있다. 결합하면 다음 하나의 강한 주장이 된다.

> 기존 RAG 충돌 성공률은 실제 contradiction sensitivity와 해소 과정을 과대평가한다. 모델과 detector는 충돌 외 요인에도 반응하며, 충돌을 정확히 찾더라도 적절한 행동으로 전달하지 못한다. 이를 요인별 개입과 단계별 행동 시험으로 분해한다.

이 주장은 현재 AIR의 blind hitㆍAIRㆍreflection 결과를 살리면서 자유형 trace를 내부 추론으로 취급하는 약점을 피한다.

---

## 4. 최우선 논문 재구성안

### 4.1 가제

**From Detection to Action: A Causal Audit of Conflict Handling in Retrieval-Augmented Language Models**

대안:

- *Right Answer, Wrong Conflict Process: Auditing RAG under Conflicting Evidence*
- *Does Conflict Recognition Reach the Answer? Stage-Wise and Causal Evaluation of RAG*
- *Beyond Conflict Accuracy: Intervention-Based Auditing of Evidence Recognition, Arbitration, and Response*

### 4.2 중심 주장

> 최종 정답과 자유형 설명은 충돌 처리 능력의 신뢰할 수 있는 proxy가 아니다. 충돌 처리는 recognition, localization, arbitration, action, realization으로 분해해야 하며, 근거 삭제ㆍ순서ㆍ복제ㆍmetadataㆍquery-scope 개입으로 각 단계의 인과적 역할을 검증해야 한다.

### 4.3 연구 질문

**RQ1. 정답률은 실제 충돌 인식과 얼마나 분리되는가?**

- blind hit, recognized wrong, resolved-but-flipped를 모델ㆍ데이터셋별로 측정한다.
- conflict와 난이도ㆍ문서 수가 같은 non-conflict control을 둔다.

**RQ2. 어떤 충돌 신호가 contradiction 자체에 반응하는가?**

- NLI, LLM judge, PPL/entropy, latent probe를 같은 claim 단위로 정렬한다.
- contradiction, relevance, novelty, lexical overlap, order, duplication을 하나씩 개입한다.

**RQ3. 올바른 중간 판정이 최종 행동을 실제로 바꾸는가?**

- gold localization, gold type, gold action을 단계적으로 oracle 제공한다.
- 각 oracle의 성능 회복량으로 병목을 분해한다.

**RQ4. 기존 완화법의 이득은 어느 경로에서 발생하는가?**

- reflection, structured prompting, CAD/CD2, reranking, multi-agent verification을 동일 토큰ㆍ호출 예산에서 비교한다.
- accuracy 증가를 legitimate correction, shortcut, blind hit, harmful flip으로 회계한다.

### 4.4 데이터 구성

새 대형 데이터셋을 처음부터 만들기보다 기존 자원을 층화한다.

1. 자연 검색: QACC, CONFLICTS/DRAGged, ConfRAG
2. 자연 문서 pair: WikiContradict
3. 통제 합성: RAMDocs, ECON, MAGIC
4. 고난도 구조 probe: MAGIC multi-hop, conditional contradiction
5. non-conflict control: 문서 수ㆍ길이ㆍ질문 난이도를 맞춘 consistent bundle

주 분석에서 데이터셋을 무리하게 pooling하지 말고, 동일 방향의 효과가 몇 개 자원에서 복제되는지 보고한다.

### 4.5 최소대조 개입 세트

| 개입 | 고정하는 것 | 바꾸는 것 | 검증 대상 |
|---|---|---|---|
| conflict toggle | 주제ㆍ길이ㆍ정답ㆍ문체 | 한 claim의 양립 가능성 | contradiction sensitivity |
| relevance twin | 문서 bundle | 질문만 변경 | query-conditioned detection |
| order swap | 모든 내용 | 문서 순서 | position shortcut |
| duplication | 독립 정보량 | 동일 주장의 표면 문서 수 | fake majority |
| source swap | claim text | source/author label | authority heuristic |
| time swap | claim text | publication/validity time | recency heuristic |
| span deletion | 나머지 문서와 정답 후보 | 선택 근거 제거 | causal evidence use |
| oracle stage | instance | localization/type/action 제공 | 병목 위치 |

### 4.6 출력과 평가

단일 EM/F1 대신 identification AUROC/AUPRC, localization F1, conflict relation과 resolvability, source attribution, action appropriateness, answer correctness/completeness, stage transition, intervention flip, risk–coverage, 토큰ㆍ호출ㆍlatency를 분리한다. 적절한 행동은 유형 라벨로 자동 결정하지 말고 독립 human annotation과 오류 비용 시나리오로 검증한다.

### 4.7 예상 비판과 선제 대응

| 예상 리뷰 | 대응 |
|---|---|
| “CoT는 faithful하지 않다” | trace를 내부 상태로 주장하지 않고 행동 산출물로만 사용; 핵심 근거는 개입 |
| “이미 ConfRAG/CONFLICTS가 평가했다” | 최종 응답 적절성이 아니라 stage decomposition과 causal factor isolation이 기여 |
| “여러 데이터셋 benchmark일 뿐” | counterfactual twin과 oracle-stage recovery로 원인적 주장 검증 |
| “충돌을 말하지 않아도 정답이면 충분하다” | silent correct와 grounded correct의 후속 개입 robustness를 비교 |
| “LLM judge가 편향됐다” | 규칙 지표, 독립 judge 교차, blind human subset, option swap |
| “추가 연산이 성능 원인이다” | 동일 토큰ㆍ호출 예산 baseline 필수화 |

### 4.8 Go/No-Go 기준

다음 세 조건 중 두 개 이상이 여러 모델ㆍ자연 데이터에서 재현돼야 ACL main으로 확장한다.

1. 정답과 recognition/localization 사이에 실질적 분리가 존재한다.
2. 최소대조 개입에서 기존 conflict signal이 contradiction 이외 요인에 일관되게 반응한다.
3. gold intermediate stage를 제공했을 때 특정 병목에서 큰 회복이 나타난다.

재현되지 않으면 Findings/분석 논문으로 축소하거나 가장 큰 오류 단계 하나만 방법론으로 전환한다.

---

## 5. 연구 포트폴리오 권고

### Paper 1: 지금 진행

**탐지-행동 간극 + 충돌 신호의 인과적 감사**

- 기존 AIR 코드ㆍ라벨ㆍ파일럿을 가장 많이 재사용한다.
- 유형, 개수, 순서, source, multi-hop을 각각 독립 논문이 아니라 stress factor로 통합한다.
- 새 resolver보다 무엇이 실제 병목인지 틀리지 않게 측정하는 것이 첫 기여다.

### Paper 2: Paper 1 결과에 따라 선택

- 병목이 semantic compilation이면 03의 LatticeConf / Q-GloCo 방향
- 병목이 fake majorityㆍsource heuristic이면 lineage-aware evidence aggregation
- 병목이 action/realization이면 cost-sensitive conflict action policy

장기 메모리는 외부 문서 논문의 하위 실험으로 억지로 합치지 않는다. 현재 관측된 order-robust multi-slot 문제를 독립 agent-memory 트랙으로 보존하되 frontier model과 자연 대화에서 재현된 뒤 재개한다.

---

## 6. 최종 의사결정

### 지금 버릴 것

- 유형×개수 상관을 중심 기여로 삼는 안
- 자연 검색에서 K>1,H>1이 흔하다는 전제
- memory policy heterogeneity가 고유 난이도라는 전제
- graph만 만들면 전역 충돌이 해결된다는 전제
- 자유형 reasoning 문장을 실제 내부 인지의 직접 증거로 쓰는 안

### 남길 것

- 유형과 개수: 통제 변수ㆍstress regime
- 메모리: 별도 응용 검증 또는 후속 트랙
- 멀티홉: semantic compilation 오류를 증폭시키는 고난도 시험대
- 그래프: uncertainty와 source grounding을 보존하는 표현
- AIR: 정답 이면의 경로를 감사하는 중심 문제의식

### 한 문장 연구 전략

> 먼저 외부 문서 충돌에서 “맞혔다”와 “충돌을 올바르게 처리했다”를 인과적으로 분리하고, 가장 큰 병목이 탐지ㆍ의미구조 복원ㆍ증거 집계ㆍ행동 중 어디인지 확인한 뒤, 해당 병목 하나에만 방법론 기여를 집중한다.

이 순서가 현재 프로젝트의 실험 자산을 가장 잘 살리면서, 이미 선점된 유형ㆍ개수ㆍ일반 메모리ㆍ단순 그래프 해결 연구와의 중복을 최소화한다.

---

## 7. 핵심 참고문헌 묶음

### 종합ㆍ기초

- [Knowledge Conflicts for LLMs: A Survey](https://aclanthology.org/2024.emnlp-main.486/)
- [Tug-of-War between Knowledge](https://aclanthology.org/2024.lrec-main.1466/)
- [ECON](https://aclanthology.org/2024.emnlp-main.447/)

### 자연 외부 문서와 행동

- [WikiContradict](https://proceedings.neurips.cc/paper_files/paper/2024/hash/c63819755591ea972f8570beffca6b1b-Abstract-Datasets_and_Benchmarks_Track.html)
- [ConflictingQA](https://aclanthology.org/2024.acl-long.403/)
- [WhoQA](https://aclanthology.org/2024.findings-emnlp.593/)
- [QACC](https://aclanthology.org/2025.findings-naacl.99/)
- [CONFLICTS](https://arxiv.org/abs/2506.08500)
- [ConfRAG](https://aclanthology.org/2026.acl-long.11/)
- [GroupQA](https://aclanthology.org/2026.findings-acl.2003/)

### 구조ㆍ멀티홉ㆍ전역성

- [Contradiction Detection in RAG Systems](https://arxiv.org/abs/2504.00180)
- [MAGIC](https://aclanthology.org/2025.findings-emnlp.466/)
- [Ragability](https://aclanthology.org/2026.lrec-1.182/)
- [Global Consistency with Noisy LLM Oracles](https://arxiv.org/abs/2601.13600)
- [ArbGraph](https://arxiv.org/abs/2604.18362)
- [KCR](https://aclanthology.org/2026.acl-long.1451/)

### 시간ㆍ출처ㆍ불확실성

- [Do Metadata and Appearance Affect RAG?](https://aclanthology.org/2024.blackboxnlp-1.24/)
- [Whose Facts Win?](https://arxiv.org/abs/2601.03746)
- [When Facts Change](https://aclanthology.org/2026.findings-acl.103/)
- [FRESCO](https://arxiv.org/abs/2604.14227)
- [When Evidence Conflicts](https://arxiv.org/abs/2605.14115)
- [ConflictScore](https://arxiv.org/abs/2606.26437)
- [EvidentialRAG](https://arxiv.org/abs/2607.10491)

### 메모리ㆍ보안ㆍ멀티모달 경계

- [MemConflict](https://arxiv.org/abs/2605.20926)
- [STALE](https://arxiv.org/abs/2605.06527)
- [TANGLE](https://arxiv.org/abs/2608.13921)
- [PoisonedRAG](https://www.usenix.org/conference/usenixsecurity25/presentation/zou-poisonedrag)
- [PURPOSE](https://arxiv.org/abs/2608.04756)
- [MMIR](https://aclanthology.org/2025.findings-acl.964/)
- [VLM-DeflectionBench](https://aclanthology.org/2026.acl-long.1307/)

