# 충돌 관련 참고 논문 분석: 방법론·한계와 신규 논문 주제

이 문서는 literature/papers/ 아래 지식 충돌(knowledge conflict) 관련 핵심 논문의 방법론과 한계를 분석하고, 공백별 최신 연구를 조사한 뒤, 이를 해결하는 신규 논문 주제를 도출한다. 기존 7편의 상세 분석에 MAGIC과 멀티홉 충돌 연구 지형을 추가했다. 작성일: 2026-08-31.

## 1. 논문별 방법론과 한계 요약

논문별 상세 분석(방법론 수식 수준, 한계의 근거, 후속 연구 여지 10개씩)은 각 파일 참조.

| 문서 | 논문 (발표) | 접근 방법론 | 핵심 한계 |
|---|---|---|---|
| [01](01_tug_of_war.md) | **Tug-of-War** (LREC-COLING 2024) | 내부 기억 vs 외부 근거 충돌 시 RALM의 인지편향 4종(Dunning-Kruger, availability, majority rule, confirmation)을 진단하고, 내부/외부 로짓을 대조하는 CD² 디코딩 제안 | ChatGPT로 생성한 인공 충돌 데이터, 토큰 겹침 지표만 사용, "근거가 상충한다"고 밝히는 abstention 능력 미측정, 블랙박스 모델 적용 불가, 내부 기억이 옳을 때의 부작용 미검증 |
| [02](02_coiecd.md) | **COIECD** (ACL 2024) | 토큰별 정보량-엔트로피 시프트로 충돌 여부를 판별한 뒤 충돌/비충돌 토큰에 다른 디코딩 전략 적용 | 충돌 라벨이 "모델이 틀린 문제"와 동치라 순환적, 충돌 판별기 자체의 정밀도/재현율 미측정, 전체 로짓 필요(API 모델 불가), pre-2024 base 모델에서만 검증, 컨텍스트가 틀린 경우 오히려 오류 강화 |
| [03](03_self_rag.md) | **Self-RAG** (ICLR 2024) | reflection token(Retrieve/IsRel/IsSup/IsUse)을 학습해 검색 시점·문서 유용성·근거 지지를 자기비평, 세그먼트 빔서치 | 문서를 항상 1개씩 독립 처리해 문서 간 모순을 원리적으로 관측 불가, IsSup이 "무지지"와 "반박"을 한 클래스로 병합, 충돌 해소가 사실상 승자독식 argmax, 자기지지적 날조 문서에 취약 |
| [04](04_ramdocs_madam_rag.md) | **RAMDocs / MADAM-RAG** (COLM 2025) | 모호성+오정보+노이즈+근거 불균형을 동시에 넣은 벤치마크와, 문서 1개당 에이전트 1개를 두는 다라운드 토론 프레임워크 | 오정보가 entity-swap 단일 전략, 출처 메타데이터·시간축 전무, all-or-nothing EM 지표, 동일 토큰 예산 베이스라인 부재(토론 구조 vs 추가 연산 분리 불가), 문서 결합이 필요한 multi-hop 구조적 불가 |
| [05](05_conflictrag.md) | **ConflictRAG** (투고 중) | 임베딩 MLP + LLM 정제의 2단계 충돌 탐지 → 유형 분류(factual/temporal/opinion) → Entropy-TOPSIS 출처 평가 → 충돌 인지 생성 | pairwise 판정만 있고 3개 이상 문서의 전역 통합 절차 부재, 합성 주입 충돌의 문체 아티팩트 학습 위험, authority 점수를 LLM 사전지식으로 추정(순환), CARS 지표가 자기 방법에 유리하게 설계됨 |
| [06](06_conflict_aware_rag.md) | **Conflict-Aware RAG** (WWW '26) | perplexity 격차 기반 ConScore를 정의해 SFT→DPO→Reranking 3단계 학습 전체에 충돌 신호 주입, 외부 API 없이 자기 신호만 사용 | PPL 격차 = 충돌이라는 전제가 미검증(길이·어휘 교란), 모델이 원래 모르는 영역은 구조적으로 개선 불가, 시간적 충돌 미통제(2018 위키 vs 2023 컷오프 모델), EM/F1만 평가 |
| [07](07_faithfulrag.md) | **FaithfulRAG** (ACL) | 내부 지식을 fact 단위로 외재화(self-fact)해 컨텍스트와 정렬 후, 4단계 구조화 Self-Think로 충돌 해소, 학습 불필요 | ablation상 성능 대부분이 구조화 CoT에서 나오고 핵심 novelty(self-fact)의 기여는 1~2%p, 정렬이 코사인 유사도라 모순 탐지가 아니라 관련성 재랭킹, 검색 문서 간 충돌은 구조적으로 미처리, 질의당 LLM 4~5회 호출 비용 미보고 |
| [09](09_multihop_conflict_landscape.md) | **MAGIC 및 멀티홉 충돌 연구 지형** (2025~2026) | KG 기반 멀티홉 충돌 벤치마크를 조건부 모순ㆍ실세계 ConfRAGㆍ최신 hypergraph RAG와 대조 | 멀티홉 자체는 더 이상 공백이 아님. pairwise-consistent 고차 충돌의 최소 증거 집합, 검증 가능한 추론 certificate, 그래프 구축 불확실성이 핵심 공백 |

## 2. 문헌 전체를 관통하는 공백 (교집합)

아래 7가지는 **분석 대상 7편 내부에서** 공통으로 비워둔 지점이다. 이것이 곧 분야 전체의 미해결 문제라는 뜻은 아니다. 3절에서 더 넓은 문헌을 대조해 각 항목을 `미해결 / 부분 해결 / 체계적 비교 부재 / 특정 도메인 한정`으로 다시 판정한다.

1. **충돌 데이터의 인공성**: 전부 entity-swap 또는 LLM 생성 반사실 문서다. 자연 발생 충돌(뉴스 정정, 위키 편집 이력, 가이드라인 개정)로 만든 벤치마크가 없다.
2. **시간축·출처 메타데이터 부재**: 발행일, 도메인 권위, 인용 관계를 가진 데이터셋이 한 편도 없다. "최신 vs 다수결 vs 권위"가 충돌하는 현실 시나리오가 통째로 빠져 있다.
3. **abstention·충돌 표출 평가 부재**: 모든 논문이 정답 맞히기(EM/F1/Recall)로만 평가한다. "출처들이 상충하므로 A와 B 두 견해가 있다"고 말하는 능력, calibration, 유보 품질을 재는 지표가 없다.
4. **충돌 탐지 신호 자체의 검증 부재**: COIECD의 엔트로피 게이팅, Conflict-Aware RAG의 ConScore 모두 다운스트림 성능으로만 간접 평가된다. 탐지 신호가 실제 사실적 모순과 상관하는지 직접 잰 논문이 없다.
5. **고차 충돌의 검증 가능한 전역 해소 부재**: Gokul et al.은 3문서 조건부 모순을, MAGIC은 멀티홉 문맥 간 충돌을 이미 벤치마킹했다. 따라서 “n-ary 충돌이 연구되지 않았다”는 표현은 부정확하다. 남은 공백은 모든 쌍이 일관돼도 전체가 불일치인 최소 증거 집합을 찾고, 추론 경로를 certificate로 검증하며, claimㆍNLI edge 오류까지 고려해 전역 해소하는 정식화다.
6. **비용 통제 비교 부재**: FaithfulRAG(질의당 5회 호출), MADAM-RAG(문서 수×라운드), ConflictRAG(pairwise 10회) 모두 동일 토큰 예산의 self-consistency 베이스라인과 비교하지 않았다.
7. **적대적 관점 부재**: "자기 주장을 완벽히 지지하는 날조 문서"는 IsSup·ConScore·TOPSIS 모두에서 오히려 유리해진다. poisoning 방어를 다룬 논문이 없다.

## 3. 공백별 최신 연구 조사 (2024~2026)

각 공백을 겨냥한 최신 논문들을 웹 조사한 결과. 단순히 여러 요소를 한 논문에서 동시에 다루지 않았다는 사실(`gap stacking`)만으로 신규성을 주장하지 않고, 기존 방법으로 답할 수 없는 구체적 연구 질문이 남았는지를 기준으로 판단한다. 요지: **공백 1은 상당히 메워졌고, 2·3·4는 체계적·인과적 검증이 남았으며, 5는 입력 그래프의 오류를 고려한 전역 해소가 열려 있다. 6은 독립 주제보다 필수 통제 실험에 가깝고, 7의 공격 문제는 최신 연구가 직접 선점했다.** 조사일: 2026-08-31.

### 공백 1: 충돌 데이터의 인공성 → 상태: 상당히 메워짐

- **WikiContradict** (NeurIPS 2024 D&B, arXiv:2406.13805): Wikipedia 편집자가 실제 모순 태그를 단 문서에서 추출한 253개 인간 검증 QA. 실세계 inter-context 충돌 벤치마크의 시초. 단 규모가 작고 출처/시점 메타데이터 없음.
- **DRAGged into Conflicts / CONFLICTS** (Google Research, 2025, arXiv:2506.08500): 실제 검색 결과에 전문가가 충돌 유형 5분류(충돌 없음/보완/의견/구식/허위)를 주석하고 유형별 기대 행동을 정의.
- **ConfRAG** (ACL 2026): 실제 웹 검색으로 수집한 1,814개 질문 × 평균 9.6개 지문, 57.2%가 명시적 모순 포함. 현재 가장 근접한 대규모 자연 충돌 벤치마크.
- **RAGuard** (2025, arXiv:2502.16101): Reddit에서 자연 발생한 오도성 문서 기반 misinformation RAG 벤치마크(정치 fact-checking 한정).
- **evolveQA** (2025, arXiv:2510.19172): AWS/Azure 변경 로그, WHO 보고 등 타임스탬프 코퍼스의 자연 발생 지식 변화 기반 QA.
- **남은 공백**: 뉴스 정정 기사 기반 벤치마크는 미확인. 의료 가이드라인은 DriftMedQA가 시뮬레이션으로 처리해 실제 개정 이력 기반은 공백. 자연 충돌 + 충돌 유형 라벨 + 출처 메타데이터를 모두 갖춘 단일 자원은 없음. 방법론 논문들은 여전히 합성 충돌(ConflictBank, RAMDocs)로 평가하는 관행이 지속.

### 공백 2: 시간축·출처 메타데이터 → 상태: 다중 신호 사용은 등장, 의미적 시간 관계는 공백

- **QA under Temporal Conflict** (2025, arXiv:2506.07270): Wikipedia 스냅샷 이력과 타임스탬프 뉴스로 시간 충돌 벤치마크 구축. 여러 시점 사실이 공존하면 최신으로 수렴하지 못함을 보임.
- **DriftMedQA** (EMNLP 2025 Findings, arXiv:2505.07968): 가이드라인 진화 시뮬레이션 4,290 시나리오. 구식 권고 기각 실패와 상충 권고 동시 승인 문제 확인.
- **Whose Facts Win?** (2026, arXiv:2601.03746): 통제된 합성 출처(기관 vs 개인)로 충돌 시 선호 측정. 기관 출처를 선호하지만 저신뢰 출처의 반복(다수결)이 이를 뒤집음: authority vs majority를 다룬 최초급 연구.
- **When Text and Numbers Disagree** (2026, arXiv:2608.20116): 타임스탬프와 명시적 신뢰도 라벨을 동시 조작. LLM은 신뢰도 라벨보다 recency를 더 일관되게 따름.
- **Recency Bias in LLM Reranking** (SIGIR-AP 2025, arXiv:2509.11353): 발행 연도 조작으로 리랭커의 recency 편향 정량화.
- **EPRAG** (2026): freshness·authority·corroboration·query suitability·policy alignment를 provenance tuple로 표현하고, freshness-first·authority-first·majority-vote 정책을 비교. 기업 문서 환경에 한정되지만 "세 신호 동시 사용" 자체는 더 이상 안전한 신규성 주장이 아니다.
- **남은 공백**: recency·majority·authority는 진실성의 보편적 기준이 아니다. 최신 오보, 동일 원문을 복제한 가짜 다수, 관할 밖의 권위 출처를 구분해야 한다. 특히 publication time과 fact validity time을 분리하고, `correction / retraction / supersession / 시점별 공존 / 진정한 견해 충돌`을 판별하는 자원과 방법은 부족하다. 복제·인용 계보를 이용해 독립적 합의와 에코체임버를 구분하는 축도 열려 있다.

### 공백 3: abstention·충돌 표출 평가 → 상태: 통합 프레임도 등장, 정책 타당성·일반화가 공백

- **CONFLICTS / DRAGged into Conflicts** (2025, arXiv:2506.08500): 충돌 유형별 "적절한 응답"(예: 양쪽 관점 제시)을 정의하고 적절성 평가. 이 공백에 가장 근접. 단 LLM-judge 판정이고 기권·보정은 미포함.
- **NATCONFQA** (2025, arXiv:2508.12355): 팩트체킹 기반 다답 QA에 답 쌍 단위 충돌 라벨 부여. "어떤 답 쌍이 충돌하는지" 명시까지 요구.
- **AbstentionBench** (Meta FAIR, 2025, arXiv:2506.09038): 6개 기권 시나리오 20개 데이터셋의 종합 기권 평가. 그러나 시나리오에 "검색 문서 간 충돌"이 없음.
- **When Evidence Conflicts (biomedical)** (2026, arXiv:2605.14115): 충돌 하 불확실성·보정·문서 순서 효과 분석. 충돌 하 calibration을 직접 다룬 드문 사례이나 생의학 한정.
- **Rich Knowledge Sources Bring Complex Knowledge Conflicts** (EMNLP 2022): 서로 다른 검색 근거가 여러 답을 지지할 때 calibration을 연구하고, 단일 답을 과도하게 제시하지 않도록 보정. 충돌 하 calibration 자체는 오래된 연구 질문이다.
- **Adaptive Question Answering** (EMNLP 2024): 모호한 다중 답을 출처 인용과 함께 제시하는 conflict-aware QA를 연구.
- **SURE-RAG** (2026, arXiv:2605.03534): claim-evidence 관계 분포를 coverage·disagreement·conflict·retrieval uncertainty로 집계해 3방향 selective decision을 수행.
- **EvidentialRAG** (2026, arXiv:2607.10491): 다중 출처 증거를 불확실성으로 융합하고 `{직접 답변 / 충돌 인지 답변 / 기권}`으로 라우팅하며 calibration까지 평가. 따라서 "표출·기권·보정의 최초 통합"은 주장하기 어렵다.
- **남은 공백**: 고정된 `{한쪽 채택 / 양쪽 병기 / 유보}` 라벨의 타당성이 검증되지 않았다. 실제 행동에는 추가 검색, 사용자에게 시간·대상 확인, 조건부 답변, 정정 출처 선택이 포함된다. 출처별 귀속을 포함한 응답 품질의 사람 검증, 오류 비용에 따른 정책 학습, 도메인 밖 일반화가 남아 있다.

### 공백 4: 충돌 탐지 신호 검증 → 상태: 합성 라벨 기준 직접 평가는 시작됨

- **ECon** (EMNLP 2024, arXiv:2410.04068): NLI·사실일관성 모델·LLM을 충돌 탐지기로서 직접 평가(정밀도·재현율). 단 라벨이 합성이고 엔트로피·PPL류 신호는 미평가.
- **Contradiction Detection in RAG** (2025, arXiv:2504.00180): 자기모순·쌍·조건부 모순을 유형별 합성 생성해 LLM 검증자 성능 측정.
- **MAGIC** (EMNLP 2025 Findings, arXiv:2507.21544): KG 기반 다중 홉 문맥 간 충돌 생성, 탐지 + 위치 특정(localization)까지 평가. 스팬 수준에 가장 근접하나 충돌이 자동 생성.
- **Residual Stream under Knowledge Conflicts** (2024, arXiv:2410.16090): 잔차 스트림 선형 프로빙으로 충돌 신호가 중간층에서 검출 가능함을 보임.
- **남은 공백**: "다운스트림으로만 간접 평가"라는 서술은 이제 부정확하다. 더 중요한 미해결 문제는 각 신호가 contradiction 자체와 novelty·irrelevance·lexical overlap·문서 길이·모델의 지식 부재를 구분하는지 여부다. 사람이 검증한 실세계 claim-pair와 한 요인만 바꾼 최소대조쌍을 결합해 이종 신호의 인과적 민감도를 동일 조건에서 비교한 연구가 부족하다.

### 공백 5: n-ary 충돌의 전역 해소 → 상태: 그래프 해소는 등장, 입력 오류를 고려한 형식화는 부재

- **Contradiction Detection in RAG Systems** (2025, arXiv:2504.00180): 두 문서씩은 직접 모순이 아니지만 세 번째 문서가 결합될 때 배타성이 생기는 conditional contradiction을 제안. 고차 충돌의 직접 선행연구이므로 반드시 인용해야 한다.
- **MAGIC** (EMNLP 2025 Findings, arXiv:2507.21544): KG 경로를 결합해야 드러나는 멀티홉 충돌 588개를 포함하고 IDㆍLOC 성능 하락을 실증. 그러나 최소 불일치 집합이나 추론 certificate를 평가하지는 않는다.
- **ArgRAG** (NeSy 2025, arXiv:2508.20131): 검색 문서로 QBAF(정량 양극 논증 프레임워크)를 구성해 support/attack 관계로 결정적 추론. 논증 프레임워크 방향의 첫 구현이나 사실 검증 태스크 한정.
- **ArbGraph** (2026, arXiv:2604.18362): 문서를 원자적 주장으로 분해해 support/contradiction 엣지 증거 그래프를 만들고 신뢰도 전파 후 생성. 이 공백에 가장 근접하나 중재가 LLM 휴리스틱이며 최적성 보장 없음.
- **HyperRAGㆍOKH-RAGㆍHyCE-RAGㆍMEGRAG** (2026): n-ary hyperedge, 순서, chain-of-evidence, 다중 입도 증거 그래프로 멀티홉 QA를 개선한다. 고차 구조 표현은 이미 선점됐지만 목적이 보완 증거 기반 QA이므로, 고차 불일치의 최소성ㆍ증명ㆍ불확실성은 여전히 열려 있다.
- **RA-RAG** (2024~2025, arXiv:2410.22954): 다중 소스 교차 검증으로 소스 신뢰도를 반복 추정. DB 커뮤니티의 truth discovery를 RAG에 연결한 사실상 유일한 사례(소스 수준에 그침).
- **TruthfulRAG** (AAAI 2026, arXiv:2511.10375): 트리플 추출 KG로 파라메트릭 vs 검색 충돌 해소(문서 간 n-ary와는 문제 설정이 다름).
- **남은 공백**: correlation clustering이나 truth discovery의 최적성·수렴성은 **입력 claim과 edge가 맞다는 조건의 알고리즘적 보장**이지 사실성 보장이 아니다. 실제로는 claim extraction, entity resolution, NLI support/contradiction 판정, 출처 독립성 추정 오류가 먼저 발생한다. 이러한 node·edge uncertainty가 전역 판정에 어떻게 증폭되는지 분석하고, 불확실한 그래프에서 위험을 통제하며 답변·복수답·기권을 선택하는 정식화가 부족하다.

### 공백 6: 비용 통제 비교 → 상태: 일반 추론에선 활발, 충돌 도메인에선 공백

- **Stop Overvaluing Multi-Agent Debate** (2025, arXiv:2502.08788): MAD가 더 많은 연산을 쓰고도 CoT·self-consistency를 못 이기는 경우가 많음을 광범위 평가.
- **Single-Agent ≥ MAS under Equal Token Budgets** (2026, arXiv:2604.02460): 토큰 예산 고정 통제 실험. 예산이 같으면 단일 에이전트가 동등 이상.
- **Pareto-Optimal Test-Time Scaling** (ACL 2026 SRW, arXiv:2605.01566): 동일 예산에서 debate·MoA가 self-consistency보다 우세라는 반대 방향 결과. 결론이 태스크·모델에 따라 갈림.
- **The Cost of Consensus** (2026, arXiv:2605.00914): 소형 모델에서 debate가 2~3배 토큰을 쓰며 정확도는 같거나 낮음.
- **남은 공백**: 충돌 벤치마크(RAMDocs, ConflictQA 등)에서 충돌 파이프라인(토론·중재·다단계)의 구조 기여를 연산량과 분리한 메타 연구는 부재. 일반 추론에서의 상충된 결과는 충돌 도메인 별도 검증의 필요성을 오히려 강화.

### 공백 7: 적대적 관점 → 상태: 충돌 해소 메커니즘 표적 공격까지 등장

- **PoisonedRAG** (USENIX Security 2025, arXiv:2402.07867): 코퍼스 오염 공격의 시초격. 260만 문서에 5개 주입으로 ASR 90%+. 충돌 해소 계층이 있는 파이프라인은 미평가.
- **ADMIT** (2025~2026, arXiv:2510.13842): 강한 반대 증거가 공존하는 상황에서도 소량 오염으로 사실검증 판정을 뒤집음(ASR 86%). 공격 측에서 가장 근접하나 해소 신호를 직접 최적화하지는 않음.
- **MAD-Spear** (2025, arXiv:2507.13038): 소수 에이전트 조작으로 다중 에이전트 토론의 동조 성향을 악용. 토론 메커니즘 공격으로는 가장 직접적이나 RAG 지식 충돌 맥락이 아님.
- **The Facade of Truth** (2026, arXiv:2601.05478) / **Ghostwriter** (2026, arXiv:2606.06244): 기만적 증거·조작된 신뢰도 마커로 LLM 믿음을 유도. 개념적으로 근접하나 충돌 해소 스코어링을 표적으로 삼지 않음.
- 방어 측: SeCon-RAG(NeurIPS 2025), ReliabilityRAG, RAGDefender 등이 충돌 인지 필터를 제안하나, 그 필터 신호를 역이용하는 적응형 공격은 미검토.
- **PURPOSE** (2026, arXiv:2608.04756): post-retrieval conflict resolver가 탐지하기 쉬운 정면 반박 대신, resolver의 기준 사실과 일관된 "업데이트"처럼 보이는 문서를 주입하는 strict black-box 공격. 3개 QA 벤치마크·5개 생성기·3개 conflict-resolution method에서 평가. poisoning × conflict resolution의 교집합 자체는 더 이상 비어 있지 않다.
- **남은 공백**: PURPOSE류 적응형 공격에 대한 인증 가능한 방어, 공격자가 provenance·authority metadata까지 조작할 수 있는 위협 모델, retriever와 resolver를 동시에 겨냥하는 end-to-end 공격, worst-case risk 보장이 남아 있다. 단순 공격 제안은 신규성이 약하다.

## 4. 신규 논문 주제 리스트 (비판적 재개정판, 추천 순)

선정 원칙은 다음과 같다.

1. 분석 대상 7편의 공백이 아니라 분야 전체 문헌 대비 공백이어야 한다.
2. 여러 요소를 한데 묶었다는 사실보다, 기존 방법으로 답할 수 없는 명확한 연구 질문이 있어야 한다.
3. 평가 데이터·신호·방법론의 단위가 맞아야 한다.
4. 정확도 향상이 아니라 어떤 오류를 왜 줄였는지 검증할 수 있어야 한다.
5. 다단계·다중 에이전트 방법은 동일 토큰·호출·지연 예산 통제를 기본 실험으로 포함한다.

### A. 충돌 신호의 인과적 타당성 감사 (진단 + 벤치마크) ★최우선 추천

**가제:** *Do RAG Conflict Scores Detect Contradiction or Distribution Shift?*

- 핵심 질문: 엔트로피 시프트·PPL 갭·NLI·내부 프로브가 실제 contradiction을 탐지하는가, 아니면 novelty·irrelevance·lexical overlap·문서 길이·모델의 지식 부재에 반응하는가?
- 기존 A와의 차이: 단순히 실세계 스팬 라벨에서 여러 신호의 AUC를 비교하지 않는다. 하나의 사례에서 한 요인만 바꾼 **최소대조쌍(counterfactual twin)** 으로 각 신호의 반응을 인과적으로 분해한다.
- 조작 요인:
  1. 문서 간 모순 유무
  2. 파라메트릭 지식과의 충돌 유무
  3. 질문 관련성
  4. 정보 신규성
  5. 어휘 중첩과 문체
  6. 문서 길이·순서·출처 수
- 주석 단위: 서로 비교 가능한 claim-pair relation을 공통 단위로 두고, 사람이 근거 span을 표시한다. token-level 신호는 claim span으로 집계하고, sequence-level 신호는 별도 분석한다.
- 평가: factor별 average treatment effect, 교란 통제 후 AUROC/AUPRC, 모델·도메인 간 전이, selective routing에 사용했을 때 risk-coverage와 실제 효용.
- 예상 가능한 강한 결론: 어떤 신호가 어떤 교란에 취약한지 밝히는 것이 목적이며, “기존 신호는 모두 무효”라는 결론을 미리 가정하지 않는다.
- 차별화: ECon·MAGIC의 직접 탐지를 확장하되, 실세계 seed + 구조적 반사실 쌍 + 이종 신호의 동일 요인 개입을 핵심 기여로 둔다.
- 주요 리스크: WikiContradict 253개만으로는 작다. 원본 사례 수보다 factor coverage와 사람 검증된 최소대조쌍 품질이 중요하며, 자동 생성 변형의 문체 아티팩트를 별도로 검사해야 한다.

### B. 불확실한 충돌 그래프에서의 선택적 전역 해소 (기법) ★방법론 추천

**가제:** *When Conflict Graphs Lie: Selective Evidence Arbitration under Noisy Claim and NLI Edges*

- 핵심 질문: claim extraction·entity resolution·NLI edge 오류가 n-ary 전역 판정에 어떻게 전파되며, 어느 사례에서는 안전하게 답하지 말아야 하는가?
- 방법:
  1. 문서를 원자 claim으로 분해
  2. support/contradiction을 binary edge가 아닌 calibrated distribution으로 표현
  3. source dependence와 node/edge uncertainty를 보존한 probabilistic signed graph 구성
  4. robust inference로 단일답·복수답·기권을 선택
- 핵심 차별점: ArbGraph와 다른 graph optimizer를 하나 더 제안하는 것이 아니다. 기존 그래프 방법이 확정값으로 처리한 **graph-construction error와 그 증폭**을 연구 대상으로 삼는다.
- 이론적 주장 범위: clean graph에서의 최적성보다, 명시한 edge corruption 조건 아래 risk bound 또는 coverage-risk 보장을 목표로 한다. 알고리즘 수렴성을 사실성 보장으로 표현하지 않는다.
- 평가: edge corruption curve, topology별 판정 뒤집힘 임계점, calibration, risk-coverage, answer/attribution quality, 동일 예산 baseline.
- 주요 리스크: SURE-RAG·EvidentialRAG도 불확실성과 3방향 결정을 다루므로, 반드시 n-ary topology + graph construction error propagation을 실험과 기여의 중심에 둬야 한다.

### C. 정정·철회·갱신을 구별하는 bitemporal provenance RAG (데이터셋 + 기법)

**가제:** *Contradiction or Supersession? Bitemporal Provenance for Retrieval-Augmented Generation*

- 핵심 질문: 모델이 단순한 recency 편향에 의존하지 않고, 서로 다른 시간 관계를 구별해 현재 시점 질문과 과거 시점 질문에 다르게 답할 수 있는가?
- 시간 표현: publication time과 fact validity time(valid-from/valid-to)을 분리한다.
- 관계 라벨: correction / retraction / supersession / 시점별 공존 / 진정한 동시 충돌.
- 데이터 후보: 뉴스 정정, 소프트웨어·클라우드 변경 로그, 공공기관 지침 개정, 논문 철회·정정 이력.
- 평가: current QA와 as-of QA를 분리하고, 최신 문서 선택 정확도가 아니라 temporal relation 분류·근거 귀속·시점별 답변 정확도를 측정.
- C 기존안과의 차이: recency×majority×authority의 조합 자체를 신규성으로 삼지 않는다. “새 문서가 옛 문서를 반박하는가, 당시에는 둘 다 참이었는가, 공식적으로 대체했는가”라는 의미적 추론을 중심에 둔다.
- 주요 리스크: 데이터 구축 비용이 크고 도메인별 정정 관행이 다르다. 1차 논문에서는 2개 도메인에 집중하는 편이 현실적이다.

### D. 복제된 다수와 독립적 합의를 구별하는 dependency-aware RAG (데이터셋 + 집계)

**가제:** *Five Sources or One? Dependency-Aware Evidence Aggregation in RAG*

- 핵심 질문: 같은 원문을 복제·요약한 여러 문서를 모델이 독립적인 다수 증거로 잘못 계산하는가?
- 방법: claim-level provenance와 derived-from / cites / near-duplicate 관계를 구성하고, raw document count 대신 independent evidence lineage를 추정해 집계한다.
- 실험: 동일 의미의 문서를 복제하는 intervention으로 다수결 효과를 측정하고, 독립 출처 수를 고정한 채 표면적 문서 수만 바꾼다.
- 평가: duplication sensitivity, confidence inflation, conflict resolution accuracy, provenance attribution.
- 차별화 조건: 단순 citation graph 또는 source credibility score만으로는 약하다. 실제 복제 계보 라벨과 인과적 duplication intervention이 필요하다.
- 주요 리스크: EPRAG 등 provenance-aware 접근과 2026년의 관련 연구가 빠르게 등장하고 있어 경쟁 확인이 필수다.

### E. 비용 민감형 충돌 행동 정책 (평가 + 정책 학습)

- 기존 B의 한쪽 채택 / 양쪽 병기 / 유보 고정 3분류를 확장한다.
- 행동 공간: 답변 / 조건부 복수답 / 추가 검색 / 사용자 명료화 요청 / 기권.
- 각 행동의 정답은 충돌 존재만으로 정하지 않고, 잘못된 단정·불필요한 기권·추가 검색 비용·사용자 지연을 포함한 utility로 정의한다.
- 평가: policy regret, utility-coverage, 추가 검색 후 정보 이득, 출처 귀속 정확도.
- 리스크: SURE-RAG·EvidentialRAG와 인접하므로, 단순 라우터가 아니라 **사용자·도메인별 오류 비용 변화에 적응하는 정책**이 핵심이어야 한다.

### F. 충돌 도메인에서의 동일 예산 재평가 (필수 실험 축)

- RAMDocs·ConflictQA·ConfRAG 등에서 다단계·다중 에이전트 방법을 동일 출력 토큰만이 아니라 전체 입력/출력 토큰, 모델 호출 수, 지연, 가능하면 금액 기준으로 비교한다.
- self-consistency·long-context 단일 호출·단일 호출 구조화 프롬프트를 포함한다.
- 독립 ACL long 주제로는 약하다. A~E의 효율성 실험 또는 재현성·분석 중심 Findings/short paper로 두는 편이 적절하다.
- “어느 결과가 나와도 기여”가 되려면 사전 등록된 비교 프로토콜, 충분한 모델·벤치마크 범위, 구조적 실패 분석이 필요하다.

### G. 충돌 해소기 대상 공격의 인증 가능한 방어 (보안/강건성)

- 기존 E의 self-supporting poisoning 공격 제안은 PURPOSE와 직접 중첩되므로 폐기한다.
- 남은 방향: PURPOSE류 adaptive attack, provenance/authority metadata 조작, retriever+resolver 공동 공격 아래 worst-case risk를 제한하는 방어.
- 공격자가 무엇을 읽고 수정할 수 있는지, 문서 수·검색 순위·metadata 조작 가능 여부를 명시한 위협 모델이 선행돼야 한다.
- 강건성 보장 없이 새로운 필터와 경험적 ASR만 제시하면 기존 방어 연구와 차별화하기 어렵다.

### H. 블랙박스 모델용 충돌 게이팅 (실용 기법, 낮은 우선순위)

- top-k logprobs도 모든 API가 제공하는 완전한 black-box 인터페이스가 아니며 모델 업데이트에 따라 동작이 바뀔 수 있다.
- 소형 프록시 신호가 대형 API 모델의 충돌 행동과 안정적으로 상관하는지, 모델·버전·도메인을 넘어 전이되는지가 먼저 검증돼야 한다.
- 단독 방법론보다는 A의 외부 신호 계열 또는 시스템 논문의 배포 실험으로 흡수하는 편이 안전하다.

### 비추천 또는 재정의가 필요한 기존 주제

| 기존 주제 | 판정 | 이유 |
|---|---|---|
| 기존 A: 실세계 스팬 비교만 수행 | **A로 재정의** | 측정 단위가 다른 신호들의 단순 AUC 비교는 약함. 인과적 factor 분해가 필요 |
| 기존 B: 표출·기권·보정 최초 통합 | **독립 신규성 상실** | EMNLP 2022, SURE-RAG, EvidentialRAG와 중첩 |
| 기존 C: recency×majority×authority 최초 교차 | **C 또는 D로 재정의** | 세 휴리스틱은 진실성 기준이 아니며 EPRAG 등 인접 연구 등장 |
| 기존 D: clean signed graph의 보장 | **B로 재정의** | 입력 edge 오류를 무시한 최적성은 사실성 보장이 아님 |
| 기존 E: resolver 표적 poisoning | **공격안 폐기, 방어로 전환** | PURPOSE가 직접 선점 |
| 기존 F: 동일 예산 메타 연구 | **필수 실험 축으로 흡수** | 단독 long paper 기여는 제한적 |
| 기존 G: top-k logprob 게이팅 | **낮은 우선순위** | 완전한 black-box가 아니고 API·모델 버전 의존성이 큼 |

### 최종 추천

자원이 제한적이면 **A: 충돌 신호의 인과적 타당성 감사**가 가장 안전하다. 대규모 학습 없이도 기존 방법의 핵심 전제를 검증할 수 있고, 성공 여부가 단순 SOTA 정확도에 덜 의존한다.

방법론 중심 ACL long을 목표로 하면 **A의 진단 결과를 B의 noisy-graph selective resolver로 연결**하는 구성이 가장 강하다. 단, 데이터셋·진단·그래프 방법을 모두 얕게 넣지 말고 다음 하나의 주장으로 통일해야 한다.

> 기존 충돌 신호는 contradiction과 distribution shift를 충분히 분리하지 못하며, 이 오류는 n-ary evidence graph에서 증폭된다. 이를 검증하는 통제된 최소대조쌍과 edge uncertainty를 보존하는 selective arbitration을 제안한다.

C와 D는 데이터 구축 자원이 있을 때 유망하다. E는 경쟁 연구와의 차별화를 더 정교하게 설계해야 한다. F는 모든 후보의 공통 실험 프로토콜로 포함한다. G와 H는 현재 상태로는 우선순위가 낮다.

**주의**: arXiv:2605.30087 (*Selective QA over Conflicting Multi-Source Personal Memory*)은 이 리포지토리의 pilot2(메모리 충돌)와 프레이밍이 사실상 동일하므로, 별도 주제로 진행하기 전에 선행·경쟁 관계를 직접 확인해야 한다.


## 5. 문서 구성

| 파일 | 내용 |
|---|---|
| [01_tug_of_war.md](01_tug_of_war.md) | Tug-of-War Between Knowledge (LREC-COLING 2024) 상세 분석 |
| [02_coiecd.md](02_coiecd.md) | COIECD: Adaptive Decoding with Information-Entropy Constraint (ACL 2024) 상세 분석 |
| [03_self_rag.md](03_self_rag.md) | Self-RAG (ICLR 2024) 상세 분석 |
| [04_ramdocs_madam_rag.md](04_ramdocs_madam_rag.md) | RAMDocs / MADAM-RAG (COLM 2025) 상세 분석 |
| [05_conflictrag.md](05_conflictrag.md) | ConflictRAG (투고 중) 상세 분석 |
| [06_conflict_aware_rag.md](06_conflict_aware_rag.md) | Conflict-Aware RAG (WWW '26) 상세 분석 |
| [07_faithfulrag.md](07_faithfulrag.md) | FaithfulRAG (ACL) 상세 분석 |
| [08_synthesis_and_topics.md](08_synthesis_and_topics.md) | 초기 종합(3절 조사 반영 이전 버전). 최신 내용은 이 README가 우선 |
| [09_multihop_conflict_landscape.md](09_multihop_conflict_landscape.md) | MAGIC, 조건부 모순, ConfRAG, 최신 graph/hypergraph RAG를 대조한 멀티홉ㆍ고차 충돌 조사와 신규 주제 |

각 상세 분석 파일은 공통 구조를 따른다: 핵심 요약 / 방법론 / 주요 결과 / 저자 명시 한계 / 비판적 분석 한계 / 후속 연구 여지.
