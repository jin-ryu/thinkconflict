그럼# Pilot 1 execution runbook

## 1. 원자료 재현

연구 루트에서 실행한다.

```bash
cd studies/02_composite_conflict
bash data/download.sh
PYTHONPATH=src ../../.venv/bin/python -m composite_conflict.prepare_pilot1
PYTHONPATH=src ../../.venv/bin/python -m composite_conflict.prepare_audit
```

원 데이터는 `data/raw/`에 저장되고 상위 Git에는 포함되지 않는다. 고정 revision, SHA-256, 레코드 수는 `data/source_snapshots.json`에 기록된다.

## 2. 생성 파일

- `data/pilot1/calibration_view.jsonl`: 주석자 A/B가 공통으로 보는 20개
- `data/pilot1/calibration_annotations_A.jsonl`: A 전용 답안
- `data/pilot1/calibration_annotations_B.jsonl`: B 전용 답안
- `data/pilot1/confrag_prevalence_view.jsonl`: calibration 통과 후 주석할 무작위 120개
- `data/pilot1/natconfqa_strict_wh_mix_view.jsonl`: 공개 v1.0에서 재현된 strict WH-mix 22개
- `data/pilot1/qacc_control_view.jsonl`: factual control 60개
- `data/pilot1/sample_manifest.json`: seed, 표본 ID, 역할, 인간 B random audit ID
- `data/pilot1/human_B_random_audit_view.jsonl`: calibration과 겹치지 않는 데이터셋별 20% blind audit view
- `data/pilot1/human_B_random_audit.jsonl`: 인간 B용 빈 sidecar

view 파일은 원문 일부를 포함하므로 Git에서 제외하고 같은 manifest로 재생성한다. view에는 원 데이터의 conflict label과 정답 label을 넣지 않았다. 필요한 경우 `raw_locator`로 원문을 확인하되 원 gold conflict field는 보지 않는다.

## 2.1 빠른 exploratory calibration 모드

시간이 제한된 초기 go/no-go 판단에서는 `data/pilot1/llm_drafts_calibration.jsonl`의 초벌 20건을 연구자 한 명이 전수 검토한다. 검토 기준과 20건 요약표는 각각 `data/pilot1/REVIEW_GUIDE.md`, `data/pilot1/calibration_review_sheet.md`에 있다. 결과는 human-verified exploratory label로만 부르고, gold나 human-human IAA로 보고하지 않는다. 주제가 유지될 때 아래의 독립 calibration과 blind audit을 추가한다.


## 3. 독립 주석

1. A와 B에게 동일한 `calibration_view.jsonl`과 `annotation_guideline.md`를 제공한다.
2. A는 A 파일만, B는 B 파일만 편집한다.
3. 상대방 답, 중간 통계, 예상 `K/H`를 보지 않는다.
4. 각 레코드의 `status`를 `complete`로 바꾼다.
5. 제출 후에만 두 파일을 비교한다.

한 사람이 두 파일을 시간차로 작성하는 것은 독립 주석으로 인정하지 않는다. 연구 책임자가 A가 될 수 있고, B는 공동연구자·대학원생·도메인 지식을 갖춘 별도 인력이 맡을 수 있다. 제3 adjudicator는 A/B가 합의하지 못한 사례에만 필요하다.

## 4. K/H 자동 파생과 검증

사람이 unit을 입력한 뒤 `K/H`를 직접 계산하지 않는다. 다음 명령으로 새 파일을 만든다.

```bash
PYTHONPATH=src ../../.venv/bin/python -m composite_conflict.annotation_cli finalize \
  --annotations data/pilot1/calibration_annotations_A.jsonl \
  --out data/pilot1/calibration_annotations_A.final.jsonl

PYTHONPATH=src ../../.venv/bin/python -m composite_conflict.annotation_cli validate \
  --view data/pilot1/calibration_view.jsonl \
  --annotations data/pilot1/calibration_annotations_A.final.jsonl \
  --require-complete
```

B에도 동일하게 수행한다.

## 5. Agreement 계산

```bash
PYTHONPATH=src ../../.venv/bin/python -m composite_conflict.agreement \
  --view data/pilot1/calibration_view.jsonl \
  --annotator-a data/pilot1/calibration_annotations_A.final.jsonl \
  --annotator-b data/pilot1/calibration_annotations_B.final.jsonl \
  --out results/pilot1/calibration_agreement.json
```

진행 기준은 `H>1` Cohen's kappa 0.70 이상, operator macro-F1 0.75 이상이다. 미달하면 전체 표본을 주석하지 않고 guideline을 한 차례 개정해 새 calibration으로 다시 평가한다.

## 6. Calibration 통과 후 hybrid 본 주석

1. 동결된 guideline과 고정 prompt로 전체 표본의 `llm_drafts.jsonl`을 생성한다.
2. 인간 A가 모든 instance를 `accept`, `edit`, `reject`로 검토해 `human_A_verified.jsonl`을 만든다.
3. 인간 B용 random 20% ID는 모델 결과를 보기 전에 manifest에 고정한다. B에게는 LLM/A label을 숨긴 view만 제공한다.
4. random audit IAA와 A가 판정한 `H>1` 추가 감사 결과를 분리한다.
5. 인간 A/B가 합의하지 못한 audit 사례만 adjudication한다.

LLM + 인간 A 한 명만으로도 내부 feasibility 수치는 만들 수 있지만 human-human IAA가 없으므로 논문용 gold benchmark로 부르지 않는다. 논문 제출 전에는 최소 calibration과 random audit에 별도 인간 B가 필요하다.
