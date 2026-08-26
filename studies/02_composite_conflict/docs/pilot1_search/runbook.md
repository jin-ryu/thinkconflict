# 파일럿 1 실행·재현 안내

## 0. 현재 상태

파일럿 1은 완료되었다. 최종 실행은 사전 계획의 독립 인간 주석 절차를 사용하지 않고, Codex가 202건을 직접 판정하는 exploratory protocol로 축소했다.

- protocol: `strict-kh-direct-v1`
- 최종 결과: [`result.md`](result.md)
- 최종 JSONL: [`../../data/pilot1/final_llm_judgments.jsonl`](../../data/pilot1/final_llm_judgments.jsonl)
- 전체 판정표: [`../../results/pilot1/final_llm_judgment_table.md`](../../results/pilot1/final_llm_judgment_table.md)

인간 검토와 human-human IAA는 수행하지 않았다. 아래 명령은 사용한 표본과 최종 산출물의 구조를 재현·검증하기 위한 것이다.

## 1. 원자료 재현

연구 루트에서 실행한다.

```bash
cd studies/02_composite_conflict
bash data/download.sh
PYTHONPATH=src ../../.venv/bin/python -m composite_conflict.prepare_pilot1
```

원 데이터는 `data/raw/`에 저장되며 Git에 포함되지 않는다. 고정 revision, SHA-256, 레코드 수는 `data/source_snapshots.json`에 기록한다.

생성되는 원문 포함 view도 Git에서 제외한다.

- `data/pilot1/calibration_view.jsonl`
- `data/pilot1/confrag_prevalence_view.jsonl`
- `data/pilot1/natconfqa_strict_wh_mix_view.jsonl`
- `data/pilot1/qacc_control_view.jsonl`

## 2. 최종 판정 재집계

Codex direct 판정 batch와 manifest를 검증하고 최종 JSONL·Markdown 표를 다시 생성한다.

```bash
cd studies/02_composite_conflict
PYTHONPATH=src ../../.venv/bin/python -m composite_conflict.finalize_direct_judgments
```

검증 항목:

- 202개 instance의 중복·누락
- `H≤K`
- `operator_set`과 `H`의 일치
- 데이터셋별 `K/H` 및 operator 분포

## 3. 테스트

저장소 루트에서 실행한다.

```bash
pytest -q
```

파일럿 1 코드 테스트는 표본 재현, NatConfQA evidence mapping, schema validation, agreement edge case, case review를 포함한다.

## 4. 향후 정식 주석

논문용 gold benchmark로 승격할 경우에는 [`annotation_guideline.md`](annotation_guideline.md)에 따라 별도 인간 A/B calibration, blind audit, adjudication을 수행해야 한다. 현재 direct 판정 결과를 human-verified gold로 사용하지 않는다.
