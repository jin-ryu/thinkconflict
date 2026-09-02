# Pilot A · MAGIC data quality audit findings

작성일: 2026-09-01  
상태: 모델 미사용 1차 prescreen / 독립 주석 전

쉬운 설명과 최종 데이터 역할 결정은 [데이터셋 선택 요약](dataset_decision.md)을 먼저 본다. 이 문서는 기술적 감사 근거를 보존한다.

## 1. 결론

현재 MAGIC multi-hop split을 그대로 Pilot A의 **fully valid conflict certificate** gold로 사용할 수 없다.

고정 seed로 선택한 dry-run multi-hop conflict 15개를 [audit protocol](data_audit_protocol.md)의 G3 proof-step soundness와 G4 terminal incompatibility로 직접 검토한 결과는 다음과 같다.

| 판정 | 수량 |
|---|---:|
| accept | 0 |
| ambiguous | 2 |
| exclude recommended | 13 |

이 수치는 gold 결과가 아니라 assistant prescreen이다. 하지만 15개 중 명확한 accept가 0이라는 결과는 no-conflict 제작과 C0--C4 annotation에 들어가기 전에 데이터 원천을 재검토해야 할 정도로 강한 경고다.

## 2. 주된 실패 유형

### 비전이 관계의 전이

- `A borders B`, `B does not border C`로부터 `A borders C`의 부정을 유도
- `A overlaps B`, `B borders C`, `C disjoint D`를 원래 overlap claim과 충돌로 간주
- `connects with`, `followed by`, `born in`, `residence`를 명시적 규칙 없이 다음 edge로 전파

### type과 mereology 혼합

- `part of`, `contains`, `shape`, `subclass`, `instance of`, `disjoint`를 같은 종류의 edge처럼 합성
- 어떤 물체가 화학물질을 포함한다는 사실과 그 물체의 category가 화학물질 category와 disjoint라는 사실을 모순으로 취급
- 장소ㆍ사람ㆍ기관ㆍ개념 category를 하나의 path에서 교차해 category error 발생

### terminal incompatibility 부재

- 두 claim이 단지 다른 속성이나 관계를 말할 뿐 동시에 참일 수 있음
- `distinct`, 다른 언어, 다른 전문 분야 같은 차이를 원 original claim의 부정으로 연결
- N-conflict 사례에서 일부 path만 충돌하고 나머지는 일관적이어도 전체를 N-conflict로 간주

## 3. 원 논문 검증과의 경계

[MAGIC](https://aclanthology.org/2025.findings-emnlp.466/)의 생성 prompt는 LLM에 “logically connected triplets”를 만들라고 지시하지만 관계별 허용 추론 규칙을 제공하지 않는다. KG-to-text 검증은 다음 두 항목을 중심으로 한다.

1. target/perturbed triplet이 text에 표현됐는가
2. subgraph triplet이 text에 포함됐는가

논문은 human inspection에서 conflict triplet coverage 95.21%, subgraph coverage 82.04%를 보고한다. 이는 **문장화 coverage** 검증이지, 각 relation composition이 논리적으로 타당하거나 terminal claims가 양립 불가능하다는 proof-soundness 검증은 아니다.

따라서 현재 발견은 MAGIC 논문의 ID/LOC benchmark 자체를 무효화한다는 주장이 아니다. 우리 파일럿이 요구하는 `gold proof skeleton`과 MAGIC의 원래 conflict 정의 사이에 맞지 않는 부분이 있다는 뜻이다.

## 4. 연구 설계에 미치는 영향

### 그대로 진행하면 생기는 문제

- C3 Gold Graph와 C4 Proof Skeleton이 잘못된 추론 규칙을 gold로 누설한다.
- 모델이 상식적으로 잘못된 path를 거부하면 오답으로 채점된다.
- `ProofSearchGap`이 모델 병목이 아니라 dataset proof 오류를 측정한다.
- no-conflict control을 만들어도 원 conflict label 자체가 불안정해 paired 비교가 성립하지 않는다.

### 권고

**MAGIC는 외부 transfer/IDㆍLOC 비교용으로 남기고, oracle-gap의 controlled diagnostic core는 허용 추론 규칙이 명시된 proof-valid set으로 바꾸는 것이 가장 안전하다.**

가능한 다음 설계는 다음과 같다.

1. transitive/equivalence/subclass/disjointness처럼 허용 규칙을 먼저 고정한다.
2. 각 사례에 rule ID가 붙은 2--4 hop proof를 생성한다.
3. 원문 문서화 전후에 fact coverage와 proof validity를 별도로 검증한다.
4. MAGIC에서는 엄격한 audit를 통과한 subset만 transfer check로 사용한다.

## 5. 현재 중단한 작업

- G1 교체 제안 6건은 G3--G4가 통과되지 않아 아직 manifest에 적용하지 않았다.
- Paired no-conflict 24개는 잘못된 conflict proof를 기준으로 만들 위험이 있어 template 상태에서 멈췄다.
- 모델 기반 검토와 생성은 다른 작업의 모델 사용이 끝날 때까지 실행하지 않는다.

세부 판정은 `data/pilot_a/proof_soundness_prescreen.jsonl`에 `gold=false`로 보존한다.
