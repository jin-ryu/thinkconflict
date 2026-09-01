"""Judge Stage G final answers unit-by-unit with an OpenAI-compatible model."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any

from openai import OpenAI


ERROR_TYPES = (
    "wrong_temporal_state",
    "wrong_fact_or_source",
    "wrong_condition",
    "omission",
    "cross_unit_contamination",
    "unsupported_extra",
    "other",
)

SYSTEM_V3 = """You are a strict semantic evaluator of personalized-memory answers.
Judge only the candidate final answer against every reference unit. Paraphrases are valid.
An explanatory statement that entails a short gold answer such as Yes or No is valid
when it agrees with the supplied gold evidence records.
Do not penalize missing explanations or memory IDs when the requested conclusion is correct.
For each unit, decide whether the candidate gives the correct query-grounded conclusion.
Then set all_unit_success=true iff every unit is correct and there is no harmful unsupported claim.
Return JSON only with this schema:
{"unit_results":[{"unit_id":"...","correct":true,"reason":"brief"}],"all_unit_success":true,"error_types":[]}
Use each reference unit_id exactly once and in the supplied order. error_types may contain only:
wrong_temporal_state, wrong_fact_or_source, wrong_condition, omission, cross_unit_contamination, unsupported_extra, other."""

SYSTEM_V4 = """You are a strict semantic evaluator of personalized-memory answers.
The candidate is ONE final answer that responds to several independent questions at once. Judge EACH reference unit in isolation:
- Locate the part of the candidate answer that responds to that unit's atomic_question and copy it into extracted_answer ("" if the unit is not addressed at all).
- Set correct=true iff extracted_answer gives the same query-grounded conclusion as gold_reference_answer, as supported by gold_evidence_records. Paraphrases are valid. A statement that entails a short gold answer such as Yes or No is valid.
- Content about OTHER units must never affect this unit's verdict, even if that other content is wrong.
- Do not penalize missing explanations, missing memory IDs, or dates quoted in the answer that differ from target_date, as long as the stated state or value is the one valid at target_date.
- required_behavior SUPERSEDE: the candidate must give the state valid at target_date; mentioning the earlier state as history is fine; giving only the earlier state is wrong.
- required_behavior VERIFY_PREFER: the candidate must give the verified value; noting the disagreement is optional; giving the conflicting value as the answer is wrong.
- required_behavior CONDITION: the candidate must give the condition or value that matches the queried item; listing several without the matching one is wrong.
- required_behavior LOOKUP: the candidate must state the recorded value.
Then set all_unit_success=true iff every unit is correct.
Return JSON only with this schema:
{"unit_results":[{"unit_id":"...","extracted_answer":"...","correct":true,"reason":"brief"}],"all_unit_success":true,"error_types":[]}
Use each reference unit_id exactly once and in the supplied order. error_types may contain only:
wrong_temporal_state, wrong_fact_or_source, wrong_condition, omission, cross_unit_contamination, unsupported_extra, other."""

SYSTEM_V4_LOOKUP_LENIENT = """You are a strict semantic evaluator of personalized-memory answers.
The candidate is ONE final answer that responds to several independent questions at once. Judge EACH reference unit in isolation:
- Locate the part of the candidate answer that responds to that unit's atomic_question and copy it into extracted_answer ("" if the unit is not addressed at all).
- Set correct=true iff extracted_answer gives the same query-grounded conclusion as gold_reference_answer, as supported by gold_evidence_records. Paraphrases are valid. A statement that entails a short gold answer such as Yes or No is valid.
- Content about OTHER units must never affect this unit's verdict, even if that other content is wrong.
- Do not penalize missing explanations, missing memory IDs, or dates quoted in the answer that differ from target_date, as long as the stated state or value is the one valid at target_date.
- required_behavior SUPERSEDE: the candidate must give the state valid at target_date; mentioning the earlier state as history is fine; giving only the earlier state is wrong.
- required_behavior VERIFY_PREFER: the candidate must give the verified value; noting the disagreement is optional; giving the conflicting value as the answer is wrong.
- required_behavior CONDITION: the candidate must give the condition or value that matches the queried item; listing several without the matching one is wrong.
- required_behavior LOOKUP: the candidate must state the main recorded value for the asked attribute (for a multi-field record: the fields named in the atomic_question, e.g. employer and title for a career question; a city for residence; the status for marital/children/work state; both physical and mental state for health). Omitting a secondary field, paraphrasing, or adding extra fields from the same user record is still correct. It is wrong if a stated field contradicts the record, if the value belongs to another person (neighbor, friend, family) rather than the user, or if the candidate refuses to state the value.
Then set all_unit_success=true iff every unit is correct.
Return JSON only with this schema:
{"unit_results":[{"unit_id":"...","extracted_answer":"...","correct":true,"reason":"brief"}],"all_unit_success":true,"error_types":[]}
Use each reference unit_id exactly once and in the supplied order. error_types may contain only:
wrong_temporal_state, wrong_fact_or_source, wrong_condition, omission, cross_unit_contamination, unsupported_extra, other."""


PROTOCOLS = {"v3_evidence": SYSTEM_V3, "v4_unit_isolated": SYSTEM_V4, "v4_lookup_lenient": SYSTEM_V4_LOOKUP_LENIENT}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def parse_json(text: str) -> dict[str, Any]:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def reference_payload(instance: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    records = {record["memory_id"]: record for record in instance["memory_context"]}
    units = []
    for unit in instance["gold_units"]:
        units.append({
            "unit_id": unit["unit_id"],
            "atomic_question": unit.get("question") or unit.get("atomic_question"),
            "target_date": unit.get("unit_target_date") or unit.get("target_date") or instance.get("target_date"),
            "required_behavior": unit["policy"],
            "gold_reference_answer": (
                unit.get("gold_atomic_answer")
                or unit.get("gold_answer")
                or unit.get("answer")
            ),
            "gold_evidence_records": [
                records[evidence_id]
                for evidence_id in unit.get("evidence_ids", [])
                if evidence_id in records
            ],
        })
    response = output.get("response", {})
    final_answer = response.get("final_answer", "") if isinstance(response, dict) else ""
    return {
        "compound_query": instance["query"],
        "reference_units": units,
        "candidate_final_answer": final_answer,
    }


def validate(parsed: dict[str, Any], expected_ids: list[str]) -> None:
    results = parsed.get("unit_results")
    if not isinstance(results, list) or len(results) != len(expected_ids):
        raise ValueError("unit_results count mismatch")
    actual_ids = [row.get("unit_id") for row in results]
    if actual_ids != expected_ids:
        raise ValueError(f"unit_ids mismatch: expected {expected_ids}, got {actual_ids}")
    if any(not isinstance(row.get("correct"), bool) for row in results):
        raise ValueError("every unit result must contain boolean correct")
    if not isinstance(parsed.get("all_unit_success"), bool):
        raise ValueError("all_unit_success must be boolean")
    errors = parsed.get("error_types")
    if not isinstance(errors, list) or any(error not in ERROR_TYPES for error in errors):
        raise ValueError("invalid error_types")
    unit_all = all(row["correct"] for row in results)
    if parsed["all_unit_success"] and not unit_all:
        raise ValueError("all_unit_success contradicts unit results")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances", nargs="+", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8004/v1")
    parser.add_argument("--judge-model", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--disable-thinking", action="store_true")
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high"))
    parser.add_argument("--protocol", choices=tuple(PROTOCOLS), default="v3_evidence")
    args = parser.parse_args()
    system_prompt = PROTOCOLS[args.protocol]

    instances = {
        row["instance_id"]: row
        for path in args.instances
        for row in load_jsonl(path)
    }
    # Generation/parsing failures remain in the denominator. Their absent
    # final_answer is judged as an omission instead of silently dropped.
    outputs = load_jsonl(args.outputs)
    missing = sorted({row["instance_id"] for row in outputs} - set(instances))
    if missing:
        raise ValueError(f"missing instances for {len(missing)} outputs")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict[str, Any]] = {}
    if args.output.exists():
        for row in load_jsonl(args.output):
            if "error" not in row:
                existing[row["run_id"]] = row

    client = OpenAI(base_url=args.base_url, api_key="EMPTY")
    lock = Lock()

    def judge(output: dict[str, Any]) -> dict[str, Any]:
        raw = ""
        run_id = output["run_id"]
        instance = instances[output["instance_id"]]
        refs = reference_payload(instance, output)
        expected_ids = [unit["unit_id"] for unit in refs["reference_units"]]
        try:
            extra_body: dict[str, Any] = {}
            if args.disable_thinking:
                extra_body["chat_template_kwargs"] = {"enable_thinking": False}
            if args.reasoning_effort:
                extra_body["reasoning_effort"] = args.reasoning_effort
            attempts = [
                (system_prompt, args.seed),
                (
                    system_prompt
                    + f"\n\nYou MUST return exactly {len(expected_ids)} unit_results entries, one per reference unit, in the supplied order.",
                    args.seed + 1,
                ),
            ]
            last_error: Exception | None = None
            for attempt_system, attempt_seed in attempts:
                response = client.chat.completions.create(
                    model=args.judge_model,
                    messages=[
                        {"role": "system", "content": attempt_system},
                        {"role": "user", "content": json.dumps(refs, ensure_ascii=False)},
                    ],
                    temperature=0,
                    max_tokens=args.max_tokens,
                    seed=attempt_seed,
                    extra_body=extra_body or None,
                )
                raw = response.choices[0].message.content or ""
                try:
                    parsed = parse_json(raw)
                    if isinstance(parsed.get("error_types"), list):
                        parsed["error_types"] = [str(error).lower() for error in parsed["error_types"]]
                    results = parsed.get("unit_results")
                    if isinstance(results, list) and len(results) == len(expected_ids):
                        # Copy errors in opaque IDs do not affect the semantic decision;
                        # the prompt requires results in reference order.
                        for result, expected_id in zip(results, expected_ids, strict=True):
                            result["unit_id"] = expected_id
                            if args.protocol in ("v4_unit_isolated", "v4_lookup_lenient"):
                                result["extracted_answer"] = str(result.get("extracted_answer") or "")
                    validate(parsed, expected_ids)
                    last_error = None
                    break
                except (ValueError, json.JSONDecodeError) as exc:
                    last_error = exc
            if last_error is not None and len(expected_ids) > 1:
                # Final fallback: judge each reference unit in its own call and merge.
                merged = {"unit_results": [], "all_unit_success": True, "error_types": []}
                raw_parts = []
                for unit_ref in refs["reference_units"]:
                    single = dict(refs, reference_units=[unit_ref])
                    response = client.chat.completions.create(
                        model=args.judge_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": json.dumps(single, ensure_ascii=False)},
                        ],
                        temperature=0,
                        max_tokens=args.max_tokens,
                        seed=args.seed,
                        extra_body=extra_body or None,
                    )
                    part_raw = response.choices[0].message.content or ""
                    raw_parts.append(part_raw)
                    part = parse_json(part_raw)
                    result = (part.get("unit_results") or [{}])[0]
                    result["unit_id"] = unit_ref["unit_id"]
                    if args.protocol in ("v4_unit_isolated", "v4_lookup_lenient"):
                        result["extracted_answer"] = str(result.get("extracted_answer") or "")
                    merged["unit_results"].append(result)
                    merged["all_unit_success"] = merged["all_unit_success"] and bool(result.get("correct"))
                    merged["error_types"].extend(
                        str(e).lower() for e in (part.get("error_types") or []) if str(e).lower() in ERROR_TYPES
                    )
                merged["error_types"] = sorted(set(merged["error_types"]))
                validate(merged, expected_ids)
                parsed = merged
                raw = "\n".join(raw_parts)
                last_error = None
            if last_error is not None:
                raise last_error
            return {
                "run_id": run_id,
                "instance_id": output["instance_id"],
                "baseline_condition": output["baseline_condition"],
                "generation_model": output["model"],
                "generation_error": output.get("error"),
                "judge_model": args.judge_model,
                "protocol": args.protocol,
                "judged_per_unit_fallback": "\n" in raw and len(expected_ids) > 1 and raw.count("unit_results") >= len(expected_ids),
                "judgment": parsed,
                "raw_judgment": raw,
                "usage": response.usage.model_dump() if response.usage else None,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "run_id": run_id,
                "instance_id": output["instance_id"],
                "generation_model": output["model"],
                "judge_model": args.judge_model,
                "error": str(exc),
                "raw_judgment": raw,
            }

    todo = [row for row in outputs if row["run_id"] not in existing]
    with args.output.open("a") as handle:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(judge, row): row for row in todo}
            for future in as_completed(futures):
                row = future.result()
                with lock:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    handle.flush()

    latest = {row["run_id"]: row for row in load_jsonl(args.output)}
    canonical = [latest[run_id] for run_id in sorted(latest)]
    with args.output.open("w") as handle:
        for row in canonical:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    expected = {row["run_id"] for row in outputs}
    final = [row for row in canonical if row["run_id"] in expected]
    print(json.dumps({
        "expected": len(expected),
        "completed": len(final),
        "errors": sum("error" in row for row in final),
    }, indent=2))


if __name__ == "__main__":
    main()
