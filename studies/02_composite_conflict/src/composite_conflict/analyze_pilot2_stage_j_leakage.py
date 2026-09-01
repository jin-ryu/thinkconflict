"""Stage J-4: policy-leakage attribution for wrong unit answers.

For every gold unit we enumerate the alternative values present in its own
memory records and label each with the resolution policy that would have
selected it:

  SUPERSEDE unit      prior value            -> stale_kept       (verify/keep-old behaviour)
  VERIFY_PREFER unit  later false value      -> latest_applied   (supersede behaviour)
                      other-person value     -> wrong_owner
  CONDITION unit      other condition/item   -> wrong_condition
                      other-person pref      -> wrong_owner

A wrong unit answer (per the evidence-aware judge) is attributed to the label
whose distinctive value strings appear in the final answer while the gold
value does not. Answers matching nothing are `unattributed`; answers that
contain the gold value but were still judged wrong are `gold_present_but_wrong`
(typically over-preservation or a contradictory composition).
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from composite_conflict.analyze_pilot2_stage_j_independence import read_jsonl, unit_judgments

STOP = {"the", "and", "or", "of", "a", "an", "to", "in", "on", "at", "for", "with", "user", "yes", "no", "none", "normal", "status", "employed", "single", "married"}


def leaves(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [s for v in value.values() for s in leaves(v)]
    if isinstance(value, list):
        return [s for v in value for s in leaves(v)]
    s = str(value).strip()
    return [s] if s else []


def distinctive(value: Any, gold_text: str) -> list[str]:
    """Leaf strings of an alternative value that do not occur in the gold answer."""
    out = []
    for leaf in leaves(value):
        low = leaf.lower()
        if len(low) < 3 or low in STOP or low in gold_text.lower():
            continue
        out.append(leaf)
    return out


def gold_value(unit: dict[str, Any], records: dict[str, dict[str, Any]]) -> Any:
    """The record value a correct resolution would surface (not the gold answer text)."""
    policy = unit["policy"]
    evidence = [records[i] for i in unit.get("evidence_ids", []) if i in records]
    if policy == "SUPERSEDE":
        for rec in evidence:
            if rec["memory_id"].endswith(":update"):
                return rec["claim"].get("value")
    if policy == "VERIFY_PREFER":
        for rec in evidence:
            if rec.get("source") == "verified_profile_record":
                return rec["claim"].get("value")
    if policy == "LOOKUP":
        for rec in evidence:
            return rec["claim"].get("value")
    if policy == "CONDITION":
        # the gold answer text is the condition itself; take the matching user record
        gold_text = str(unit.get("gold_atomic_answer", "")).lower()
        best = None
        for rec in records.values():
            if unit["target_attribute"] in rec["memory_id"] and rec.get("source") != "other_person_statement":
                cond = str(rec["claim"].get("condition", ""))
                overlap = len(set(cond.lower().split()) & set(gold_text.split()))
                if best is None or overlap > best[0]:
                    best = (overlap, cond)
        return best[1] if best else None
    return None


def alternatives(unit: dict[str, Any], records: dict[str, dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    policy = unit["policy"]
    gold = gold_value(unit, records)
    gold_strings = [s for s in leaves(gold) if len(s) >= 3 and s.lower() not in STOP]
    gold_text = " ".join(gold_strings)
    alts: list[dict[str, Any]] = []
    if policy == "SUPERSEDE":
        for i in unit.get("evidence_ids", []):
            rec = records.get(i)
            if rec and rec["memory_id"].endswith(":prior"):
                alts.append({"label": "stale_kept", "memory_id": i, "strings": distinctive(rec["claim"].get("value"), gold_text)})
    elif policy == "VERIFY_PREFER":
        group = unit["target_attribute"]
        for rec in records.values():
            if rec.get("source") == "unverified_conflicting_statement" and rec["memory_id"] in unit.get("evidence_ids", []):
                alts.append({"label": "latest_applied", "memory_id": rec["memory_id"], "strings": distinctive(rec["claim"].get("value"), gold_text)})
            elif rec.get("source") == "other_person_statement" and rec["claim"].get("attribute") == group:
                alts.append({"label": "wrong_owner", "memory_id": rec["memory_id"], "strings": distinctive(rec["claim"].get("value"), gold_text)})
    elif policy == "LOOKUP":
        for rec in records.values():
            if rec.get("source") == "other_person_statement" and rec["claim"].get("attribute") == unit["target_attribute"]:
                alts.append({"label": "wrong_owner", "memory_id": rec["memory_id"], "strings": distinctive(rec["claim"].get("value"), gold_text)})
    elif policy == "CONDITION":
        conflict_id = unit["target_attribute"]
        for rec in records.values():
            if conflict_id not in rec["memory_id"]:
                continue
            claim = rec["claim"]
            label = "wrong_owner" if rec.get("source") == "other_person_statement" else "wrong_condition"
            strings = distinctive(claim.get("condition"), gold_text)
            if label == "wrong_condition":
                strings = [x for x in strings if x.lower() != str(gold).lower()]
            if strings:
                alts.append({"label": label, "memory_id": rec["memory_id"], "strings": strings})
    return gold_strings, [a for a in alts if a["strings"]]


def final_answer(row: dict[str, Any]) -> str:
    resp = row.get("response")
    if isinstance(resp, str):
        try:
            resp = ast.literal_eval(resp)
        except Exception:
            try:
                resp = json.loads(resp)
            except Exception:
                return str(row.get("raw_response") or resp)
    if isinstance(resp, dict):
        return str(resp.get("final_answer") or "") + " " + " ".join(str(u.get("resolution", "")) for u in resp.get("resolved_units", []) if isinstance(u, dict))
    return str(row.get("raw_response") or "")


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9][a-z0-9\-']+", text.lower()) if len(t) >= 4 and t not in STOP}


def matches(answer: str, strings: list[str], gold_tokens: set[str]) -> bool:
    """A value matches if it is contained verbatim, or if >=2 of its distinctive tokens appear."""
    low = answer.lower()
    ans_tokens = _tokens(answer)
    for s in strings:
        if s.lower() in low:
            return True
        distinct = _tokens(s) - gold_tokens
        if len(distinct) >= 2 and len(distinct & ans_tokens) >= 2:
            return True
        if len(distinct) == 1 and distinct <= ans_tokens:
            return True
    return False


def attribute(answer: str, gold_strings: list[str], alts: list[dict[str, Any]]) -> str:
    gold_tokens = _tokens(" ".join(gold_strings))
    gold_hit = matches(answer, gold_strings, set())
    hits = sorted({a["label"] for a in alts if matches(answer, a["strings"], gold_tokens)})
    if hits and not gold_hit:
        return "+".join(hits)
    if hits and gold_hit:
        return "gold_and_alt"
    if gold_hit:
        return "gold_present_but_wrong"
    return "unattributed"


def extracted_answers(judgments: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    """(instance_id, unit_id) -> judge-extracted answer span (v4 protocol only)."""
    out = {}
    for row in judgments:
        for item in (row.get("judgment") or {}).get("unit_results", []):
            text = str(item.get("extracted_answer") or "").strip()
            if text:
                out[(row["instance_id"], item["unit_id"])] = text
    return out


def analyse(composites: list[dict[str, Any]], outputs: list[dict[str, Any]], judgments: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts = unit_judgments(judgments)
    spans = extracted_answers(judgments)
    out_by_id = {row["instance_id"]: row for row in outputs}
    matrix: dict[str, Counter] = defaultdict(Counter)   # key -> label counts
    totals: dict[str, int] = Counter()
    for row in composites:
        cell = row.get("cell") or f"K{row['K']}_H{row['H']}"
        het = row["condition"]
        records = {r["memory_id"]: r for r in row["memory_context"]}
        v = verdicts.get(row["instance_id"], {})
        gen = out_by_id.get(row["instance_id"])
        if gen is None:
            continue
        answer = final_answer(gen)
        for unit in row["gold_units"]:
            if v.get(unit["unit_id"], False):
                continue
            gold_strings, alts = alternatives(unit, records)
            span = spans.get((row["instance_id"], unit["unit_id"]))
            label = attribute(span if span else answer, gold_strings, alts)
            if span is None and spans:
                label = "not_addressed" if label == "unattributed" else label
            for key in (f"{unit['policy']}|ALL", f"{unit['policy']}|{het}", f"ALL|{het}", f"{unit['policy']}|{cell}"):
                matrix[key][label] += 1
                totals[key] += 1
    report = {}
    for key, counts in sorted(matrix.items()):
        n = totals[key]
        report[key] = {"wrong_unit_trials": n, "labels": {k: {"n": c, "share": round(c / n, 3)} for k, c in counts.most_common()}}
    return report


def markdown(report: dict[str, Any], label: str) -> str:
    lines = [f"### {label}", "", "| unit policy | subset | wrong trials | stale_kept | latest_applied | wrong_owner | wrong_condition | gold_and_alt | gold_present_but_wrong | not_addressed | unattributed |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for key in sorted(report):
        policy, subset = key.split("|")
        if subset not in ("ALL", "homogeneous", "heterogeneous", "no_conflict"):
            continue
        r = report[key]
        def share(lbl: str) -> str:
            tot = sum(v["n"] for k, v in r["labels"].items() if lbl in k.split("+"))
            return f"{tot / r['wrong_unit_trials']:.2f}" if r["wrong_unit_trials"] else "-"
        lines.append(f"| {policy} | {subset} | {r['wrong_unit_trials']} | {share('stale_kept')} | {share('latest_applied')} | {share('wrong_owner')} | {share('wrong_condition')} | {share('gold_and_alt')} | {share('gold_present_but_wrong')} | {share('not_addressed')} | {share('unattributed')} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--composites", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    report = analyse(read_jsonl(args.composites), read_jsonl(args.outputs), read_jsonl(args.judgments))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    slug = args.label.replace("/", "_")
    (args.out_dir / f"{slug}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = markdown(report, args.label)
    (args.out_dir / f"{slug}.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
