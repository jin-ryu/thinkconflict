"""실험 3 — 인과 개입 배터리 (계획서 §3.3.4, RQ4).

모델 내부 접근 없이 **생성 조작만으로** 구현되는 두 주력 개입과 두 대조군:

    truncation (주력)   `</think>` 직전 등 다지점에서 사고를 끊고 즉시 답변 강제 생성
    resampling (주력)   L2 판정 문장 직후에서 이후 궤적을 K회 재생성 (프리픽스 고정)
    filler     (대조군) 절단 구간을 같은 길이의 무의미 토큰으로 대체
    no-op      (대조군) `</think>` 자연 종료 지점에서 절단 — 사실상 무개입

해석 규칙 (사전등록 §4, 코드로 강제):
    인과 기여 = 절단 효과 − no-op 효과
    filler 대조로 형식 교란의 **상한**을 확인한 뒤에만 ΔAccuracy를 인과 기여로 읽는다.
    → analyze()가 no-op·filler 없이는 인과 해석을 산출하지 않고 거부한다.

resampling 지점(L2 문장) 국소화는 판정자 의존이므로 **인접 문장 다지점에서 함께
재생성**해 국소화 잡음을 완충한다 (§3.3.4).

usage:
    python -m experiments.exp3_causal.interventions run \
        --generations results/raw/qwen_standard_dragged.jsonl \
        --labels results/labels/qwen_standard_dragged.jsonl \
        --data data/processed/dragged.jsonl --model qwen \
        --mode truncation --out results/raw/qwen_dragged_trunc.jsonl
    python -m experiments.exp3_causal.interventions analyze --dir results/raw/
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from diagnosis.grading import grade
from diagnosis.metrics import MIN_COMPARABLE_N
from diagnosis.trace_parser import parse_record
from experiments.exp1_mitigation.envs import build_messages
from preprocessing.schema import read_jsonl, render_documents
from serving.client import DECODING, GenConfig, make_client

TRUNCATION_FRACTIONS = (0.25, 0.5, 0.75, 0.9, 1.0)  # 사고 길이 대비 절단 지점 (1.0 = no-op)
FILLER_TOKEN = "..."   # Lanham et al., 2023의 filler 대조 장치
RESAMPLE_K = 10
NEIGHBOR_OFFSETS = (-1, 0, 1)  # L2 문장 국소화 잡음 완충 (인접 문장 다지점)
SENT_RE = re.compile(r"(?<=[.!?])\s+")

# 개입 후 강제 답변 프리픽스 — 절단면에서 즉시 답을 내게 한다
FORCE_ANSWER = "\n</think>\n\nFinal answer:"


@dataclass
class InterventionSpec:
    mode: str          # truncation | filler | noop | resampling
    fraction: float | None = None   # truncation/filler 절단 지점
    k: int = RESAMPLE_K             # resampling 재생성 횟수


def truncate_thinking(thinking: str, fraction: float) -> str:
    """사고를 문자 길이 fraction 지점에서 문장 경계로 자른다."""
    if fraction >= 1.0:
        return thinking
    cut = int(len(thinking) * fraction)
    head = thinking[:cut]
    parts = SENT_RE.split(head)
    return " ".join(parts[:-1]) if len(parts) > 1 else head


def make_filler(thinking: str, fraction: float) -> str:
    """절단 구간을 같은 '길이'의 무의미 토큰으로 대체 (형식 교란 상한 측정용)."""
    kept = truncate_thinking(thinking, fraction)
    removed_chars = len(thinking) - len(kept)
    n_filler = max(1, removed_chars // (len(FILLER_TOKEN) + 1))
    return kept + " " + " ".join([FILLER_TOKEN] * n_filler)


def split_sentences(thinking: str) -> list[str]:
    return [s for s in SENT_RE.split(thinking) if s.strip()]


def resample_prefixes(thinking: str, l2_char_offset: int | None) -> list[str]:
    """L2 판정 문장 직후 + 인접 문장 다지점의 프리픽스 목록."""
    sents = split_sentences(thinking)
    if not sents:
        return []
    if l2_char_offset is None:
        anchor = len(sents) - 1
    else:  # 문자 오프셋 → 문장 인덱스
        acc, anchor = 0, len(sents) - 1
        for i, s in enumerate(sents):
            acc += len(s) + 1
            if acc > l2_char_offset:
                anchor = i
                break
    idxs = sorted({min(max(anchor + o, 0), len(sents) - 1) for o in NEIGHBOR_OFFSETS})
    return [" ".join(sents[: i + 1]) for i in idxs]


def build_intervened_prompt(item, doc_order_seed: int, env: str,
                            thinking_prefix: str) -> list[dict]:
    """사고 프리픽스를 assistant 턴으로 되먹여 그 지점부터 이어 생성하게 한다."""
    docs_text, _ = render_documents(item, shuffle_seed=doc_order_seed)
    msgs = build_messages(env, item.question, docs_text)
    msgs.append({"role": "assistant", "content": f"<think>\n{thinking_prefix}"})
    return msgs


def run(spec: InterventionSpec, gens_path: Path, labels_path: Path,
        data_path: Path, model_key: str, out_path: Path,
        env: str = "standard") -> None:
    """개입 생성을 실행해 JSONL로 기록한다 (raw 생성물 — git 미포함)."""
    items = {it.question_id: it for it in read_jsonl(data_path)}
    labels = {}
    with open(labels_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                labels[(r["question_id"], r["seed"])] = r

    cfg = GenConfig(model_key=model_key, env=env)
    client, model_id = make_client(cfg)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(gens_path, encoding="utf-8") as gf, open(out_path, "a", encoding="utf-8") as out:
        for line in gf:
            if not line.strip():
                continue
            rec = json.loads(line)
            parsed = parse_record(rec)
            item = items.get(rec["question_id"])
            if not parsed.ok or not parsed.thinking or item is None:
                continue
            lab = labels.get((rec["question_id"], rec["seed"]), {})
            # 경로별 취약성 검증: 정답을 낸 각 경로 표본에 동일 개입 (§3.3.4)
            if lab.get("fa") != "correct":
                continue

            prefixes: list[tuple[str, dict]] = []
            if spec.mode == "resampling":
                for i, pref in enumerate(resample_prefixes(parsed.thinking,
                                                           lab.get("l2_char_offset"))):
                    prefixes += [(pref, {"resample_point": i, "k_index": k})
                                 for k in range(spec.k)]
            else:
                fracs = TRUNCATION_FRACTIONS if spec.fraction is None else (spec.fraction,)
                for frac in fracs:
                    if spec.mode == "noop":
                        pref = parsed.thinking
                    elif spec.mode == "filler":
                        pref = make_filler(parsed.thinking, frac)
                    else:
                        pref = truncate_thinking(parsed.thinking, frac)
                    prefixes.append((pref, {"fraction": frac}))

            for pref, meta in prefixes:
                msgs = build_intervened_prompt(item, rec["seed"], env,
                                               pref + FORCE_ANSWER)
                resp = client.chat.completions.create(
                    model=model_id, messages=msgs, seed=rec["seed"],
                    max_tokens=512, **DECODING)
                answer = resp.choices[0].message.content
                out.write(json.dumps({
                    "question_id": rec["question_id"], "seed": rec["seed"],
                    "model": model_key, "env": env, "mode": spec.mode,
                    "origin_path": lab.get("path"), **meta,
                    "answer": answer,
                    "fa": grade(answer, item.correct_answers),
                }, ensure_ascii=False) + "\n")
                out.flush()


# ── 분석: 인과 기여 = 절단 효과 − no-op 효과 (filler 상한 확인 후에만) ─────────

def _flip_rate(records: list[dict]) -> tuple[float | None, int]:
    """개입 후 정답이 뒤집힌 비율. 대상은 모두 개입 전 정답(FA=correct) 표본."""
    scored = [r for r in records if r["fa"] != "abstain"]
    if not scored:
        return None, 0
    return sum(1 for r in scored if r["fa"] != "correct") / len(scored), len(scored)


def analyze(records: list[dict]) -> dict:
    by_mode: dict[str, list[dict]] = {}
    for r in records:
        by_mode.setdefault(r["mode"], []).append(r)

    if "noop" not in by_mode:
        return {"refused": "no-op(자연 종료점) 대조군 없이는 ΔAccuracy를 인과 기여로 "
                           "해석할 수 없다 (사전등록 §4). --mode noop 먼저 실행."}
    if "filler" not in by_mode:
        return {"refused": "filler 대조군 없이는 형식 교란 상한을 확인할 수 없어 "
                           "인과 해석이 금지된다 (사전등록 §4). --mode filler 먼저 실행."}

    noop_flip, _ = _flip_rate(by_mode["noop"])
    filler_flip, _ = _flip_rate(by_mode["filler"])
    report: dict = {
        "noop_flip_rate": noop_flip,
        "filler_flip_rate": filler_flip,
        "format_perturbation_ceiling": (filler_flip - noop_flip)
        if (filler_flip is not None and noop_flip is not None) else None,
    }

    for mode in ("truncation", "resampling"):
        if mode not in by_mode:
            continue
        flip, n = _flip_rate(by_mode[mode])
        causal = flip - noop_flip if (flip is not None and noop_flip is not None) else None
        entry = {"flip_rate": flip, "n": n, "causal_contribution": causal,
                 "comparable": n >= MIN_COMPARABLE_N}
        if causal is not None and report["format_perturbation_ceiling"] is not None:
            entry["exceeds_format_ceiling"] = causal > report["format_perturbation_ceiling"]
            entry["interpretation"] = (
                "사고 내용 제거의 인과 기여 (형식 교란 상한 초과)"
                if entry["exceeds_format_ceiling"] else
                "형식 교란 상한 이내 — 내용 제거의 인과 기여로 해석하지 않는다")
        # 경로별 취약성: 취약 경로 정답이 정상 경로보다 잘 깨지는가 (§3.3.4)
        entry["by_origin_path"] = {}
        for path in ("legitimate", "shortcut", "discordant_hit", "blind_hit"):
            sub = [r for r in by_mode[mode] if r.get("origin_path") == path]
            f, n_p = _flip_rate(sub)
            entry["by_origin_path"][path] = {
                "flip_rate": f, "n": n_p, "comparable": n_p >= MIN_COMPARABLE_N}
        report[mode] = entry

    # truncation은 절단 지점별 곡선도 보고 (어느 지점부터 답이 고정되는가)
    if "truncation" in by_mode:
        curve = {}
        for r in by_mode["truncation"]:
            curve.setdefault(r.get("fraction"), []).append(r)
        report["truncation"]["by_fraction"] = {
            str(frac): dict(zip(("flip_rate", "n"), _flip_rate(rs)))
            for frac, rs in sorted(curve.items(), key=lambda kv: kv[0] or 0)}
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run")
    r.add_argument("--generations", required=True, type=Path)
    r.add_argument("--labels", required=True, type=Path)
    r.add_argument("--data", required=True, type=Path)
    r.add_argument("--model", required=True)
    r.add_argument("--env", default="standard")
    r.add_argument("--mode", required=True,
                   choices=["truncation", "filler", "noop", "resampling"])
    r.add_argument("--fraction", type=float)
    r.add_argument("--k", type=int, default=RESAMPLE_K)
    r.add_argument("--out", required=True, type=Path)

    a = sub.add_parser("analyze")
    a.add_argument("--files", nargs="+", required=True, type=Path)
    a.add_argument("--out", type=Path)

    args = ap.parse_args()
    if args.cmd == "run":
        spec = InterventionSpec(args.mode, args.fraction, args.k)
        run(spec, args.generations, args.labels, args.data, args.model,
            args.out, args.env)
    else:
        records = []
        for p in args.files:
            with open(p, encoding="utf-8") as f:
                records += [json.loads(l) for l in f if l.strip()]
        report = analyze(records)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
