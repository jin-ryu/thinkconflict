"""라벨링 드라이버: 생성 JSONL → 3단계 라벨 JSONL (계획서 Phase 3).

results/raw/*.jsonl (serving/client.py 산출)을 읽어 파싱·라벨링하고
results/labels/*.jsonl로 쓴다. 판정자는 대상 모델과 **다른 계열**이어야 하므로
(부록 A(a)) --judge-model이 대상 모델과 같은 계열이면 거부한다.

usage:
    python -m diagnosis.run_labeling \
        --generations results/raw/qwen_standard_dragged.jsonl \
        --data data/3_processed/dragged/dragged_temporal.jsonl \
        --out results/labels/qwen_standard_dragged.jsonl \
        [--judge-model gptoss --judge-url http://localhost:8003/v1]
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from diagnosis.labeler import build_openai_judge, label_generation
from diagnosis.metrics import print_report
from diagnosis.trace_parser import parse_record
from preprocessing.schema import assert_reviewed, read_jsonl

# 판정자 자기선호 편향 통제: 트레이스 생성 모델과 같은 계열은 그 모델의 판정에서 제외
SAME_FAMILY = {"qwen": {"qwen"}, "gemma": {"gemma"}, "gptoss": {"gptoss", "gpt"}}


def make_judge(judge_model: str | None, judge_url: str | None, target_model: str):
    if not judge_model:
        return None
    # 부분 문자열로 본다 — 실제로 넘기는 값은 서빙 모델 id("Qwen/Qwen3.6-27B")라
    # 논리명("qwen")과 정확히 일치하지 않는다. 정확 일치로 검사하면 같은 계열
    # 판정자가 가드를 그냥 통과해 자기선호 편향 통제가 무력화된다.
    if any(f in judge_model.lower() for f in SAME_FAMILY.get(target_model, set())):
        raise SystemExit(
            f"판정자 '{judge_model}'는 대상 모델 '{target_model}'과 동일 계열 — "
            "자기선호 편향 통제 위반 (부록 A(a)). 다른 계열 판정자를 지정할 것.")
    from openai import OpenAI
    client = OpenAI(base_url=judge_url or "http://localhost:8003/v1", api_key="EMPTY")
    return build_openai_judge(client, judge_model)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", required=True, type=Path)
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--judge-model")
    ap.add_argument("--judge-url")
    args = ap.parse_args()

    assert_reviewed(args.data)
    items = {it.question_id: it for it in read_jsonl(args.data)}
    records, n_unparsed = [], 0
    judge = None

    with open(args.generations, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if judge is None and args.judge_model:
                judge = make_judge(args.judge_model, args.judge_url, rec["model"])
            item = items.get(rec["question_id"])
            if item is None:
                continue
            parsed = parse_record(rec)
            if not parsed.ok:
                n_unparsed += 1
                continue  # 파싱 실패는 trace_parser의 실패율 리포트가 담당
            labels = label_generation(parsed, item, rec["doc_order"], judge)
            records.append({
                "question_id": rec["question_id"], "dataset": rec["dataset"],
                "model": rec["model"], "env": rec["env"], "seed": rec["seed"],
                "thinking": rec.get("thinking", True), **asdict(labels),
            })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as out:
        for r in records:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"라벨 {len(records)}건 → {args.out} (파싱 실패 {n_unparsed}건 제외)")
    # 행동 트랙 = **채점이 성립하는 문항**(정답이 있는 문항)이다. 기준은 fa이지 l2가
    # 아니다 — labeler는 L1 미탐지 시 l2를 None으로 두므로, l2로 거르면 L1 실패 건이
    # 통째로 빠져 Loss_L1이 구조적으로 0이 되고 blind_hit 경로가 사라진다.
    # 정답이 없는 문항(의견 충돌)만 fa=None으로 제외돼야 한다 (§3.2 이중 트랙).
    behav = [r for r in records if r.get("fa") is not None]
    if behav:
        print_report(behav, f"{args.generations.stem} — behavior track")


if __name__ == "__main__":
    main()
