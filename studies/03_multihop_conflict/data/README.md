# Pilot A data

Pilot A의 데이터 원본과 표집ㆍ검증 산출물을 둔다.

현재 confirmatory core는 [Pilot A 계획서](../docs/pilot_a_plan.md)에 따라 **ProofWriter의 검증된 multi-hop proof를 문서 간 충돌로 변환하는 방식으로 재설계 중**이다. 아래 MAGIC 파일은 이전 설계의 감사 기록과 향후 external transfer 후보이며, 새 core 평가 입력이 아니다.


## ProofWriter 전환 산출물

- `proofwriter_feasibility.json`: 공식 아카이브 schema와 1--4 hop 후보 수 집계.
- `pilot_a/proofwriter_natlang_dry_run_manifest.json`: 원문 없는 고정 15개 source ID와 5개 paired-control 표시.
- `pilot_a/proofwriter_natlang_dry_run_validation.json`: 생성 구조ㆍterminal polarity 자동 검사.
- `pilot_a/proofwriter_natlang_symbolic_validation.json`: 독립 forward-chaining 재검사.
- `pilot_a/generated/proofwriter_natlang_dry_run.jsonl`: 원문 포함 로컬 dry run. Git에 포함하지 않는다.

현재 결과는 구조 검증 `PASS`지만 사람 semantic-equivalence 검수가 남아 있어 `dry_run_not_for_model_evaluation` 상태다. NatLang은 단항 속성 추론 중심이므로 관계형ㆍ실제 문서 일반화를 대표하지 않는다.

## 기존 MAGIC 감사 산출물

- `raw/magic/`: 공식 MAGIC의 고정 revision. Git에 포함하지 않으며 `download.sh`로 복원한다.
- `source_snapshots.json`: 원본 revision, 파일별 SHA-256, 레코드 수와 라이선스 상태.
- `pilot_a/sample_manifest.json`: 원문을 포함하지 않는 provisional 표본 ID와 reserve 순서.
- `pilot_a/review_annotations.jsonl`: 데이터 감사 판정 sidecar. 원문 대신 stable ID만 기록한다.
- `pilot_a/review_A.jsonl`, `review_B.jsonl`: G1--G4를 독립 판정하는 주석자별 sidecar.
- `pilot_a/assistant_prescreen.jsonl`: 자동 경고 11건의 비-gold 1차 검토. 교체 우선순위에만 사용한다.
- `pilot_a/reserve_coverage_prescreen.jsonl`: 3ㆍ4-conflict reserve의 G1 비-gold 직접 검토.
- `pilot_a/replacement_proposal.json`: G1만 반영한 교체 제안. G2--G4 전에는 적용하지 않는다.
- `pilot_a/proof_soundness_prescreen.jsonl`: 고정 dry-run 15개의 G3--G4 비-gold 직접 검토.
- `pilot_a/dataset_report.md`: 구성 결과와 아직 남은 gate.
- `pilot_a/structural_validation.json`: checksumㆍIDㆍ중복ㆍschema 구조 검증 결과.
- `pilot_a/structural_validation_report.md`: 구조 검증 요약과 의미 검증의 경계.
- `pilot_a/generated/`: 원문이 포함된 로컬 작업 파일. Git에 포함하지 않는다.

## 재현

```bash
bash studies/03_multihop_conflict/data/download.sh
.venv/bin/python studies/03_multihop_conflict/src/audit_proofwriter_feasibility.py
.venv/bin/python studies/03_multihop_conflict/src/prepare_proofwriter_dry_run.py
.venv/bin/python studies/03_multihop_conflict/src/validate_proofwriter_dry_run.py

# 기존 MAGIC 감사 재현이 필요한 경우에만 실행
.venv/bin/python studies/03_multihop_conflict/src/prepare_pilot_a_data.py
```

생성되는 로컬 파일은 다음과 같다.

- `audit_candidates.jsonl`: primary와 reserve의 원문ㆍtripletㆍlexical coverage 정보
- `multihop_conflicts.jsonl`: provisional multi-hop conflict 60개
- `singlehop_conflicts.jsonl`: provisional single-hop conflict 16개
- `no_conflict_templates.jsonl`: paired no-conflict 24개의 제작ㆍ검수 template
- `nli_fact_coverage.jsonl`: fact→context entailment triage 점수. Gold 판정으로 사용하지 않는다.

## 중요한 상태 구분

기존 MAGIC 표본은 `provisional_pre_audit`에서 중단됐다. 고정 dry-run 15개의 proof-soundness prescreen에서 confirmatory core로 사용할 근거가 확보되지 않았으므로 다음 작업은 수행하지 않는다.

1. 기존 MAGIC manifest를 사용한 모델 본평가
2. MAGIC proof를 기준으로 한 paired no-conflict 완성
3. MAGIC graph를 gold C3/C4로 간주한 oracle-gap 분석

관련 파일은 데이터 감사의 재현성과 MAGIC external transfer 후보 선정을 위해 삭제하지 않고 보존한다. 새 ProofWriter core는 별도 manifest와 생성ㆍsymbolic validation 산출물로 구분한다.

공식 MAGIC 저장소에는 확인 시점에 별도 라이선스 파일이나 dataset card의 license 표기가 없었다. 재배포 조건이 확인되기 전에는 원문이 포함된 `generated/`를 외부에 공개하지 않는다.
