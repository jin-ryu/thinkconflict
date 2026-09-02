# 데이터셋 선택 요약: 왜 MAGIC 대신 ProofWriter인가

작성일: 2026-09-01  
상태: Pilot A 데이터 결정 / 쉬운 설명

## 한 줄 결론

> MAGIC은 “모델이 충돌 위치를 찾는가”를 평가하기에는 사용할 수 있지만, 우리가 하려는 “모델이 어느 추론 단계에서 실패했는가”를 평가할 만큼 정답 proof가 엄밀하지 않았다. 그래서 실패 원인 분해에는 ProofWriter를 쓰고, 실제 문서에서의 유효성은 별도의 자연 데이터로 검증한다.

## 1. MAGIC을 그대로 쓰지 못한 이유

MAGIC이 나쁜 데이터셋이라는 뜻은 아니다. **MAGIC의 원래 목적과 우리 실험의 채점 기준이 다르기 때문**이다.

### MAGIC의 원래 목적

MAGIC은 여러 context에 충돌이 있는지 탐지하고, 관련 위치를 찾는 IDㆍLOC 평가를 위해 만들어졌다. 이를 위해 지식 그래프의 관계 경로를 자연어 context로 바꿨다.

### 우리 파일럿이 추가로 요구하는 것

우리의 C0--C4 실험은 다음까지 정답이어야 한다.

1. 어떤 원문 문장이 필요한 전제인가?
2. 전제에서 어떤 중간 결론이 도출되는가?
3. 각 추론 단계가 논리적으로 유효한가?
4. 마지막 두 결론이 실제로 동시에 참일 수 없는가?

이 중 하나라도 틀리면 모델의 실패가 아니라 데이터 정답의 오류를 측정하게 된다.

### 실제로 발견한 문제

고정된 MAGIC multi-hop 15개를 모델 없이 먼저 읽어본 결과는 다음과 같았다.

| 판정 | 수량 |
|---|---:|
| 명확히 사용 가능 | 0 |
| 애매함 | 2 |
| 제외 권고 | 13 |

이 수치는 독립된 사람 주석 결과가 아니라 assistant prescreen이다. 따라서 MAGIC 전체가 잘못됐다는 통계로 사용하면 안 된다. 하지만 본평가를 중지하고 데이터 원천을 바꾸기에는 충분히 강한 경고였다.

쉽게 말하면 다음과 같은 문제가 반복됐다.

- `A가 B와 국경을 접한다`와 `B가 C와 국경을 접한다`고 해서 `A가 C와 국경을 접하는` 것은 아니다.
- 어떤 물체가 물질을 `포함한다`는 것과 그 물체가 그 물질의 `종류`라는 것은 다르다.
- 두 문장이 서로 다른 속성을 말할 뿐인데 충돌로 표시된 사례가 있었다.
- 원 graph에는 필요한 사실이 있지만 자연어 context에는 빠진 사례가 있었다.

이 상태에서 MAGIC graph를 C3 정답, 경로를 C4 정답으로 사용하면 문제가 생긴다.

- 모델이 잘못된 추론을 거부했는데 오답으로 채점될 수 있다.
- `ProofSearchGap`이 모델의 proof-search 문제가 아니라 데이터 proof 문제를 나타낼 수 있다.
- 잘못된 conflict를 기준으로 no-conflict 짝을 만들면 paired 실험도 성립하지 않는다.

따라서 MAGIC은 다음 역할로만 남긴다.

- 원 논문과 같은 IDㆍLOC 비교
- 엄격한 감사를 통과한 일부 사례의 외부 전이 확인
- ProofWriter에서 발견한 오류 패턴이 다른 데이터에서도 보이는지 보는 보조 분석

상세 판정은 [MAGIC 품질 감사](data_quality_audit_findings.md)에 있다.

## 2. ProofWriter를 선택한 이유

ProofWriter는 원래 multi-hop conflict 데이터셋이 아니다. 자연어 사실과 규칙으로부터 결론을 도출하는 데이터이며, 정답 proof와 중간 결론을 제공한다.

우리는 이를 다음처럼 conflict로 변환한다.

```text
문서 1ㆍ2의 사실과 규칙 → 여러 단계 후 h가 도출됨
문서 3 → not h를 명시함
결과 → h와 not h의 문서 간 충돌
```

이 방식의 장점은 다음과 같다.

- 몇 hop인지 정확히 통제할 수 있다.
- 필요한 사실과 규칙을 정확히 알 수 있다.
- 별도 forward-chaining 검사기로 정답을 다시 계산할 수 있다.
- C0 원문, C1 근거, C2 canonical claim, C3 graph, C4 proof를 같은 사실 정보로 만들 수 있다.

현재 20개 dry run은 15개 conflict와 5개 paired control로 구성했고, 독립 symbolic validation에서 오류 0건이었다.

## 3. “인위적으로 만든 데이터 아니냐”는 비판

**그 비판은 맞다.** ProofWriter 파생 데이터에는 다음 한계가 있다.

- 우리가 마지막 반대 문서를 인위적으로 추가한다.
- 문서가 실제 웹 문서보다 짧고 논리 퍼즐에 가깝다.
- NatLang subset도 주로 사람의 단항 속성 표현을 다루며 복잡한 관계ㆍ시간ㆍ조건이 부족하다.
- 모든 conflict가 현재는 `h` 대 `not h` 형태라 실제 충돌의 다양성을 대표하지 못한다.

따라서 ProofWriter만으로 다음을 주장하면 안 된다.

- 실제 RAG 문서에서도 같은 실패 비율이 나타난다.
- 현실의 모든 multi-hop conflict를 대표한다.
- 제안 방법이 실제 웹ㆍ정책ㆍ시간 충돌까지 해결한다.

### 그래도 파일럿에는 필요한 이유

우리가 먼저 알고 싶은 것은 현실에서 몇 퍼센트 실패하는지가 아니라 **실패가 원문 선택, 의미 변환, graph 구성, proof 탐색 중 어디서 처음 생기는가**다. 이 인과적 원인 분해에는 다른 요인을 고정하고 정답 proof를 아는 통제 데이터가 필요하다.

즉 역할은 다음처럼 나뉜다.

| 데이터 | 답하는 질문 |
|---|---|
| ProofWriter 파생 통제셋 | 실패가 어느 단계에서 처음 발생하는가? |
| 신규 자연 문서셋(구축 시) | 그 실패와 해결 효과가 실제 문서에서도 나타나는가? |

## 4. ACL Main에서 합성 데이터 비판을 막기 위한 필수 설계

ProofWriter 결과만으로 ACL Main을 주장하지 않는다.

### 파일럿 단계

- ProofWriter NatLang 20개를 사람 검수한다.
- 통제 데이터에서 C0--C4 gap이 존재하는지 본다.
- gap이 없다면 자연 데이터 대규모 구축이나 방법론 개발로 넘어가지 않는다.

### 본논문 단계

상위 연구 계획의 Q-GloCo 구성에 따라 다음 두 축을 모두 갖춰야 한다.

1. **통제 진단셋**: ProofWriter 기반으로 hopㆍproofㆍdistractor를 통제한다.
2. **외부 벤치마크**: MAGIC 감사 통과 사례로 기존 multi-hop conflict에서 ID·LOC와 oracle gap을 비교한다.
3. **신규 자연 문서셋**: 바로 쓸 공개 자연 multi-hop conflict gold가 확인되지 않았으므로 별도 구축 타당성 파일럿 후 결정한다.

구체적인 목표 구성은 다음과 같다.

| 원천 | 파일럿 | ACL 본논문 목표 | 선택 이유 |
|---|---:|---:|---|
| WikiContradict | 제외 | 제외 | 실제 Wikipedia 충돌, 사람 검증, explicit/implicit label과 문맥별 답 제공 |
| ConfRAG | 제외 | 제외 | 실제 장문 웹 문서, 문서별 근거와 다중 answer cluster 제공 |
| 신규 자연 multi-hop set | TBD | TBD | 별도 수집·proof 주석 타당성 검증 후 결정 |

WikiContradict와 ConfRAG의 자연 충돌 사례는 보조 calibration으로만 사용할 수 있으며 multi-hop 결과에 합산하지 않는다. 신규 자연 multi-hop 사례는 최소 두 문서, 두 개 이상의 추론 step, single-document insufficiency, source-grounded proof를 두 주석자가 검증해야 한다. 규모는 후보 수율과 주석 합의도를 측정한 뒤 결정하며 300개를 선결 조건으로 두지 않는다.

### 논문에서의 안전한 주장

- 가능(신규 자연 셋을 실제 구축·검증한 경우에만): “통제 실험의 병목과 해결 효과가 사람 검증 자연 multi-hop conflict에서도 재현됐다.”
- 불가능: “ProofWriter에서 좋아졌으므로 실제 RAG multi-hop conflict를 해결했다.”

## 5. 최종 역할 결정

| 데이터 | Pilot A | ACL 본논문 | 이유 |
|---|---|---|---|
| ProofWriter NatLang 파생 | 핵심 원인 분해 | 통제 진단ㆍablation | proof가 검증 가능하지만 합성적임 |
| WikiContradict | multi-hop 평가 제외 | 자연 충돌 calibration 후보 | hop·proof gold가 없음 |
| ConfRAG | multi-hop 평가 제외 | 자연 상충 답변 calibration 후보 | answer cluster가 multi-hop proof를 보장하지 않음 |
| MAGIC | 감사 통과 사례 | IDㆍLOC 선행 비교ㆍtransfer | multi-hop conflict 직접 관련 벤치마크지만 자연문서 외적 타당성 근거는 아님 |
| Ragability | 제외 | 제외 | WikiContradict에서 파생돼 중복 |
| EX-FEVERㆍHoVer | 제외 | 필요 시 후보 탐색에만 사용 | 멀티홉이지만 문서 간 충돌 gold가 아님 |

## 6. 현재 상태

- ProofWriter 공식 아카이브와 schema 확인: PASS
- 1--4 hop 후보 수: 충분
- NatLang dry run 20개 구조 검사: PASS
- 독립 forward chaining: 20개 오류 0
- 사람 semantic-equivalence 검수: 아직 안 함
- 자연 multi-hop conflict 본평가셋: 공개셋 미확인, 구축 타당성도 아직 검증하지 않음

따라서 현재 결론은 **“ProofWriter로 본실험을 시작해도 된다”가 아니라 “ProofWriter dry run을 사람 검수할 단계까지 왔다”**이다.
