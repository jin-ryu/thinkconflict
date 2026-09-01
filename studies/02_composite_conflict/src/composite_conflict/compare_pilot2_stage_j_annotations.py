"""Compare independent annotations (blind) with the machine judge verdicts in the human sample.

Reports unit-level agreement and Cohen's kappa overall, per generation label, per cell
and per policy, lists every disagreement for adjudication, and recomputes the
accuracy of each stratum under the annotator's verdicts.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    agree = sum(a == b for a, b in pairs) / n
    pa = sum(a for a, _ in pairs) / n
    pb = sum(b for _, b in pairs) / n
    exp = pa * pb + (1 - pa) * (1 - pb)
    return round((agree - exp) / (1 - exp), 3) if exp < 1 else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, required=True, help="human_sample_with_machine.jsonl")
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--annotator", default="annotator")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    sample = {json.loads(l)["sample_id"]: json.loads(l) for l in args.sample.open(encoding="utf-8")}
    ann = {json.loads(l)["sample_id"]: json.loads(l) for l in args.annotations.open(encoding="utf-8")}
    groups = defaultdict(list)
    disagreements = []
    labels_by_policy = defaultdict(Counter)
    for sid, row in sample.items():
        a = ann.get(sid)
        if not a:
            continue
        machine = {u["unit_id"]: bool(u.get("correct")) for u in row["_machine"]["unit_results"]}
        for unit, au in zip(row["units"], a["units"]):
            m = machine.get(unit["unit_id"], False)
            h = bool(au["correct"])
            pair = (m, h)
            for key in ("ALL", f"gen:{row['generation_label']}", f"cell:{row['cell']}", f"policy:{unit['policy']}"):
                groups[key].append(pair)
            if not h:
                labels_by_policy[unit["policy"]][au["label"]] += 1
            if m != h:
                disagreements.append({
                    "sample_id": sid, "generation_label": row["generation_label"], "cell": row["cell"], "instance_id": row["instance_id"],
                    "unit_id": unit["unit_id"], "policy": unit["policy"], "atomic_question": unit["atomic_question"], "gold": unit["gold_atomic_answer"],
                    "machine_correct": m, "annotator_correct": h, "annotator_label": au["label"], "annotator_note": au.get("note", ""),
                    "machine_reason": next((u.get("reason") for u in row["_machine"]["unit_results"] if u["unit_id"] == unit["unit_id"]), None),
                    "candidate_final_answer": row["candidate_final_answer"],
                })
    report = {"annotator": args.annotator, "groups": {}, "annotator_labels_by_policy": {p: dict(c) for p, c in labels_by_policy.items()}, "disagreements": len(disagreements)}
    lines = [f"### Machine (v4 judge) vs {args.annotator}", "", "| group | n units | agreement | kappa | machine acc | annotator acc | machine ok / annot wrong | machine wrong / annot ok |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for key in sorted(groups, key=lambda k: (k != "ALL", k)):
        pairs = groups[key]
        n = len(pairs)
        rep = {"n": n, "agreement": round(sum(a == b for a, b in pairs) / n, 3), "kappa": kappa(pairs), "machine_acc": round(sum(a for a, _ in pairs) / n, 3), "annotator_acc": round(sum(b for _, b in pairs) / n, 3), "machine_ok_annot_wrong": sum(1 for a, b in pairs if a and not b), "machine_wrong_annot_ok": sum(1 for a, b in pairs if b and not a)}
        report["groups"][key] = rep
        lines.append(f"| {key} | {n} | {rep['agreement']:.3f} | {rep['kappa']} | {rep['machine_acc']:.3f} | {rep['annotator_acc']:.3f} | {rep['machine_ok_annot_wrong']} | {rep['machine_wrong_annot_ok']} |")
    lines += ["", "Annotator error labels by policy: " + json.dumps(report["annotator_labels_by_policy"], ensure_ascii=False)]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (args.out_dir / "disagreements.jsonl").open("w", encoding="utf-8") as f:
        for d in disagreements:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
