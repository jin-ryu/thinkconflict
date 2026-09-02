# 03 문서 안내

이 폴더의 문서는 모두 같은 비중으로 읽을 필요가 없다. 현재 의사결정은 아래 두 문서만 보면 된다.

## 먼저 읽을 문서

1. [Pilot A 계획서](pilot_a_plan.md)  
   지금 무엇을 왜 실험하며, 데이터ㆍ조건ㆍ모델ㆍGo/No-Go 기준이 무엇인지 정리한 실행 기준 문서다.
2. [데이터셋 선택 요약](dataset_decision.md)  
   MAGIC을 핵심 데이터로 쓰지 못한 이유, ProofWriter를 선택한 이유, 합성 데이터 비판에 대한 대응을 쉬운 말로 정리한 문서다.

상위 ACL 연구 전체의 문제 설정과 최종 방법론은 [상위 README](../README.md)를 본다.

## 필요할 때만 읽을 근거 문서

| 문서 | 역할 | 언제 보는가 |
|---|---|---|
| [ProofWriter 가능성 검사](proofwriter_feasibility.md) | 공식 아카이브ㆍschemaㆍhop 후보 수ㆍ라이선스 상태 | 데이터가 실제로 충분한지 수치와 checksum을 확인할 때 |
| [MAGIC 품질 감사 상세](data_quality_audit_findings.md) | 15개 prescreen과 proof-soundness 실패 유형 | MAGIC 제외 판단의 기술적 근거를 확인할 때 |
| [기존 연구로 검증된 사실](prior_validated_findings.md) | 재실험하지 않을 선행 결과와 남은 공백 | Related Work와 가설 경계를 확인할 때 |
| [데이터 감사 프로토콜](data_audit_protocol.md) | G1--G4 판정 규칙과 주석 절차 | 실제 데이터 검수ㆍadjudication을 수행할 때 |

## 데이터 폴더의 결과 문서

다음은 계획 문서가 아니라 실행 결과다.

| 문서 | 의미 |
|---|---|
| [NatLang dry-run 결과](../data/pilot_a/proofwriter_natlang_dry_run_report.md) | 15 conflict + 5 control 생성 구조 검사 |
| [독립 symbolic validation](../data/pilot_a/proofwriter_natlang_symbolic_validation_report.md) | forward chaining으로 proof와 conflict label 재검증 |
| [기존 MAGIC dataset report](../data/pilot_a/dataset_report.md) | 중단한 MAGIC 중심 설계의 감사 이력 |
| [데이터 README](../data/README.md) | 다운로드ㆍ재현ㆍ공개 제한 |

## 문서 상태 원칙

- `pilot_a_plan.md`와 `dataset_decision.md`는 현재 결정을 반영하는 핵심 문서다.
- 감사ㆍ가능성 문서는 결론의 근거이므로 삭제하지 않지만 일상적으로 읽을 필요는 없다.
- `data/pilot_a/`의 보고서는 실행할 때 갱신되는 결과물이다.
- 새로운 결정 문서를 만들기 전에 이 안내와 기존 핵심 문서에 합칠 수 있는지 먼저 확인한다.
