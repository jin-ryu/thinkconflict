# Pilot 1 최종 LLM 직접 판정표

> 상태: 빠른 exploratory go/no-go 판정. 인간 검토·human-human IAA가 없으므로 gold benchmark가 아니다.

## 실행 정보

- 판정 모델: `OpenAI Codex interactive agent (GPT-5-based; exact deployment checkpoint unavailable)`
- 판정 protocol: `strict-kh-direct-v1`
- 판정 방식: 자동 open-LLM API가 아니라 Codex가 질문·answer cluster·문서 snippet을 직접 읽고 strict K/H 기준으로 판정
- 표본: ConfRAG 무작위 120 + NatConfQA strict WH-mix 22 + QACC 무작위 60 = 202건
- 주의: 정확한 내부 checkpoint ID와 raw model trace는 제공되지 않으므로 완전 재현 가능한 자동 judge 결과가 아니다.

## 핵심 결과

| 데이터셋 | 표집 성격 | N | K=0 | K=1 | K>1,H>1 | 결론 |
|---|---|---:|---:|---:|---:|---|
| ConfRAG | 자연 web 무작위 prevalence | 120 | 67 | 53 | 0 | strict 복합 충돌 미관측 |
| NatConfQA | conflict/non-conflict pair 혼합 선별 | 22 | 2 | 20 | 0 | strict 복합 충돌 미관측 |
| QACC | factual 대조 무작위 | 60 | 28 | 32 | 0 | strict 복합 충돌 미관측 |

세 표본은 표집 방식이 달라 pooled prevalence를 계산하지 않는다. 핵심 prevalence 표본인 ConfRAG에서는 120건 중 0건이므로, 현재 데이터와 strict 정의는 ‘자연 검색에서 K>1,H>1이 충분히 흔하다’는 주장을 지지하지 않는다. 0/120의 양측 95% Wilson 상한은 약 3.1%다.

여러 answer cluster가 있어도 대부분은 (a) 보완 정보, (b) 하나의 모호한 answer slot을 scope/time으로 조건화하는 K=1 사례, 또는 (c) 동일 사실값의 K=1 대립이었다. 한 slot의 일반 효과와 세부 수치를 억지로 별도 unit으로 나누지 않았다.

## Operator 분포

| 데이터셋 | CONDITION | KEEP_BOTH | VERIFY_PREFER | SUPERSEDE | ABSTAIN_QUALIFY |
|---|---:|---:|---:|---:|---:|
| ConfRAG | 20 | 17 | 9 | 3 | 4 |
| NatConfQA | 10 | 0 | 7 | 3 | 0 |
| QACC | 21 | 0 | 4 | 6 | 1 |

## 연구 판단

현재 결과만으로는 자연 prevalence를 주요 동기로 삼는 ‘복합 충돌 해결 파이프라인’ 논문을 그대로 진행하기 어렵다. 다음 단계는 무작위 표본을 더 늘리기보다, 하나의 질문에 독립 answer slot이 둘 이상 존재하도록 설계된 multi-part QA 또는 여러 원자료 instance를 근거 보존 방식으로 조합한 controlled composite benchmark를 구축하고, 자연 retrieval log에서 외적 타당성을 별도 확인하는 방향이 더 타당하다.

정의를 사후에 넓혀 complementary information이나 한 slot의 여러 하위 수치를 K>1로 세면 사례 수는 증가하지만, ‘독립 core conflict unit’이라는 원래 기여가 약해지므로 권장하지 않는다.

## 전체 판정표

| ID | Dataset | K | H | Operator | 확신도 | 판정 근거 |
|---|---|---:|---:|---|---|---|
| `confrag-666` | ConfRAG | 1 | 1 | CONDITION | medium | 비만 촉진과 보호 효과는 미생물 구성·대사 조건에 따라 달라지는 동일 효과 방향 충돌이다. |
| `confrag-428` | ConfRAG | 1 | 1 | KEEP_BOTH | low | 이혼 법원의 성별 편향 방향에 관한 경험적·관점적 주장이 대립하지만 관할과 사례 차이가 크다. |
| `confrag-171` | ConfRAG | 0 | 0 | - | high | 유전·생화학·환경 요인을 결합한 단일 보완 설명뿐이다. |
| `confrag-806` | ConfRAG | 0 | 0 | - | high | 치료·가족 지원·의사소통·전문가 도움은 함께 적용 가능한 조언이다. |
| `confrag-467` | ConfRAG | 0 | 0 | - | medium | 공직 윤리와 Public Trust Doctrine은 서로 다른 법적 맥락의 예시이지 양립 불가능한 정의가 아니다. |
| `confrag-369` | ConfRAG | 1 | 1 | KEEP_BOTH | medium | 신 존재에 대한 철학·신앙적 입장은 단일 사실 선택보다 정당한 관점 보존이 필요하다. |
| `confrag-556` | ConfRAG | 0 | 0 | - | medium | Airfone 통화와 저고도 일부 휴대전화 통화는 동시에 발생할 수 있다. |
| `confrag-121` | ConfRAG | 1 | 1 | VERIFY_PREFER | high | 켄터키 최초 학교 총격의 시기·장소 후보가 동일 슬롯에서 직접 대립한다. |
| `confrag-1499` | ConfRAG | 1 | 1 | CONDITION | medium | 시간 단위의 물리적 표준과 달력·진법 표기 체계를 구분해야 상반된 설명이 해소된다. |
| `confrag-1822` | ConfRAG | 1 | 1 | CONDITION | high | 달의 여신 이름은 그리스·로마·마야 신화라는 문화 범위를 명시해야 한다. |
| `confrag-874` | ConfRAG | 0 | 0 | - | high | 설탕의 직접 원인 부정과 체중 증가를 통한 위험 상승은 양립한다. |
| `confrag-480` | ConfRAG | 0 | 0 | - | high | Manifest Destiny에 대한 단일 설명만 존재한다. |
| `confrag-1732` | ConfRAG | 1 | 1 | CONDITION | high | 피자 자체의 법적 정의와 학교급식에서 토마토소스를 채소 제공량으로 인정하는 규칙을 구분해야 한다. |
| `confrag-1872` | ConfRAG | 1 | 1 | CONDITION | high | raw/cooked의 영양 보존 우열은 식품·영양소·조리법별로 조건화해야 한다. |
| `confrag-487` | ConfRAG | 1 | 1 | CONDITION | high | 두 손가락 제스처의 방향·문화·의미가 달라 서로 다른 기원을 갖는다. |
| `confrag-1037` | ConfRAG | 0 | 0 | - | high | 유가 수입·예산 배분·우선순위는 러시아 현대화 재원의 보완 설명이다. |
| `confrag-229` | ConfRAG | 0 | 0 | - | high | 비용·복잡성·정치적 반대 등 복수 원인이 결합된 답이다. |
| `confrag-909` | ConfRAG | 1 | 1 | KEEP_BOTH | medium | 운명에 관한 개인적·심리학적 관점은 하나의 사실값으로 축약하기 어렵다. |
| `confrag-1993` | ConfRAG | 0 | 0 | - | high | 1959년 봉기 진압과 중국의 침공·점령은 망명 원인의 보완적 역사 설명이다. |
| `confrag-964` | ConfRAG | 1 | 1 | CONDITION | high | 원자 개념 제안·현대 원자론·원자 내부 발견을 discovery의 정의와 시기로 구분해야 한다. |
| `confrag-406` | ConfRAG | 0 | 0 | - | medium | 정부 붕괴 양상에 따른 통제 시나리오들이며 동일 사건에 대한 배타적 결과 주장이 아니다. |
| `confrag-1099` | ConfRAG | 0 | 0 | - | high | 인도 민족주의 운동의 서로 다른 단계와 변화 축을 보완적으로 설명한다. |
| `confrag-451` | ConfRAG | 0 | 0 | - | medium | 예수·성육신·성경·가치 등 기독교 신앙의 서로 다른 구성 요소다. |
| `confrag-564` | ConfRAG | 0 | 0 | - | high | 수확량 증대·기아 완화·식량 자급은 같은 Green Revolution 목표의 수단과 결과다. |
| `confrag-1120` | ConfRAG | 1 | 1 | KEEP_BOTH | high | 가장 존경받는 래퍼는 평가 기준과 개인 선호에 따라 후보가 달라지는 주관적 판단이다. |
| `confrag-1332` | ConfRAG | 1 | 1 | KEEP_BOTH | high | Horseshoe Theory의 설명력에 대한 정치학적 찬반 관점을 함께 제시해야 한다. |
| `confrag-1975` | ConfRAG | 0 | 0 | - | high | 정부 통제·재정·정치적 기반 등 폐지 동기의 보완 설명이다. |
| `confrag-1854` | ConfRAG | 1 | 1 | VERIFY_PREFER | high | HFCS가 다른 당과 유사한 위험인지 고유한 주원인인지에 관한 경험적 주장이 대립한다. |
| `confrag-1751` | ConfRAG | 0 | 0 | - | high | 유전·문화·해부·언어는 인간 지능 진화의 병존 가능한 요인이다. |
| `confrag-1415` | ConfRAG | 1 | 1 | KEEP_BOTH | high | 징병제 필요성·자유·공동책임에 대한 규범적 정책 판단이 대립한다. |
| `confrag-664` | ConfRAG | 1 | 1 | VERIFY_PREFER | high | 적정량 MSG의 안전성과 독성 위험에 대한 동일 건강 사실 주장을 근거 수준으로 검증해야 한다. |
| `confrag-983` | ConfRAG | 0 | 0 | - | high | 개인별 선호 차이를 인정하는 긍정 답들은 양립하며 언급 부재 문서는 반대 근거가 아니다. |
| `confrag-640` | ConfRAG | 0 | 0 | - | high | 재귀성과 선천 구조·사회문화 고려는 Chomsky–Everett 논쟁의 보완적 쟁점이다. |
| `confrag-1610` | ConfRAG | 0 | 0 | - | high | 핵융합·양자컴퓨팅·의료영상은 helium-3의 서로 다른 응용이다. |
| `confrag-633` | ConfRAG | 1 | 1 | KEEP_BOTH | medium | 임사체험의 생물학적 설명과 영적 해석은 증거 성격이 달라 불확실성을 표시해 병기해야 한다. |
| `confrag-918` | ConfRAG | 1 | 1 | KEEP_BOTH | high | 영국 축구 최고 역사는 우승·기간·시대 등 평가 기준에 따라 달라지는 가치 판단이다. |
| `confrag-1708` | ConfRAG | 0 | 0 | - | high | 참여 규모·불의 노출·활동 방해·정치 지지는 시위 효과의 보완 메커니즘이다. |
| `confrag-1563` | ConfRAG | 1 | 1 | VERIFY_PREFER | medium | 태평양 함대 무력화라는 일본의 전략 목적과 미국 참전을 의도했다는 주장이 역사적 의도 슬롯에서 대립한다. |
| `confrag-1352` | ConfRAG | 1 | 1 | KEEP_BOTH | high | 마리아의 영구 동정에 관한 가톨릭·정교회 전통과 성서 해석의 교리적 관점 차이다. |
| `confrag-1810` | ConfRAG | 0 | 0 | - | high | 효과가 있다는 주장과 다른 열량 제한식보다 우월하지 않다는 주장은 양립한다. |
| `confrag-1731` | ConfRAG | 1 | 1 | SUPERSEDE | medium | 미국 LGBT 비율 3.5–5%와 7.1%는 조사 연도·정의가 다른 시계열 추정치로 최신 기준을 정해야 한다. |
| `confrag-435` | ConfRAG | 0 | 0 | - | high | 잔혹형 금지의 일반 원칙과 교정시설·비례성 적용은 보완 관계다. |
| `confrag-1476` | ConfRAG | 0 | 0 | - | medium | 보안·전자파 위험 가능성과 예방조치 시 안전하다는 주장은 조건부로 양립한다. |
| `confrag-323` | ConfRAG | 0 | 0 | - | high | 10월에 기여를 기념하는 집단은 복수일 수 있어 후보들이 상호 배타적이지 않다. |
| `confrag-497` | ConfRAG | 0 | 0 | - | high | 신념·경제환경·낙인 스트레스는 문화가 비만에 미치는 보완 경로다. |
| `confrag-1382` | ConfRAG | 0 | 0 | - | high | 법·교육·권력 형성·대화는 인종주의 완화의 병행 전략이다. |
| `confrag-1602` | ConfRAG | 0 | 0 | - | high | 주된 처형 방식으로는 폐기됐지만 일부 주에서 여전히 사용된다는 설명은 양립한다. |
| `confrag-873` | ConfRAG | 1 | 1 | VERIFY_PREFER | high | 유럽의 마지막 로마군을 누가 언제 격파했는지에 대한 역사적 사실 후보가 직접 대립한다. |
| `confrag-1805` | ConfRAG | 0 | 0 | - | high | 대통령 투표가 선거인단을 결정한다는 동일 설명이다. |
| `confrag-1973` | ConfRAG | 0 | 0 | - | high | 관련 문서가 권한 여부를 답하지 못하는 불충분 사례이며 반대 주장은 없다. |
| `confrag-86` | ConfRAG | 1 | 1 | CONDITION | high | 최초 지역 노조·최초 전국 조직·최초 공인 전국 조직의 범위를 구분해야 한다. |
| `confrag-1895` | ConfRAG | 1 | 1 | KEEP_BOTH | medium | crony capitalism을 자본주의의 형태로 볼지 자본주의에 반하는 현상으로 볼지 개념·이념적 관점이 대립한다. |
| `confrag-1771` | ConfRAG | 1 | 1 | CONDITION | high | new media의 시작은 디지털 기술·개인용 컴퓨팅·소셜미디어 중 어떤 정의를 쓰는지에 따라 달라진다. |
| `confrag-1154` | ConfRAG | 0 | 0 | - | high | KCR/TRS와 학생·지식인 등 광범위한 참여자는 포함 관계다. |
| `confrag-19` | ConfRAG | 1 | 1 | CONDITION | medium | values가 규범 가치·정상 참고치·성과 지표 중 무엇을 뜻하는지 질문 의미를 조건화해야 한다. |
| `confrag-649` | ConfRAG | 0 | 0 | - | high | 미국 입국 자격이 있으면 별도 비자가 없고 그 외에는 비자가 필요하다는 동일 규칙이다. |
| `confrag-18` | ConfRAG | 0 | 0 | - | high | 찬반 논거를 요청한 질문에 서로 보완되는 양측 설명이다. |
| `confrag-826` | ConfRAG | 0 | 0 | - | high | 명료성 효용과 사용 찬반 논쟁의 존재는 양립한다. |
| `confrag-1720` | ConfRAG | 1 | 1 | SUPERSEDE | high | DHS 합의 도달과 협상 교착은 문서 시점에 따라 이전 상태가 최신 상태로 갱신된다. |
| `confrag-1785` | ConfRAG | 0 | 0 | - | high | 쿠바 혁명 역할·상징 이미지·처형 행적은 Che Guevara에 관한 서로 다른 역사 측면이다. |
| `confrag-634` | ConfRAG | 0 | 0 | - | high | 주관적 증상 평가와 의학적 감별의 어려움은 물리검사 한계의 보완 설명이다. |
| `confrag-1155` | ConfRAG | 0 | 0 | - | high | 서방이 일반 동맹으로 Sunni를 지원하면서 특정 맥락에서 Shia와 협력하는 것은 양립한다. |
| `confrag-87` | ConfRAG | 1 | 1 | VERIFY_PREFER | high | 공화당의 gerrymandering 총이익이 크다는 주장과 양당의 aggregate advantage가 없다는 경험적 주장이 대립한다. |
| `confrag-1570` | ConfRAG | 1 | 1 | CONDITION | high | 합법 porn 사이트 자체와 이를 사칭한 악성 사이트·제3자 광고를 구분해야 위험 주장이 양립한다. |
| `confrag-957` | ConfRAG | 0 | 0 | - | high | 죄책감의 문화적 원인과 행위가 의학적으로 안전하다는 설명은 양립한다. |
| `confrag-494` | ConfRAG | 0 | 0 | - | high | herbal therapy가 보조 치료일 수 있지만 단독 완치는 아니라는 데 답들이 합의한다. |
| `confrag-1010` | ConfRAG | 0 | 0 | - | high | 통화정책 경직성·충격 전파·자원 비용은 금본위제 반대의 보완 근거다. |
| `confrag-437` | ConfRAG | 1 | 1 | SUPERSEDE | medium | 세계 성인 HIV prevalence 수치가 조사 연도에 따라 달라지므로 최신 동일 연령 기준으로 갱신해야 한다. |
| `confrag-1937` | ConfRAG | 0 | 0 | - | high | 공룡의 시기·지역·다양화 계기는 서로 보완되며 인간 이전이라는 설명과도 양립한다. |
| `confrag-655` | ConfRAG | 1 | 1 | ABSTAIN_QUALIFY | high | 인공감미료가 설탕보다 안전한지 더 위험한지 근거가 불확정적이므로 단일 우열 선택을 유보해야 한다. |
| `confrag-241` | ConfRAG | 0 | 0 | - | high | Eye of Providence에 대한 일관된 상징 설명만 있다. |
| `confrag-602` | ConfRAG | 0 | 0 | - | high | 설탕이 주원인은 아니라는 주장과 위험을 높이는 중요한 요인이라는 주장은 양립한다. |
| `confrag-1172` | ConfRAG | 0 | 0 | - | high | 관계 불만·개인 성향·기회는 외도의 병존 가능한 원인이다. |
| `confrag-228` | ConfRAG | 1 | 1 | CONDITION | high | Commonwealth·영국·뉴질랜드·Queensland·미국 등 관할별 최초 의회와 의장을 구분해야 한다. |
| `confrag-1754` | ConfRAG | 1 | 1 | CONDITION | medium | 고대 중국 지배와 근대 프랑스 식민전쟁 중 imperial power의 시대·정의를 명시해야 한다. |
| `confrag-876` | ConfRAG | 0 | 0 | - | high | 생백신 위험·낮은 면역반응·백신이 면역계를 약화시키지 않는다는 주장은 서로 다른 효과다. |
| `confrag-1700` | ConfRAG | 1 | 1 | KEEP_BOTH | high | 의료용 대마 비범죄화의 정책 찬반과 입법 경로에 관한 규범적 입장 차이다. |
| `confrag-1105` | ConfRAG | 0 | 0 | - | high | 예술 표현·직접 선동 부재·장르 보편성은 기소하지 않는 이유의 보완 설명이다. |
| `confrag-543` | ConfRAG | 1 | 1 | ABSTAIN_QUALIFY | high | 생명 기원의 primordial soup·panspermia·geysers 등 가설은 현재 근거로 하나를 확정하기 어렵다. |
| `confrag-1647` | ConfRAG | 1 | 1 | VERIFY_PREFER | high | 점성술의 정치 예측 정확성에 관한 긍정·부정 주장을 경험적 검증으로 평가해야 한다. |
| `confrag-110` | ConfRAG | 0 | 0 | - | high | 상업화 비판과 음악을 통한 집단 표현은 병존 가능한 해석이며 곡의 품질 평가는 질문과 다르다. |
| `confrag-1399` | ConfRAG | 1 | 1 | KEEP_BOTH | high | 배울 최적의 영어 억양은 학습 목적·사용 지역·개인 선호에 따른 가치 판단이다. |
| `confrag-481` | ConfRAG | 0 | 0 | - | high | 정당 규칙 아래 primary·caucus·district·state 절차로 대의원을 선발한다는 포함 관계다. |
| `confrag-1938` | ConfRAG | 1 | 1 | CONDITION | high | 현재 완공된 최고층 Burj Khalifa와 미래 완공 예상 Jeddah Tower를 상태·시점으로 구분해야 한다. |
| `confrag-1325` | ConfRAG | 1 | 1 | KEEP_BOTH | high | 영아 사후 운명과 원죄에 대한 교파·성서 해석이 달라 단일 사실로 확정할 수 없다. |
| `confrag-60` | ConfRAG | 0 | 0 | - | high | 27개 주가 일부라도 북쪽이고 13개 주가 전역이 북쪽이라는 서로 다른 기준의 수치다. |
| `confrag-979` | ConfRAG | 0 | 0 | - | high | 기후·토양·관개·인프라·경제성은 캘리포니아 농업의 보완 설명이다. |
| `confrag-401` | ConfRAG | 0 | 0 | - | high | 인터넷 망중립성 질문에서 부동산 데이터의 동명 용례는 무관 문서이지 반대 claim이 아니다. |
| `confrag-1355` | ConfRAG | 1 | 1 | CONDITION | high | visa 보유 자체와 EAD 자격을 주는 별도 immigration status·신청 범주를 구분해야 한다. |
| `confrag-1537` | ConfRAG | 0 | 0 | - | high | 국제 승인·영토·국가성 요건은 신생 국가 설립 장벽의 보완 설명이다. |
| `confrag-1965` | ConfRAG | 0 | 0 | - | high | AI의 독립적 도덕 판단 능력 부재라는 단일 주장만 있다. |
| `confrag-1304` | ConfRAG | 1 | 1 | KEEP_BOTH | high | 예수 없이 가능한 세속적 영성과 예수 중심 기독교 영성은 신념 체계의 관점 차이다. |
| `confrag-1` | ConfRAG | 1 | 1 | KEEP_BOTH | medium | 창조론 내부에서도 홍수 배수 위치·메커니즘에 서로 다른 비검증적 해석이 존재한다. |
| `confrag-305` | ConfRAG | 0 | 0 | - | high | 9·11 리더십·선거 전략·상대 약점·2000년 판결은 두 차례 당선의 서로 다른 기여 요인이다. |
| `confrag-705` | ConfRAG | 1 | 1 | VERIFY_PREFER | high | Maratha guerrilla tactics가 자생했는지 Malik Ambar·Deccan 군대에서 차용했는지 역사적 기원 주장이 대립한다. |
| `confrag-1858` | ConfRAG | 0 | 0 | - | high | 실종 사례는 있으나 납치의 증거는 없고 자연현상·인적 오류로 설명된다는 데 합의한다. |
| `confrag-924` | ConfRAG | 0 | 0 | - | high | 역사적 원인과 최근 증가 증거를 보완적으로 제시한다. |
| `confrag-895` | ConfRAG | 0 | 0 | - | medium | California duty-day tax와 연방·주 세금 결합은 198.8% 계산의 병존 가능한 구성 요소다. |
| `confrag-389` | ConfRAG | 0 | 0 | - | high | 문화 상징이 운명 인식과 집단 행동에 영향을 준다는 단일 주장이다. |
| `confrag-646` | ConfRAG | 0 | 0 | - | high | 일반인의 만성질환 예방 효과는 낮지만 결핍 등 특정 집단에는 유익할 수 있다는 조건부 합의다. |
| `confrag-1195` | ConfRAG | 0 | 0 | - | high | 증거 수집 시간과 불명확한 법적 기준은 FTC 조치 지연의 보완 설명이다. |
| `confrag-1066` | ConfRAG | 1 | 1 | CONDITION | high | 일본의 최악 환경문제는 평가 시기·피해 지표·지역에 따라 대기오염·기후·산업오염·산불로 달라진다. |
| `confrag-734` | ConfRAG | 1 | 1 | KEEP_BOTH | high | 가장 영향력 있는 가수는 영향력 기준과 평가자에 따라 달라지는 가치 판단이다. |
| `confrag-1650` | ConfRAG | 1 | 1 | CONDITION | high | Iraq 직접 예산·장기 간접비용·Iraq와 Afghanistan 합산액의 비용 범위를 구분해야 한다. |
| `confrag-1094` | ConfRAG | 0 | 0 | - | high | 변경 내용·Lucas의 목적·팬 반응은 서로 보완되는 설명이다. |
| `confrag-404` | ConfRAG | 1 | 1 | CONDITION | high | FY2025 enacted/requested DoD 예산·총 budgetary resources·FY2026 proposal은 회계연도와 범위가 다르다. |
| `confrag-1691` | ConfRAG | 1 | 1 | VERIFY_PREFER | medium | 각 의회가 모든 proceedings를 공개할 법적 의무가 있는지에 대한 yes/no 주장을 헌법상 예외와 함께 검증해야 한다. |
| `confrag-1381` | ConfRAG | 0 | 0 | - | high | 연방제·지방자치·주별 기준은 경찰 조직 분산의 동일 원인 체계다. |
| `confrag-85` | ConfRAG | 1 | 1 | CONDITION | high | Act의 명문 정의 부재와 판례·Mitakshara상 ancestral/coparcenary property 용례를 법원천별로 구분해야 한다. |
| `confrag-1629` | ConfRAG | 0 | 0 | - | high | 위험 분담·비용 상쇄·경쟁력·고용 유지는 기업 보조금 요청의 보완 동기다. |
| `confrag-541` | ConfRAG | 1 | 1 | ABSTAIN_QUALIFY | high | WiFi 수면 근접의 안전·위험 연구가 충돌하고 문맥도 불확정적이므로 확신을 제한해야 한다. |
| `confrag-1934` | ConfRAG | 1 | 1 | ABSTAIN_QUALIFY | high | aura를 초자연적 실재·학습 능력·시각 현상으로 보는 주장은 과학적 근거가 부족해 단일 실재 주장으로 확정할 수 없다. |
| `confrag-703` | ConfRAG | 1 | 1 | CONDITION | high | 배우자 상대 일반 불법행위·정신적 손해·제3자 alienation of affection는 관할과 청구 원인에 따라 가능 여부가 달라진다. |
| `confrag-846` | ConfRAG | 0 | 0 | - | high | Espionage Act·공개 방식·법정 채널·제도 한계는 Snowden 보호 부재의 보완 설명이다. |
| `confrag-907` | ConfRAG | 1 | 1 | KEEP_BOTH | medium | 성구의 권한 주체와 heaven–earth 방향에 관한 교단·번역별 신학 해석을 병기해야 한다. |
| `confrag-49` | ConfRAG | 0 | 0 | - | high | 권력 남용·공직자 강요·공적 권한 남용은 동일 기소의 혐의명과 행위 설명이다. |
| `confrag-1607` | ConfRAG | 0 | 0 | - | high | Jesuit 창설·선교·교육·문화 교류·Counter-Reformation 역할은 보완 정보다. |
| `confrag-1032` | ConfRAG | 0 | 0 | - | high | 두 답 모두 섬유·불포화지방이 많은 자연식품이 단순 low-fat 표시보다 낫다는 데 합의한다. |
| `confrag-570` | ConfRAG | 0 | 0 | - | medium | 장기 내전의 다양한 행위자와 특정 시점의 주된 HTS 공세는 포함·시점 관계이며 직접 대립하지 않는다. |
| `confrag-1861` | ConfRAG | 0 | 0 | - | high | 인성·리더십 프로그램과 사회 변화 적응은 BSA 중요성의 보완 설명이다. |
| `natconfqa-climate-fever.70.1` | NatConfQA | 1 | 1 | VERIFY_PREFER | high | CO2–온도 관계가 강하고 온난화를 증폭한다는 주장과 관계가 약하거나 포화됐다는 주장이 대립한다. |
| `natconfqa-climate-fever.82.1` | NatConfQA | 1 | 1 | VERIFY_PREFER | medium | CO2 두 배 증가 시 온도 민감도 수치가 동일 질문 슬롯에서 달라 모델·근거를 검증해야 한다. |
| `natconfqa-climate-fever.78.1` | NatConfQA | 1 | 1 | SUPERSEDE | high | 2007 high-end 60cm가 2014 약 90cm로 갱신되며 나머지 값은 시점·배출 시나리오별 조건값이다. |
| `natconfqa-climate-fever.79.1` | NatConfQA | 1 | 1 | CONDITION | high | 감가상각된 기존 coal과 신규 wind·fossil 설비의 비용을 자산 연식·지역·비용 지표로 구분해야 한다. |
| `natconfqa-climate-fever.40.1` | NatConfQA | 0 | 0 | - | medium | 21세기·수세기·수천년 및 severe scenario가 다른 전망치로, 명시된 시간 범위에서는 함께 참일 수 있다. |
| `natconfqa-climate-fever.46.1` | NatConfQA | 1 | 1 | SUPERSEDE | high | 기록이 추가되며 1998·2005에서 2016으로 warmest year가 갱신되는 시계열 사실이다. |
| `natconfqa-climate-fever.45.1` | NatConfQA | 1 | 1 | CONDITION | high | Arctic ice-free 예측 시점은 예측 발표연도·모델·ice-free 정의에 따라 크게 달라진다. |
| `natconfqa-healthver_4_claims_12.89.1` | NatConfQA | 1 | 1 | CONDITION | medium | PPE 부족은 감염·시스템 위험 원인이고 pneumonia·respiratory failure는 환자의 근접 사망 원인이므로 인과 수준을 구분해야 한다. |
| `natconfqa-healthver_2_claims_31.88.1` | NatConfQA | 1 | 1 | CONDITION | medium | 온도 영향의 방향과 1°C당 계수는 독립 unit이 아니라 같은 temperature–transmission 효과 슬롯이며, 재생산지수·누적확진·지역·온도구간별 추정치를 조건화해야 한다. 일부 source answer–evidence 연결은 원문과 불일치한다. |
| `natconfqa-climate-fever.58.1` | NatConfQA | 0 | 0 | - | high | 규제 제한 표결·Clean Power Plan 반대·수정안 공동발의는 Portman의 서로 다른 의정 행위다. |
| `natconfqa-climate-fever.41.1` | NatConfQA | 1 | 1 | VERIFY_PREFER | high | CO2 흡수가 산성도를 높인다는 화학 과정과 산성도에 영향이 없다는 주장이 직접 대립한다. |
| `natconfqa-climate-fever.30.1` | NatConfQA | 1 | 1 | VERIFY_PREFER | high | 20세기 온도 추세가 상승·하락·무상승이라는 방향 주장으로 직접 대립한다. |
| `natconfqa-climate-fever.37.1` | NatConfQA | 1 | 1 | CONDITION | high | 온난화가 growing season을 늘리거나 줄인다는 효과는 지역·작물·온도 범위로 조건화해야 한다. |
| `natconfqa-climate-fever.84.1` | NatConfQA | 1 | 1 | CONDITION | medium | 해수면 표층 온도가 하락 또는 상승한다는 주장은 대상 해역·사건·기간 범위가 누락돼 있다. |
| `natconfqa-climate-fever.61.1` | NatConfQA | 1 | 1 | CONDITION | medium | 수십 cm와 수 m 전망은 기간·배출·빙상 붕괴 시나리오가 다른 동일 sea-level amount 슬롯이다. |
| `natconfqa-climate-fever.48.1` | NatConfQA | 1 | 1 | VERIFY_PREFER | high | 우주선이 구름량·기후에 유의한 영향을 준다는 주장과 통계적으로 영향이 없다는 주장이 대립한다. |
| `natconfqa-climate-fever.44.1` | NatConfQA | 1 | 1 | SUPERSEDE | high | 21세기 high-end 60cm가 후속 평가에서 90cm로 갱신되고 61–110cm 범위와 조정된다. |
| `natconfqa-healthver_10_claims_16.87.1` | NatConfQA | 1 | 1 | VERIFY_PREFER | high | 사회적 거리두기가 성장률을 낮추는지 영향이 없는지에 대한 경험적 효과 주장이 직접 대립한다. |
| `natconfqa-climate-fever.62.1` | NatConfQA | 1 | 1 | CONDITION | high | Republican Party 내부의 기후변화 존재·인간 기여 입장은 인물·시기·공식 platform별로 이질적이다. |
| `natconfqa-climate-fever.69.1` | NatConfQA | 1 | 1 | VERIFY_PREFER | medium | NOAA 연구자의 엄정성·조작 부재와 데이터 투명성 부족 주장을 공개 기록으로 검증해야 한다. |
| `natconfqa-climate-fever.38.1` | NatConfQA | 1 | 1 | CONDITION | high | Paris Accord의 국가별 자발 목표 존재와 법적 구속·집행 목표 부재를 target의 의미로 구분해야 한다. |
| `natconfqa-climate-fever.43.1` | NatConfQA | 1 | 1 | CONDITION | medium | Antarctic ice mass 순변화의 부호는 관측기간·지역·측정법과 thickness 정보에 따라 달라진다. |
| `qacc-1283` | QACC | 0 | 0 | - | high | Boss Baby soundtrack 가수는 Missi Hale로 문서가 일치한다. |
| `qacc-0880` | QACC | 1 | 1 | CONDITION | high | town 전체 최대 34와 household·lot당 4, VIP별 5–6을 범위로 구분해야 한다. |
| `qacc-0958` | QACC | 1 | 1 | CONDITION | high | 최초 실험 텔레비전 중계 1939와 최초 coast-to-coast·national broadcast를 중계 범위로 구분해야 한다. |
| `qacc-0456` | QACC | 1 | 1 | CONDITION | high | 1971 TV movie와 정규 CBS series의 1972-09-14 첫 방영을 구분해야 한다. |
| `qacc-0146` | QACC | 1 | 1 | VERIFY_PREFER | high | Cassie 사망 episode 날짜가 2005-05-24와 2005-03-24로 직접 대립한다. |
| `qacc-0201` | QACC | 0 | 0 | - | high | Yom Kippur War에 대한 Arab oil embargo·생산 감소·가격 상승은 1973–74 위기의 보완 원인이다. |
| `qacc-0870` | QACC | 0 | 0 | - | high | 2017 Laureus World Sportsman 수상자는 Usain Bolt로 관련 근거가 일치한다. |
| `qacc-0156` | QACC | 1 | 1 | CONDITION | high | 146·180·184·185 수치는 조사일과 visa-free에 visa-on-arrival·territories를 포함하는지에 따라 달라진다. |
| `qacc-0657` | QACC | 1 | 1 | SUPERSEDE | high | 2018 Super Bowl LII가 과거 최신이었으나 Eagles가 2023 Super Bowl LVII에 출전해 최신값이 갱신됐다. |
| `qacc-0287` | QACC | 0 | 0 | - | high | 2018 New York U.S. Open golf 우승자는 Brooks Koepka로 문서가 일치한다. |
| `qacc-1588` | QACC | 1 | 1 | CONDITION | medium | Gandhi Nagar의 기준 지점·경계와 도보 입구에 따라 Seelampur·East Azad Nagar·Shastri Park가 달라진다. |
| `qacc-1503` | QACC | 0 | 0 | - | high | Snow Dogs의 Nana는 Border Collie로 관련 근거가 일치한다. |
| `qacc-0067` | QACC | 1 | 1 | VERIFY_PREFER | high | Columbo의 개가 이름 없이 Dog로 불렸다는 다수 근거와 원래 Fang이라는 주장이 대립한다. |
| `qacc-0365` | QACC | 0 | 0 | - | high | Bob 배역 배우를 명시하는 충분한 근거와 반대 후보가 없어 불충분 사례다. |
| `qacc-1333` | QACC | 1 | 1 | CONDITION | high | 공식 PGA Tour 82승과 과거 81승·대안 Snead criteria 95승을 기준일과 집계 규칙으로 구분해야 한다. |
| `qacc-1430` | QACC | 0 | 0 | - | high | 문서들은 June 16과 1976 Soweto uprising을 설명하지만 최초 기념 연도를 서로 다르게 주장하지 않는다. |
| `qacc-1339` | QACC | 0 | 0 | - | high | Kelly Taylor의 어머니 Jackie 역은 Ann Gillespie로 문서가 일치한다. |
| `qacc-1086` | QACC | 1 | 1 | CONDITION | high | 방송 premiere 2017-09-28과 home-media 상품 출시 2018-10-22를 release 매체로 구분해야 한다. |
| `qacc-0296` | QACC | 1 | 1 | CONDITION | high | Gavin and Stacey의 Smithy 여동생 Rudi 역 Sheridan Smith와 James Corden의 실제 자매 cameo를 구분해야 한다. |
| `qacc-0741` | QACC | 1 | 1 | CONDITION | high | 1947 첫 영국인 Commander-in-Chief Lockhart·첫 인도인 Cariappa·COAS 명칭의 첫 Rajendrasinhji를 직함·국적·시기로 구분해야 한다. |
| `qacc-0973` | QACC | 1 | 1 | SUPERSEDE | high | Elizabeth II 재위기의 Charles 답이 왕위 계승 후 William으로 갱신됐다. |
| `qacc-1296` | QACC | 0 | 0 | - | high | 첫 Horrid Henry 책은 1994년에 쓰이고 출판된 것으로 근거가 일치한다. |
| `qacc-1187` | QACC | 1 | 1 | CONDITION | medium | 유사 제목·가사를 가진 The Dramatics의 1971 곡과 Milira의 1990 곡 및 후속 cover를 정확한 제목·녹음으로 구분해야 한다. |
| `qacc-0855` | QACC | 1 | 1 | CONDITION | medium | 1st Middlesex and Norfolk와 Norfolk, Bristol and Middlesex는 다른 선거구이므로 정확한 district 명칭·시점이 필요하다. |
| `qacc-0470` | QACC | 0 | 0 | - | high | Simon Commission의 1928 방문 당시 Viceroy는 Lord Irwin으로 문서가 일치한다. |
| `qacc-1477` | QACC | 0 | 0 | - | high | shortstop 최다 Gold Gloves는 Ozzie Smith 13회로 일치한다. |
| `qacc-0853` | QACC | 1 | 1 | CONDITION | high | Arnold Winkler 역 Ronnie Dapo와 Arnold Bailey 역 Sheldon Collins는 같은 프로그램의 서로 다른 Arnold 캐릭터다. |
| `qacc-0191` | QACC | 1 | 1 | VERIFY_PREFER | high | 모든 변 길이만 같은 polygon은 equilateral이며 각까지 같아야 regular라는 수학 정의와 regular 답이 대립한다. |
| `qacc-0658` | QACC | 1 | 1 | CONDITION | high | 1917-04-02 Wilson의 선전포고 요청과 04-06 공식 참전을 사건 단계로 구분해야 한다. |
| `qacc-0729` | QACC | 1 | 1 | CONDITION | high | 세계·프랑스·스위스 및 공개·비공개·공식 처형 범위를 구분하면 1939·1940·1977이 해소된다. |
| `qacc-0574` | QACC | 0 | 0 | - | high | Guyana의 첫 executive president는 Forbes Burnham으로 근거가 일치한다. |
| `qacc-0376` | QACC | 1 | 1 | VERIFY_PREFER | high | Arrow는 8시즌으로 종료됐다는 근거와 9시즌·새 episode가 나온다는 비공식 주장을 구분해 검증해야 한다. |
| `qacc-1423` | QACC | 0 | 0 | - | high | calculus의 독립 발명자는 Isaac Newton과 Gottfried Wilhelm Leibniz로 일치한다. |
| `qacc-1394` | QACC | 0 | 0 | - | high | Princess Tilde 역은 Hanna Alström으로 일치한다. |
| `qacc-1565` | QACC | 0 | 0 | - | high | Luther Vandross와 1982 cover를 부른 가수는 Cheryl Lynn으로 일치한다. |
| `qacc-0134` | QACC | 0 | 0 | - | high | The Bacchae 말미에 maenads에게 찢긴 인물은 Pentheus로 일치한다. |
| `qacc-0965` | QACC | 0 | 0 | - | high | Virginia Declaration of Rights와 English Bill of Rights가 주요 두 선행 문서라는 근거가 일치한다. |
| `qacc-0435` | QACC | 1 | 1 | CONDITION | medium | L.K. Advani의 My Country My Life와 Ehud Barak의 동명·유사 표기 책을 저자·판본으로 구분해야 한다. |
| `qacc-0278` | QACC | 0 | 0 | - | high | 곡의 원작자·최초 가수는 Stuart Hamblen이며 다른 문서는 cover·앨범이다. |
| `qacc-0850` | QACC | 1 | 1 | SUPERSEDE | high | Valhalla가 최신이던 문서가 Mirage 출시 전후 정보로 갱신되며 upcoming Nexus는 출시작과 구분된다. |
| `qacc-1554` | QACC | 0 | 0 | - | high | From Dusk till Dawn: The Series는 3시즌 30화로 일치한다. |
| `qacc-1025` | QACC | 1 | 1 | CONDITION | medium | 현재 수상자·최초 수상자·최다 반복 수상 기록을 구분해야 하며 반복 수상자는 공동 기록일 수 있다. |
| `qacc-1424` | QACC | 1 | 1 | CONDITION | high | Holden V8 Supercar 엔진은 규정 세대·차종에 따라 5.0L에서 5.4/5.7L로 달라진다. |
| `qacc-0477` | QACC | 0 | 0 | - | medium | snippet은 Janis Joplin과 Michael McClure의 기여를 암시하지만 상반된 단독 작곡자 후보를 충분히 제시하지 않는다. |
| `qacc-0939` | QACC | 1 | 1 | CONDITION | high | Elvis와 Michael Jackson 판매량 비교는 albums·records·physical·RIAA certified·claimed worldwide sales 지표에 따라 달라진다. |
| `qacc-1065` | QACC | 0 | 0 | - | high | 방광은 비었을 때 lesser pelvis에 있고 차면 abdomen으로 확장되며 아동 위치도 다르다는 해부 설명이 양립한다. |
| `qacc-1159` | QACC | 0 | 0 | - | medium | 11대 캐나다 총리는 R. B. Bennett로 보이며 반대 후보 근거가 없다. |
| `qacc-1107` | QACC | 1 | 1 | SUPERSEDE | high | Pisa Tower 기울기는 보강 전 1990년 5.5도에서 현재 약 3.97–3.99도로 감소했다. |
| `qacc-1409` | QACC | 0 | 0 | - | high | Rock and Roll All Nite의 가수는 KISS로 일치한다. |
| `qacc-1470` | QACC | 1 | 1 | CONDITION | high | 최소 UDP payload 0 bytes·UDP datagram/header 8 bytes·IPv4/IPv6 packet 28/48 bytes를 프로토콜 계층으로 구분해야 한다. |
| `qacc-0777` | QACC | 1 | 1 | CONDITION | high | Australian one-dollar coin 1984·decimal coins 1966·colonial holey dollar 1814를 coin 종류와 통화체계로 구분해야 한다. |
| `qacc-1237` | QACC | 1 | 1 | SUPERSEDE | high | India national parks 수가 2021년 104개에서 2023년 106개로 갱신됐다. |
| `qacc-0517` | QACC | 0 | 0 | - | high | Gods and Generals의 Stonewall Jackson 역은 Stephen Lang으로 일치하며 Russell Crowe는 초기 후보였다. |
| `qacc-0202` | QACC | 1 | 1 | ABSTAIN_QUALIFY | high | Mona Lisa 완성 시점은 1506·1516·1519 및 미완성설이 있어 현재 문맥만으로 단일 완료일을 확정하기 어렵다. |
| `qacc-1256` | QACC | 0 | 0 | - | high | GDP·IGR 기준 Nigeria 최고 부유 주는 Lagos로 근거가 일치한다. |
| `qacc-1121` | QACC | 0 | 0 | - | high | Narora·Kakrapar·Tarapur는 원자력 발전소로 atomic/nuclear energy를 생산한다. |
| `qacc-1295` | QACC | 1 | 1 | CONDITION | high | 미국 최대 운영 광산·최대 매장층·과거 북미 최대·캐나다의 세계 최대를 국가·운영 상태·측정 지표로 구분해야 한다. |
| `qacc-0746` | QACC | 0 | 0 | - | medium | road transport industry 창립자의 이름을 snippet이 생략해 충분하지 않지만 서로 다른 후보 claim은 없다. |
| `qacc-1377` | QACC | 0 | 0 | - | high | 1987 Masters of the Universe의 Skeletor 역은 Frank Langella로 일치한다. |
| `qacc-0781` | QACC | 1 | 1 | SUPERSEDE | medium | Season 8의 2023-01-17 premiere 정보와 이후 Season 9 예정 정보가 query 시점에 따라 new season 값을 갱신한다. |
