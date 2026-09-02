# Pilot A · Oracle-Gap Attribution for Multi-Hop Conflict

작성일: 2026-08-31  
수정일: 2026-09-01  
상태: 축소 파일럿 / ProofWriter NatLang dry run 구조 검증 PASSㆍ의미 검수 전
상위 연구: [03 · Query-Conditioned Global Conflict from Documents](../README.md)
선행 근거: [기존 연구로 검증된 사실과 남은 공백](prior_validated_findings.md)

## 1. 파일럿의 역할

기존 연구는 다음 현상을 이미 보였다.

- multi-hop conflict는 single-hop conflict보다 탐지와 국소화가 어렵다.
- 충돌이 여러 개면 탐지는 쉬워질 수 있지만 전체 위치를 찾기는 어려워진다.
- multi-step prompt는 단순 binary prompt보다 강할 수 있다.
- 세 문서를 함께 봐야 드러나는 conditional contradiction이 존재한다.
- pairwise consistency는 global consistency를 보장하지 않는다.
- atomic claim 또는 KG 기반 충돌 처리 방법이 유용할 수 있다.

따라서 본 파일럿은 이 사실들을 다시 증명하지 않는다. 핵심 질문은 하나다.

> Proof가 검증된 multi-hop 문서 충돌에서 모델의 실패는 evidence selection, semantic compilation, graph organization, proof search 중 어디에서 처음 발생하는가?

동일 사례에 정보량을 통제한 oracle representation을 단계적으로 제공해 최초 병목을 분해한다. 이 결과가 있어야 후속 해결 방법을 claim compiler, graph constructor, proof search 중 어디에 집중할지 정할 수 있다.

## 2. 연구 범위

### 포함

- multi-hop inter-context conflict의 exact localization과 proof validity
- 동일 사례의 `raw → gold evidence → canonical claims → graph → proof skeleton` 개입
- 개입 단계별 성능 회복량과 최초 오류 위치
- 최신 공개ㆍAPI 모델에서 병목의 재현성

### 제외

- single-hop보다 multi-hop이 어렵다는 재검증
- conflict 개수별 일반 성능 곡선 재검증
- prompt engineering 자체의 비교 연구
- conditional/higher-order conflict의 존재 증명
- 단순히 graph 입력이 raw text보다 낫다는 비교
- LatticeConf 또는 새로운 학습 방법의 구현
- query twin과 answer-relevant action의 본실험

## 3. 핵심 연구 질문

### P-RQ1. Evidence selection gap

전체 문맥 대신 gold source sentences만 제공하면 fully valid conflict certificate가 얼마나 회복되는가?

### P-RQ2. Semantic compilation gap

Gold source sentences를 정보-equivalent한 canonical claims로 변환해 제공하면 추가 회복이 발생하는가?

### P-RQ3. Representation과 graph organization의 효과를 분리할 수 있는가?

동일 atomic facts를 canonical prose와 triplet serialization으로 각각 제공했을 때 차이가 있는가? Triplet에 graph adjacency를 추가하면 그 이후에도 회복이 발생하는가?

### P-RQ4. Proof-search gap

Gold graph가 주어진 뒤 proof skeleton을 제공하면 추가 회복이 발생하는가?

## 4. 사전 estimand와 가설

### Primary estimand

```text
SelectionGap       = Score(C1 Gold Evidence) - Score(C0 Raw)
CanonicalizationGap= Score(C2 Canonical Prose) - Score(C1 Gold Evidence)
SerializationGap   = Score(C2T Gold Triples) - Score(C2 Canonical Prose)
GraphGap           = Score(C3 Gold Graph) - Score(C2T Gold Triples)
ProofSearchGap     = Score(C4 Proof Skeleton) - Score(C3 Gold Graph)
ResidualGap        = Oracle ceiling - Score(C4 Proof Skeleton)
```

Primary score는 60개 conflict subset의 **fully valid conflict certificate rate**다. 인접 oracle gap도 이 subset에서 계산한다. 20개 no-conflict control은 conflict macro F1와 false positive rate에만 사용한다.

### H1 · Semantic compilation bottleneck

최소 두 모델에서 `CanonicalizationGap ≥ 10%p`이고, 그중 한 모델 이상에서 paired bootstrap 95% CI의 하한이 0보다 크다.

### H2 · Serialization-only explanation 배제

`C2T - C2`가 전체 `C3 - C1` 회복량의 절반 미만이어야 한다. 그렇지 않으면 발견은 semantic compilation이 아니라 단순한 triplet 형식 또는 token 압축 효과일 수 있다.

H1--H2가 지지되지 않아도 파일럿은 GraphGap 또는 ProofSearchGap을 통해 다른 방법론 방향을 선택할 수 있다.

### Secondary diagnostic · Single-hop calibration

20개 single-hop calibration set에서 oracle gap의 방향과 단계별 순위를 비교한다. 표본이 작으므로 5%p 차이 같은 confirmatory threshold를 두지 않으며, “multi-hop-specific” 효과를 주장하는 근거로 사용하지 않는다. Multi-hop에서 유의한 병목을 발견한 경우에만 본실험에서 충분한 matched single-hop 표본을 추가해 interaction을 검정한다.

## 5. 데이터

### 5.1 핵심 원천: ProofWriter OWA/NatLang

[ProofWriter](https://aclanthology.org/2021.findings-acl.317/)는 그 자체로 문서 간 충돌 데이터셋이 아니다. 자연어 사실과 규칙으로부터 결론을 여러 단계에 걸쳐 도출하고, 그 정답 proof를 함께 제공하는 통제 추론 데이터셋이다. C0--C2 semantic compilation 비교에는 사람이 패러프레이즈한 문장과 canonical fact/rule mapping을 함께 제공하는 `OWA/NatLang`을 사용한다. 일반 synthetic `OWA/depth-5`는 후보 가용성과 구조 검사용 보조 원천으로만 사용한다.

본 파일럿은 ProofWriter를 그대로 평가하지 않고 다음과 같이 **multi-hop inter-context conflict로 변환**한다.

1. Gold proof 길이가 2--4단계인 결론 `h`와 그 전제ㆍ규칙을 고른다.
2. 전제와 규칙을 2--3개 source document에 나누어 배치한다.
3. 별도 document에 `not h`를 명시한다.
4. 앞 문서들을 따라 `h`를 도출해야만 `h`와 `not h`의 충돌을 발견할 수 있게 한다.
5. 원래 proof, 사용한 rule ID, source sentence ID, 최종 양립 불가능한 두 claim을 gold certificate로 보존한다.

예시는 다음과 같다.

```text
Document A: 모든 차분한 대상은 푸르다. 리오는 차분하다.
Document B: 모든 푸른 대상은 젊다.
Document C: 리오는 젊지 않다.

A와 B에서 '리오는 젊다'를 2-hop으로 도출해야 C와의 충돌이 드러난다.
```

따라서 이 데이터의 장점은 “원래부터 충돌 데이터”라는 점이 아니라, **우리가 만든 충돌의 추론 경로가 논리적으로 맞는지 기계적으로 검증할 수 있다는 점**이다.

사용 후보 필드는 배포본 확인 후 exact schema를 manifest에 동결하되, 최소한 다음 정보를 요구한다.

- theory의 natural-language facts와 rules
- query/target claim과 polarity
- 정답 label
- proof 또는 proof graph
- proof depth/length

공식 V2020.12.3의 checksum은 고정했다. 아카이브와 README에는 명시적 라이선스가 없으므로 확인 전까지 원본 문장ㆍJSONL은 재배포하지 않고, source IDㆍ변환 scriptㆍ비원문 통계만 추적한다.

### 5.2 변환 단위와 생성 규칙

#### Conflict 사례

- 실제 사용된 rule 수 기준 2-hop, 3-hop, 4-hop을 각각 20개씩 구성한다.
- 공식 depth split 이름만 믿지 않고 각 gold proof를 replay해 실제 hop을 다시 계산한다.
- proof에 필요하지 않은 사실과 규칙을 distractor로 추가하되, 추가된 사실로 더 짧은 대체 proof가 생기지 않아야 한다.
- premise와 rule을 여러 문서에 나누되, 어느 한 문서만으로 결론이 완성되지 않게 한다.
- NatLang의 증명 가능한 target은 양의 claim이므로 conflict에는 `not h`를 terminal로 추가한다. No-conflict에도 같은 형태의 음수 terminal을 넣어 부정어가 label 단서가 되지 않게 한다.
- 같은 theory의 중복을 제거하고 source split, 문장 길이, proof shape를 가능한 범위에서 균형화한다.
- NatLang은 단항 속성 추론에 치우치므로 binary relation과 실제 문서 일반화는 외부 전이 평가에서 반드시 확인한다.

#### Paired no-conflict control

- 동일 proof chain과 동일한 문서 수ㆍ문장 수ㆍ부정 표현 수를 유지한다.
- terminal document만 proof 결론과 양립 가능한 claim으로 교체한다.
- conflict/control 쌍 사이의 token 길이와 표면 template을 맞춘다.
- Conflict와 control 모두 음수 terminal을 하나씩 포함시켜 negation 빈도를 label별로 일치시킨다.
- 자동 논리 검사로 전체 theory가 일관적인지 확인한다.

#### 문서화

- ProofWriter 문장을 그대로 한 덩어리 theory로 주지 않고, source가 구분된 짧은 문서로 재구성한다.
- 각 문장에 source sentence ID를 부여한다.
- C0에는 proof와 무관한 distractor를 포함하고 C1에는 gold source sentences만 남긴다.
- 문장을 유창하게 바꾸는 naturalization은 별도 변형으로 관리한다. 원 의미와 양방향 entailment가 확인되지 않은 paraphrase는 core에 넣지 않는다.

### 5.3 Controlled diagnostic core: 80개

| 구성 | 수량 | 역할 |
|---|---:|---|
| multi-hop conflict | 60 | 주 분석 |
| matched multi-hop no-conflict | 20 | false positive와 label leakage 통제 |
| 합계 | 80 | 통제된 병목 원인 분해 |

#### Multi-hop conflict 표집

- 2-hop, 3-hop, 4-hop에서 각각 20개를 구성한다.
- seed `20260901`로 후보 theory 순서를 먼저 고정한다.
- source split, proof shape, context token 길이를 보조 층으로 사용한다.
- 동일 theory에서 여러 query를 중복 채택하지 않는다.
- proof replay, terminal incompatibility, source coverage를 모두 통과한 사례만 포함한다.
- 제외 사유와 다음 대체 후보를 manifest에 남기고, 어떤 평가 모델 출력도 보기 전에 60개를 동결한다.
- 주 결과는 hop별 macro 평균과 전체 micro 평균을 함께 보고한다.

#### No-conflict control

- 2-hop 7개, 3-hop 7개, 4-hop 6개의 conflict 사례와 짝을 이룬 control을 만든다.
- proof chain은 유지하고 terminal claim만 양립 가능한 claim으로 바꾼다.
- 문장 수, token 길이, terminal polarity, proof shape를 맞춘다.
- 두 연구자가 conflict/consistent/ambiguous를 독립 판정한다.
- 합의하지 못한 control은 제외하고 교체한다.

### 5.4 Single-hop calibration: 20개

Single-hop은 선행 결과 재현이 아니라 병목 순서가 multi-hop에만 나타나는지 보는 보조 진단으로만 사용한다.

- ProofWriter의 실제 1-rule proof에서 conflict 16개와 paired no-conflict 4개를 만든다.
- C0, C1, C2, C2T, C3만 평가하고 C4는 생략한다.
- single/multi-hop 절대 성능 차이를 새로운 발견으로 주장하지 않는다.

### 5.5 자연 충돌 후보의 한계(멀티홉 평가 아님)

현재 확인된 공개 데이터 중 자연 텍스트 문서, 문서 간 충돌, 2-hop 이상 proof, 충돌 근거와 proof gold를 동시에 만족하는 fixed-context 데이터셋은 확인하지 못했다. 아래 두 데이터는 자연 충돌 후보일 뿐 멀티홉 충돌 평가셋이 아니다.

#### WikiContradict: 자연 충돌 calibration 후보

[WikiContradict](https://huggingface.co/datasets/ibm-research/Wikipedia_contradict_benchmark)는 Wikipedia 편집자가 표시한 실제 내용 불일치를 사람이 검증한 데이터다. 253개 고유 conflict에 `context1`, `context2`, 문맥별 `answer1`, `answer2`, `Explicit`/`Implicit (reasoning required)` label을 제공한다.

- multi-hop 본평가에서는 제외
- calibration에 사용할 경우 `question_ID`가 겹치지 않는 사례만 선택
- 두 context가 질문에 대해 실제로 다른 답을 지지하는지 재검수
- `Implicit (reasoning required)` label을 2-hop 이상의 근거로 간주하지 않으며 multi-hop 평가 수치에 합산하지 않음
- source span, canonical claim, answer-relevant terminal conflict를 두 사람이 주석

#### ConfRAG: 자연 상충 답변 calibration 후보

[ConfRAG](https://huggingface.co/datasets/OracleY/ConfRAG)는 실제 웹 장문을 검색해 만든 1,814문항 데이터다. 각 문항에 3--10개 web document, 문서별 answer/reason, 2--8개 answer cluster와 supporting website index가 있다.

- `ConfRAGsuggested.jsonl`의 `contradicts=true`만 사용
- multi-hop 본평가에서는 제외
- calibration에 사용할 경우 최소 두 answer cluster가 있고 각 cluster가 서로 다른 website evidence로 지지되는 사례만 사용
- 여러 answer cluster와 reason만으로 multi-hop proof가 보장되지 않으므로 multi-hop 평가 수치에 합산하지 않음
- source URLㆍ문서ㆍ근거 문장이 보존된 사례만 사용
- source span, canonical claim, answer cluster와 terminal conflict를 두 사람이 주석

#### 멀티홉 평가에서의 역할

- Ragability는 WikiContradict 43개 conflict를 fantasy entity로 바꾼 파생셋이므로 중복을 피하기 위해 제외한다.
- MAGIC은 multi-hop conflict 직접 관련 외부 벤치마크로 사용하되 자연문서 외적 타당성 근거로 부르지 않는다. 사용할 사례 수는 proof audit 후 결정한다.
- EX-FEVER와 HoVer는 자연 멀티홉 evidence를 제공하지만 문서 간 충돌 gold가 아니라 claim verification 데이터이므로 자연 conflict 평가로 세지 않는다.
- MERRIN은 자연 web의 multi-hop 추론과 noisy/conflicting 환경을 다루지만, 문항별 text-only inter-document conflict proof gold를 보장하는 fixed-context 벤치마크가 아니므로 직접 평가에서 제외한다.

WikiContradict와 ConfRAG을 사용하는 별도 calibration은 자연 충돌 일반화만 보조적으로 확인하며, multi-hop 성능이나 proof-search 결론에는 사용하지 않는다.

**정정:** WikiContradict 100개 + ConfRAG 200개를 자연 multi-hop conflict 300개로 간주하던 계획은 폐기한다. 두 데이터셋에는 hop 수와 전체 conflict proof gold가 없으므로, 선별만으로 엄격한 multi-hop 데이터가 된다고 보장할 수 없다. 파일럿 외부 비교는 MAGIC 감사 통과 사례로 제한한다. 자연 multi-hop 평가는 별도의 수집·주석 타당성 파일럿에서 최소 두 문서, 두 개 이상의 추론 step, single-document insufficiency, source-grounded proof를 검증한 뒤에만 추가한다.

### 5.6 데이터 수용 기준

평가 모델을 실행하기 전에 다음을 모두 통과해야 한다.

1. Gold proof를 symbolic replay했을 때 target conclusion이 도출된다.
2. Conflict 사례에서는 target과 terminal claim이 정확한 polarity 반대다.
3. No-conflict control의 전체 fact/rule 집합은 일관적이다.
4. 2-hop 이상 사례는 어느 한 문서만으로 target을 도출할 수 없다.
5. C0 원문에 proof의 모든 premise와 rule이 실제로 표현되어 있다.
6. C1--C4가 C0에 없던 사실을 추가하지 않는다.
7. Conflict와 control 사이의 negationㆍ길이ㆍ문서 수 차이로 label을 예측할 수 없다.
8. 20개 blind sample에서 두 주석자가 proof validity와 conflict label에 합의한다.

한 항목이라도 구조적으로 실패하면 모델 실행보다 생성 규칙을 먼저 수정한다.

### 5.7 True higher-order set

이번 파일럿에서는 만들지 않는다. Conditional contradiction의 존재와 난도는 선행연구가 이미 보였다. 이후 방법이 minimal conflict certificate를 직접 목표로 할 때만 별도의 평가 세트를 설계한다.

## 6. Oracle ladder

### C0 · Raw Documents

- sentence ID가 붙은 `context1`, `context2` 전체
- 충돌과 무관한 문장 포함
- end-to-end 실패 측정

### C1 · Gold Evidence

- C0에서 proof에 필요한 원문 문장만 제공
- 문장은 수정하거나 정규화하지 않음
- evidence selection, 길이, distractor 영향을 제거

### C2 · Gold Canonical Prose

- C1의 각 의미 단위를 짧고 명시적인 자연어 atomic claim으로 제공
- entity alias를 canonical entity ID 또는 동일 이름으로 정렬
- 원문에 없는 관계나 전제를 추가하지 않음
- text-to-claim canonicalization 오류를 제거하되 tuple 형식 이점은 주지 않음

### C2T · Gold Triples

- C2와 정확히 같은 atomic facts를 `(subject, relation, object)`로 직렬화
- time, modality, condition이 필요한 경우 별도 slot 사용
- C2와 fact 수ㆍ순서ㆍentity 표기를 동일하게 유지
- canonicalization 효과와 serialization 효과를 분리

### C3 · Gold Graph

- C2T의 fact를 그대로 사용
- node identity와 adjacency만 추가
- derived conclusion, conflict edge, 정답 path는 제공하지 않음
- 새로운 사실을 추가하지 않음

### C4 · Gold Proof Skeleton

- 필요한 premise node와 inference edge의 순서만 제공
- 중간 결론의 정답 문장과 terminal conflict 판정은 제공하지 않음
- proof path 탐색을 제거하고 step execution과 최종 incompatibility 판단만 남김

## 7. 정보 등가성과 누설 방지

Oracle gap이 의미를 가지려면 뒤 조건이 더 많은 사실을 제공해서는 안 된다.

### 필수 검사

1. C1의 모든 의미 단위가 C0 source sentence에 근거하는가?
2. C2/C2T의 모든 claim이 C1에서 양방향 entail되는가?
3. C2와 C2T의 fact inventory가 동일한가?
4. C3가 adjacency 외 새로운 factual content를 추가하지 않는가?
5. C4가 terminal conflict label 또는 최종 결론을 누설하지 않는가?

### 통제

- 모든 조건에서 사실 순서를 동일 seed로 무작위화한다.
- `original`, `perturb`, `conflict`, `gold` 같은 역할 이름을 제거한다.
- 20개를 두 연구자가 blind review한다.
- token 수와 fact 수를 조건별로 보고한다.
- C1과 C2의 길이 차이가 큰 경우 length를 공변량으로 보고하고 matched-length subset을 별도 분석한다.
- C2와 C2T 차이를 통해 구조화 효과가 단순 serialization 효과인지 확인한다.

정보 등가성 위반이 10%를 넘으면 본 실행 전에 oracle 제작 규칙을 수정한다.

## 8. 출력과 gold certificate

모든 조건에서 동일한 출력 schema를 사용한다.

```json
{
  "conflict": true,
  "source_evidence": ["A:S2", "B:S4"],
  "atomic_claims": ["c1", "c2"],
  "derived_claims": ["d1"],
  "proof_steps": [
    {"premises": ["c1", "c2"], "conclusion": "d1"}
  ],
  "terminal_incompatibility": ["d1", "c3"],
  "confidence": 0.0
}
```

Gold certificate는 다음을 포함한다.

- 최소 또는 충분 source evidence set
- information-equivalent canonical claims
- entity/relation alignment
- 필요한 graph edges
- proof skeleton
- terminal incompatible claims

## 9. 평가

### Primary

**Fully valid conflict certificate rate**: 아래 항목을 모두 만족한 사례의 비율이다.

1. conflict label 정확
2. sufficient source evidence 포함
3. unsupported evidence 없음
4. 모든 proof step 유효
5. terminal claims가 실제로 양립 불가능

### Secondary

- conflict macro F1
- exact source-evidence-set accuracy
- claim inventory F1
- proof edge F1
- terminal incompatibility accuracy
- unsupported assumption rate
- no-conflict false positive rate

MAGIC의 기존 ID/LOC 수치를 다시 논문의 핵심 결과로 보고하지 않는다.

## 10. 모델 선정과 prompt

### 10.1 선정 원칙

모델은 로컬 보유 여부가 아니라 다음 네 실험적 역할로 선정한다.

1. **충돌 문헌 anchor**: MAGIC 등 선행 충돌 연구가 평가한 계열ㆍ크기와 연결되는가?
2. **같은 계열 규모 통제**: 모델 family를 고정하고 8B→32B 규모 증가를 비교할 수 있는가?
3. **계열 일반화**: Qwen 이외의 decoder family에서도 oracle gap이 재현되는가?
4. **reasoning 통제**: 서로 다른 모델을 비교하는 대신 동일 가중치의 thinking off/on으로 추론 모드 효과를 분리할 수 있는가?

[MAGIC](https://aclanthology.org/2025.findings-emnlp.466/)는 `Mixtral-8x7B-Instruct`, `Llama-3.1-70B-Instruct`, Claude 3.5 Haiku, GPT-4o-mini, o1을 평가했다. 부록의 소형 Mistral-7B/Llama-3.1-8B와 70B급 결과 사이에는 큰 격차가 있었고, o1이 GPT-4o-mini보다 항상 강하지 않아 “reasoning 모델이면 해결된다”는 결론을 지지하지 않았다. [Contradiction Detection in RAG Systems](https://arxiv.org/abs/2504.00180)도 대체로 큰 모델이 더 강하지만 CoT 효과는 architecture에 따라 달라진다고 보고한다. 더 최근의 [Global Consistency with Noisy LLM Oracles](https://arxiv.org/abs/2601.13600)는 Claude, DeepSeek-R1, GPT-OSS, Mistral Large처럼 계열과 reasoning 특성이 다른 모델에 걸쳐 방법을 검증했다. 따라서 단일 최신 모델 여러 개를 나열하기보다 **문헌 anchor + within-family scale + cross-family + reasoning-mode control**이 이 파일럿의 원인 분해에 더 적합하다.

### 10.2 Confirmatory model panel

| 역할 | 정확한 모델 | 규모/설정 | 선정 근거 |
|---|---|---|---|
| small open | `Qwen/Qwen3-8B` | 8B, BF16, thinking off | 최근 multi-hop/RAG 연구에서 널리 쓰이는 Qwen 7--8B급의 현실적 배포 기준점 |
| within-family scale-up | `Qwen/Qwen3-32B` | 32B, BF16, thinking off | 8B와 familyㆍprompt를 고정해 규모만 커졌을 때 병목이 남는지 확인 |
| cross-family mid-size | `mistralai/Mistral-Small-3.2-24B-Instruct-2506` | 24B, BF16 | MAGIC의 Mistral/Mixtral 계열과 연결하면서 Qwen 결과의 family 특이성을 배제 |
| literature anchor | `hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4` | 70B, AWQ INT4 | MAGIC의 `Llama-3.1-70B-Instruct`와 직접 계열ㆍ규모 비교가 가능한 anchor |

Llama 70B는 양자화 artifact이므로 BF16 모델과 절대 성능의 공정한 규모 곡선으로 해석하지 않는다. 역할은 MAGIC와의 family/size anchor 및 gap 방향 복제다. 주 가설은 “네 모델 중 최소 두 모델에서 재현”으로 판단하며, pooled 평균 하나로 모델 이질성을 감추지 않는다.

실행 전 manifest에 exact Hugging Face revision을 고정한다. 현재 재사용 가능한 revision은 Qwen3-8B `b968826d9c46dd6066d109eabc6255188de91218`, Qwen3-32B `9216db5781bf` local snapshot, Llama-3.1-70B-AWQ `2123003760781134cfc31124aa6560a45b491fdf`다. Mistral은 첫 출력 생성 전에 로컬 snapshot의 full commit SHA를 기록하고, 이후 변경하지 않는다.

### 10.3 Reasoning sensitivity

`Qwen/Qwen3-32B`의 동일 checkpoint를 thinking on으로 추가 실행한다. 모델 family와 parameter count를 그대로 둔 채 reasoning mode만 바꾸기 위한 분석이며 confirmatory 4-model 평균에는 포함하지 않는다.

- 대상: multi-hop conflict 60개
- 조건: C0, C2, C3, C4
- `max_tokens=6000`
- 이전 실행에서 4,000-token thinking budget을 소진한 사례가 있었으므로 parse 실패와 budget exhaustion을 오류로 유지하고 별도 비율을 보고한다.

### 10.4 독점 API 모델의 위치

독점 API 모델은 Pilot A의 Go/No-Go 필수 조건에서 제외한다. 현재 실행 자격 증명이 없고, API snapshot이 바뀌면 원인 분해보다 버전 차이가 섞이기 때문이다. 다만 ACL 본실험으로 확장할 경우에는 당시 사용 가능한 **비-reasoning frontier 1개와 reasoning frontier 1개**를 exact dated snapshot으로 사전 등록해 외적 타당성을 확인한다. 이것은 파일럿 성공 뒤의 확인 실험이지, open model에서 실패한 가설을 구제하는 분석이 아니다.

### 10.5 Prompt와 decoding

- 하나의 structured reasoning prompt를 모든 oracle 조건에 공통 사용한다.
- direct vs. CoT 비교를 연구 질문으로 두지 않는다.
- prompt는 20개 dry run 전에 고정하고 core 결과를 본 뒤 수정하지 않는다.
- confirmatory panel은 `temperature=0`, `seed=20260901`, `max_tokens=1400`으로 고정한다.
- invalid JSON은 같은 prompt로 한 번만 deterministic retry하고, 최초 실패를 primary denominator에서 제거하지 않는다.
- 단일 H100 80GB에서 모델별로 순차 serving하며 동시 요청 수는 16으로 고정한다. vLLM version과 chat template hash를 manifest에 기록한다.

Pairwise NLI, MUS, ArbGraph, LatticeConf는 파일럿의 원인 분해에 필수가 아니므로 구현하지 않는다. 후속 방법을 결정한 뒤 본실험 기준선으로 추가한다.

## 11. 분석

### Paired oracle-gap analysis

- 동일 instance의 인접 조건 차이를 paired bootstrap으로 비교한다.
- 95% CI와 효과 크기를 함께 보고한다.
- 모델별 결과와 pooled 결과를 모두 보고한다.

### First-failure attribution

최소 50개 오류를 다음 최초 실패 지점으로 분류한다.

1. evidence selection
2. claim canonicalization
3. entity/relation alignment
4. graph composition
5. proof path search
6. inference-step execution
7. terminal conflict judgment
8. output parsing

20개는 두 연구자가 독립 분류하고 합의도를 보고한다.

### Confound audit

- input token 수
- fact 수
- relation family
- path length
- context order
- model output 길이

`C2 - C1`이 input 길이만으로 설명되는지 matched-length subset과 회귀 보조 분석으로 확인한다.

## 12. Go/No-Go

### Go A · Semantic compilation 방법

- H1 충족
- H2 충족
- 수동 오류의 35% 이상이 canonicalization/alignment에서 최초 발생
- C4에서 residual gap이 작아 올바른 representation이 주어지면 reasoning 가능

이 경우 uncertainty-aware claim compilation, multiple semantic hypotheses 또는 source-grounded compiler를 후속 방법으로 검토한다.

### Go B · Graph/proof 방법으로 피벗

- `CanonicalizationGap < 5%p`
- `GraphGap` 또는 `ProofSearchGap ≥ 10%p`
- 오류 다수가 graph composition 또는 proof path search에서 최초 발생

이 경우 semantic lattice 주장을 약화하고 conflict-specific graph organization, certificate search 또는 verifier를 후속 방법으로 검토한다.

### Partial Go · Selection/attention 문제

- SelectionGap만 크고 이후 gap은 모두 5%p 미만

이 경우 semantic compilation 신규성은 약하다. conflict-aware evidence selection 또는 long-context attention 연구와의 중복을 다시 검토한다.

### No-Go

- 강한 두 모델의 C0 fully valid certificate rate가 모두 85% 이상
- 모든 인접 oracle gap이 5%p 미만
- 관찰된 회복이 C2T serialization 또는 token 길이로 대부분 설명됨
- oracle representation의 정보 등가성을 안정적으로 확보하지 못함
- C4에서도 unsupported reasoning이 광범위하게 남아 gold schema 자체가 불안정함

## 13. 예상 실행량

```text
Confirmatory core: 80 × 6 conditions × 4 models = 1,920 calls
Single-hop calibration: 20 × 5 conditions × 4 models = 400 calls
Qwen3-32B thinking sensitivity: 60 × 4 conditions = 240 calls
총 고정 실행량: 2,560 calls
```

2,560은 동결된 설정의 primary calls 수다. Prompt 동결 전에 폐기한 setup call과 invalid JSON retry는 별도 집계한다. Dry run 20개는 prompt가 바뀌면 동결 후 다시 실행하고 최종 primary calls에 포함한다. Natural transfer는 Go 이후 `24 × 3 conditions × 4 models = 288 calls`를 별도 실행한다.

## 14. 실행 순서

### Step 0 · 선행 근거 동결

- [prior_validated_findings.md](prior_validated_findings.md)를 인용 근거로 고정
- 이미 검증된 현상을 파일럿 가설이나 신규 기여로 다시 사용하지 않음

### Step 1 · ProofWriter 도입 가능성 확인

- **완료:** 공식 V2020.12.3, schema, checksum 기록
- **완료:** OWA gold proof와 intermediate 구조 확인
- **완료:** 2--4 hop 후보 수 집계와 라이선스 미명시 상태 기록
- 결과: [ProofWriter feasibility audit](proofwriter_feasibility.md) PASS

### Step 2 · 20개 변환ㆍoracle dry run

- multi-hop conflict 15개
- no-conflict 5개
- **완료:** NatLang 기반 15 conflict + 5 paired control 생성
- **완료:** fact/rule 혼합 문서 분할과 독립 forward-chaining replay
- **완료:** C0--C4 구조 작성 및 자동 구조 검사
- **남음:** 사람 semantic-equivalence blind audit
- **남음:** prompt, parser, certificate scorer 고정

### Step 3 · Core 80개

- 층화 표집
- no-conflict control 검증
- confirmatory 모델 4개와 reasoning sensitivity 실행
- paired oracle-gap 분석
- first-failure 오류 분석

### Step 4 · 결정

- Go A / Go B / Partial Go / No-Go 결정문 작성
- Go일 때만 MAGIC 외부 전이를 실행하고 자연 multi-hop conflict 구축 타당성을 별도로 판정
- 결과에 맞춰 상위 README의 연구 질문과 방법론 수정

## 15. 산출물

1. ProofWriter source ID, 변환 규칙, conflict/control manifest
2. C0--C4 oracle inputs와 정보 등가성 audit
3. symbolic proof replay 및 consistency validation 결과
4. 모델 출력과 고정 scorer
5. 단계별 oracle gap과 신뢰구간
6. first-failure attribution 50건
7. Go A / Go B / Partial Go / No-Go 결정문
8. 후속 방법론 범위 수정안

## 16. 해석 제한

파일럿 결과가 좋더라도 다음을 주장하지 않는다.

- multi-hop conflict가 어렵다는 사실을 처음 발견했다.
- conditional 또는 higher-order conflict를 처음 제안했다.
- pairwise consistency의 한계를 처음 보였다.
- graph representation이 항상 raw text보다 우월하다.
- ProofWriter에서 파생한 합성 문서가 실제 웹 문서를 대표한다.
- oracle gap만으로 특정 해결 방법의 효과가 증명되었다.

본 파일럿의 기여는 **이미 알려진 실패 현상을 반복하는 것이 아니라, 그 실패가 처음 생기는 표현ㆍ추론 계층을 통제된 개입으로 식별하는 것**이다.
