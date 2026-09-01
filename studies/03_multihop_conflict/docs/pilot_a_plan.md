# Pilot A · Multi-Hop Conflict Feasibility

작성일: 2026-08-31  
수정일: 2026-09-01  
상태: 축소 파일럿 / 데이터셋 확보 및 표본 감사 전  
상위 연구: [03 · Query-Conditioned Global Conflict from Documents](../README.md)

## 1. 이 파일럿에서 실제로 확인할 것

이 파일럿은 새로운 대규모 벤치마크를 먼저 만드는 실험이 아니다. 공개된 MAGIC의 텍스트와 지식 그래프 구조를 이용해 다음 질문에 최소 비용으로 답한다.

> 여러 문서의 사실을 연결해야만 드러나는 multi-hop conflict에서 모델의 실패는 원문을 구조화된 사실로 변환하는 semantic compilation 때문인가, 아니면 구조화된 사실이 주어진 뒤의 proof reasoning 때문인가?

따라서 본 파일럿의 직접 연구 대상은 **multi-hop inter-document conflict**다. 일반적인 multi-hop QA, 단순 문장쌍 NLI, 충돌 유형 분류를 주 연구 대상으로 삼지 않는다.

Query-conditioning과 pairwise-consistent higher-order conflict는 중요하지만, 기존 공개 데이터가 필요한 gold를 제공하지 않는다. 두 요소는 핵심 결과가 확인된 뒤 소규모 확장 실험으로만 검증한다.

## 2. 왜 계획을 축소하는가

기존 계획은 파일럿 단계에서 다음을 동시에 요구했다.

- controlled instance 240개와 natural instance 40개 제작
- source span, semantic claim, alignment, proof, decision의 전 계층 이중 주석
- query twin, temporal/scope conflict, higher-order conflict 동시 검증
- 네 모델과 여러 기준선에서 약 13,440 model-instance calls

그러나 현재 공개 데이터 중 이 모든 gold를 한 번에 제공하는 데이터셋은 없다. 특히 다음 구조는 직접 제작해야 한다.

```text
모든 proper subset은 consistent
하지만 세 개 이상의 사실을 함께 사용하면 inconsistent
```

따라서 먼저 공개 데이터로 검증 가능한 `multi-hop difficulty`와 `semantic compilation gap`만 본다. 파일럿 결과 없이 240개 데이터 제작이나 LatticeConf 구현을 시작하지 않는다.

## 3. 공개 데이터 가용성 판정

### 3.1 핵심 데이터: MAGIC

[MAGIC](https://huggingface.co/datasets/HYU-NLP/MAGIC)은 총 1,080개 사례와 다음 필드를 공개한다.

- `subgraph`: 원본 KG에서 가져온 주변 triplet
- `original_triplet`: 충돌 형성의 기준 사실
- `perturb_triplet`: 충돌을 만들기 위해 변형된 사실 또는 경로
- `context1`, `context2`: 두 구조를 자연어로 표현한 문맥
- single-hop 및 multi-hop split
- 1--4 conflict 구성

이 구조는 동일 사례에 대해 raw text와 gold symbolic representation을 비교할 수 있으므로 핵심 파일럿에 적합하다.

다만 MAGIC의 `1--4 conflict`는 충돌 개수 조건이지, 모든 쌍은 일관되지만 전체 집합만 모순인 logical arity를 뜻하지 않는다. 또한 질문, query twin, 실제 웹 문서, 정확한 자연문서 span annotation은 제공하지 않는다.

### 3.2 자연문서 sanity check

- [ConfRAG](https://huggingface.co/datasets/OracleY/ConfRAG): 질문, 장문 웹 문서, 문서별 answer/reason, 관점 cluster를 제공한다.
- [WikiContradict](https://huggingface.co/datasets/ibm-research/Wikipedia_contradict_benchmark): 질문, 두 Wikipedia passage, 충돌 위치ㆍ유형과 상충 답변을 제공한다.

두 데이터셋은 자연문서 타당성 확인에는 유용하지만 normalized claim과 multi-hop proof gold는 제공하지 않는다. 따라서 본 파일럿의 주 통계에는 합치지 않고 20건의 수동 sanity set으로만 사용한다.

### 3.3 이번 파일럿에서 사용하지 않는 데이터

- MultiHop-RAG, HotpotQA, 2WikiMultiHopQA, MuSiQue: 보완적 multi-hop QA이며 원래 충돌 데이터가 아니다.
- ECon, DRUID: pairwise evidence conflict 또는 claim-context stance 분석에는 유용하지만 multi-hop conflict proof를 제공하지 않는다.
- Foundations의 VitaminC/FEVER fact cluster: 구조화된 fact 이후의 global consistency 기준선에는 쓸 수 있지만 원문 semantic compilation 실험의 원천 데이터로는 부족하다.

## 4. 연구 질문과 사전 가설

### P-RQ1. Multi-hop conflict가 실제로 더 어려운가?

길이, 충돌 개수, 관계군을 가능한 한 맞췄을 때 raw text 조건의 multi-hop conflict localization이 single-hop보다 낮은가?

**H1:** multi-hop의 exact localization이 single-hop보다 최소 10%p 낮다.

### P-RQ2. Semantic compilation gap이 존재하는가?

동일 모델에 raw text 대신 gold triplet을 주면 multi-hop conflict 판단과 localization이 얼마나 회복되는가?

**H2:** multi-hop에서 gold triplet 조건이 raw text보다 최소 10%p 높다.

### P-RQ3. 구조가 주어진 뒤에도 proof reasoning 오류가 남는가?

Gold triplet에 이어 전체 subgraph를 제공했을 때 추가 회복이 있는가?

**H3:** gold graph가 gold triplet보다 유의하게 높다면 병목의 일부는 compilation이 아니라 graph/proof reasoning에 있다.

### 탐색 질문

- 충돌 개수 1--4가 늘어날 때 누락률이 어떻게 변하는가?
- evidence order를 바꾸면 예측 또는 localization이 바뀌는가?
- 자연 웹 문서에서도 동일한 오류 유형을 관찰할 수 있는가?

Query-conditioning과 true higher-order conflict는 이 파일럿의 confirmatory 가설로 사용하지 않는다.

## 5. 데이터 구성

### 5.1 Core set: 120개

| 구조 | conflict | matched no-conflict | 합계 |
|---|---:|---:|---:|
| single-hop | 40 | 20 | 60 |
| multi-hop | 40 | 20 | 60 |
| 합계 | 80 | 40 | 120 |

#### Conflict 사례

- MAGIC single-hop에서 40개, multi-hop에서 40개를 층화 표집한다.
- 가능한 범위에서 `rel_id`, conflict 개수, context 길이 분포를 맞춘다.
- 동일 entity 또는 거의 동일한 context가 train/dev/test에 중복되지 않도록 표본 ID와 relation을 기록한다.

#### Matched no-conflict 사례

MAGIC에는 conflict 중심 파일만 있으므로 40개 control을 파생한다.

- 동일 subgraph 안에서 양립 가능한 triplet으로 perturb 경로를 교체한다.
- conflict 사례와 문장 수, token 길이, 관계 표현을 맞춘다.
- 단순히 부정어를 삭제한 문장을 control로 사용하지 않는다.
- 생성 후 두 연구자가 independently `consistent / ambiguous / conflicting`을 판정한다.
- 두 연구자가 합의하지 못한 사례는 제외하고 새 사례로 대체한다.

No-conflict control은 detection false positive를 측정하기 위한 것이며 MAGIC 원본 데이터로 표시하지 않고 파생 데이터임을 명시한다.

### 5.2 Natural sanity set: 20개

| 원천 | 수량 | 목적 |
|---|---:|---|
| WikiContradict | 10 | 자연 발생 direct/implicit conflict |
| ConfRAG | 10 | 실제 다중 출처 장문과 질문 관련성 |

각 사례에는 다음 최소 annotation만 추가한다.

- question
- conflict label
- conflict를 지지하는 source span
- direct 또는 multi-hop/implicit 여부
- 현재 질문에 conflict가 관련되는지
- 현재 schema로 proof를 표현할 수 있는지

정규화 claim의 모든 slot이나 완전한 minimal proof는 아직 주석하지 않는다. 이 20개는 성능 순위나 통계적 유의성 주장의 근거로 사용하지 않는다.

### 5.3 Exploratory true higher-order set: 최대 12개

Core 결과가 Go 기준을 통과했을 때만 제작한다.

- temporal/order 4개
- hierarchy/set membership 4개
- conditional/exception 4개

각 사례는 작은 규칙 집합으로 먼저 작성하고 자동 검사한다.

1. 전체 집합은 inconsistent여야 한다.
2. 모든 proper subset은 consistent여야 한다.
3. 외부 상식 없이 proof가 완결되어야 한다.
4. 규칙 검증 후에만 자연어 문서로 paraphrase한다.

12개는 현상 발견용 탐색 사례이며, 일반화된 성능 주장을 위한 benchmark로 사용하지 않는다.

## 6. 입력 조건

Core 120개를 동일 모델과 동일 출력 형식에서 세 조건으로 평가한다.

| 조건 | 입력 | 제거하는 병목 |
|---|---|---|
| C0 Raw | `context1`, `context2`의 자연어 문맥 | 없음: end-to-end |
| C1 Gold Facts | 출처 표시를 제거하고 섞은 gold triplet 집합 | text-to-fact compilation |
| C2 Gold Graph | 섞은 triplet과 필요한 subgraph edge | compilation과 graph construction |

### 누설 방지

- `original_triplet`, `perturb_triplet`, `conflict` 같은 역할 이름을 모델에 보여주지 않는다.
- C1/C2의 사실 순서를 무작위화한다.
- 정답 label이나 최종 충돌 쌍을 직접 제공하지 않는다.
- C2에는 proof 결과가 아니라 proof를 찾는 데 필요한 graph facts만 제공한다.
- 20개를 사람이 검토해 C1/C2만 보고 파일명 또는 표현 관습으로 label을 추측할 수 없는지 확인한다.

## 7. 과제와 출력

질문을 억지로 생성하지 않고 MAGIC의 원래 목적인 conflict detection/localization을 먼저 평가한다.

```json
{
  "conflict": true,
  "evidence": [
    {"source": "context1", "claim": "..."},
    {"source": "context2", "claim": "..."}
  ],
  "derived_claims": [],
  "brief_proof": [],
  "confidence": 0.0
}
```

출력 설명의 문체가 아니라 다음을 채점한다.

- conflict label
- 모든 충돌 근거의 localization
- derived claim 또는 graph path의 정확성
- unsupported assumption 유무

## 8. 모델과 기준선

### 8.1 모델

초기 실행은 세 능력 구간만 사용한다.

1. 7B--14B 공개 instruct 모델 1개
2. 30B--70B 공개 instruct/reasoning 모델 1개
3. frontier API 모델 1개

정확한 모델명, 버전, 실행일, temperature, 최대 출력 token을 RUNLOG에 고정한다. API 비용이 크면 frontier 모델은 core 120개만 실행하고 order permutation은 40개 subset에 한정한다.

### 8.2 기준선

- B0: pairwise NLI 또는 pairwise LLM judge
- B1: full-context direct prompt
- B2: facts → derived claims → conflict 순서의 structured reasoning

Foundations-style MUS와 LatticeConf는 본 파일럿에서 구현하지 않는다. C1/C2에서도 오류가 충분히 남을 때만 이후 단계에서 proof-search 기준선과 제안 방법을 구현한다.

## 9. 평가 지표

### Primary

- conflict macro F1
- exact localization accuracy
- multi-hop conflict recall
- no-conflict false positive rate

### Secondary

- partial evidence F1
- fully valid proof rate
- unsupported assumption rate
- conflict 개수별 recall
- evidence-order flip rate

### 핵심 gap

```text
CompilationGap = Score(C1 Gold Facts) - Score(C0 Raw)
GraphGap       = Score(C2 Gold Graph) - Score(C1 Gold Facts)
MultiHopGap    = Score(single-hop, C0) - Score(multi-hop, C0)
```

Primary score는 exact localization으로 고정한다. Detection macro F1는 no-conflict control을 포함해 함께 보고한다.

## 10. 분석 방법

- 동일 instance의 C0--C2 차이는 paired bootstrap 95% CI로 계산한다.
- single-hop과 multi-hop은 relation, 길이, conflict 개수를 공변량으로 둔 회귀 분석을 보조적으로 사용한다.
- 효과 크기와 신뢰구간을 우선 보고하고, 120개 표본에서 유의성만으로 결론 내리지 않는다.
- 오류 사례는 최소 60건을 다음 첫 실패 지점으로 분류한다.

1. relevant fact 누락
2. text-to-fact compilation 오류
3. entity 또는 relation alignment 오류
4. graph/path composition 오류
5. terminal conflict 판정 오류
6. false positive 또는 unsupported assumption

오류 분류 20건은 두 연구자가 독립 수행해 분류 기준의 안정성을 확인한다.

## 11. Go/Partial-Go/No-Go

### Go A: semantic compilation 방법 연구

다음을 모두 만족하면 semantic compilation uncertainty를 다루는 방법으로 진행한다.

1. 최소 두 모델에서 multi-hop `C1 - C0 ≥ 10%p`
2. 그중 한 모델 이상에서 paired bootstrap CI 하한이 0보다 큼
3. multi-hop의 compilation gap이 single-hop보다 최소 5%p 큼
4. 수동 오류 중 compilation/alignment 오류가 35% 이상
5. 자연 사례 20개 중 15개 이상에서 span과 필요한 derived claim을 합의 가능

이 경우에만 hypothesis lattice 또는 uncertainty-aware claim compilation을 구현한다.

### Go B: proof-search 방법으로 피벗

다음 패턴이면 문제는 multi-hop conflict이지만 제안 방법의 중심을 바꾼다.

- `C1 - C0 < 5%p`
- `C2 - C1 ≥ 10%p` 또는 C2에서도 큰 residual error
- 오류의 다수가 path composition 또는 terminal conflict 판정

이 경우 semantic compilation을 핵심 주장으로 두지 않고 graph/proof search, verification 또는 conflict-aware reasoning 방법을 검토한다.

### Partial Go: 데이터ㆍ진단 연구

- 명확한 multi-hop gap은 있으나 간단한 structured prompt가 대부분 회복
- 방법론 필요성은 약하지만 자연문서에서도 오류 유형이 반복됨

이 경우 대규모 ACL main 방법론으로 즉시 확장하지 않고 분석/벤치마크 범위를 재검토한다.

### No-Go

다음 중 하나면 현재 방향을 중단하거나 다른 conflict setting으로 이동한다.

- 강한 두 모델의 raw multi-hop exact localization이 모두 90% 이상
- `C1 - C0`와 `C2 - C1`이 모두 5%p 미만
- multi-hop과 single-hop 차이가 길이ㆍ충돌 개수를 통제하면 사라짐
- no-conflict control이 명확하게 구성되지 않음
- 자연 사례의 50% 이상이 현재 proof schema로 표현되지 않음

## 12. 예상 실행량

Core 기준 최대 실행량은 다음과 같다.

```text
120 instances × 3 representations × 3 models = 1,080 calls
order permutation: 40 instances × 3 models = 120 calls
prompt baseline 추가분: 필요한 조건에만 최대 약 600 calls
총 예상: 약 1,200--1,800 calls
```

기존 약 13,440 calls 계획의 10--14% 수준이다. Natural 20개와 higher-order 12개는 핵심 통계에서 분리한다.

## 13. 실행 순서

### Step 0 · 데이터 감사

- MAGIC 전체 파일 다운로드 및 checksum 기록
- 각 split의 사례 수와 field schema 확인
- single/multi-hop 각각 10개를 사람이 읽어 graph와 context 정합성 점검
- 중복 entity, relation, 비정상 생성 문장 비율 기록

이 감사에서 심각한 label 또는 text 문제가 20%를 넘으면 표본 수를 늘리지 않고 데이터 원천을 재검토한다.

### Step 1 · 30개 dry run

- single-hop conflict 10개
- multi-hop conflict 10개
- matched no-conflict 10개
- C0--C2 prompt와 parser 구현
- 공개 모델 1개와 강한 모델 1개 실행

30개에서 출력 파싱과 누설 방지를 먼저 고친다. 가설 임계값은 변경하지 않는다.

### Step 2 · Core 120개

- 층화 표집 및 no-conflict control 완성
- 모델 3개에서 C0--C2 실행
- 40개 order permutation
- bootstrap gap과 오류 60건 분석

### Step 3 · Natural sanity 20개

- WikiContradict 10개, ConfRAG 10개 선정
- 최소 span/relevance annotation
- controlled 결과와 같은 실패 유형이 존재하는지만 판정

### Step 4 · 결정

- Go A / Go B / Partial Go / No-Go 결정문 작성
- Go일 때만 higher-order 12개 제작
- 결과에 맞춰 상위 README의 연구 주장과 후속 방법론 수정

## 14. 착수 전 고정할 항목

- [ ] MAGIC 버전 또는 commit/hash
- [ ] 표본 추출 seed와 ID 목록
- [ ] no-conflict control 생성 규칙
- [ ] C0--C2 prompt와 JSON schema
- [ ] primary metric: exact localization
- [ ] 모델 버전과 decoding 설정
- [ ] 오류 분류 지침
- [ ] Go/No-Go 임계값
- [ ] API 예산 상한

모든 변경은 결과를 보기 전에 RUNLOG에 기록한다.

## 15. 파일럿 산출물

1. 감사된 MAGIC core 120개 ID와 파생 no-conflict control
2. C0--C2 입력과 모델 출력
3. single-hop/multi-hop 및 compilation/graph gap 결과표
4. 오류 분석 60건과 이중 분류 20건
5. natural sanity set 20개
6. Go A / Go B / Partial Go / No-Go 결정문
7. 후속 실험과 방법론 범위를 반영한 README 수정안

## 16. 이 파일럿이 답하지 않는 것

파일럿 결과가 좋더라도 다음을 바로 주장하지 않는다.

- 실제 웹의 모든 충돌이 MAGIC과 같은 graph 구조를 갖는다.
- multi-hop conflict가 모든 RAG 실패의 주된 원인이다.
- query-conditioned global conflict가 해결되었다.
- 12개 탐색 사례로 higher-order conflict 일반화가 입증되었다.
- gold graph에서의 향상이 곧 LatticeConf의 필요성을 증명한다.

파일럿의 목적은 더 좁다. **multi-hop conflict의 실재 난이도와 첫 병목 위치를 확인해, 어떤 해결 방법을 개발할 가치가 있는지를 결정하는 것**이다.
