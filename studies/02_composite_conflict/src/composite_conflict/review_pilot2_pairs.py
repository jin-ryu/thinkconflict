"""LLM first-pass review of Pilot 2 same-session pair candidates."""
from __future__ import annotations

import argparse
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any

from openai import OpenAI


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def policy_key(row: dict[str, Any]) -> str:
    return "+".join(sorted(set(row["policies"])))


def sample_candidates(rows: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = policy_key(row)
        groups.setdefault(key, []).append(row)

    # H=1은 independent unit을 얻기 쉬운 CONDITION+CONDITION을 우선한다.
    quotas = {
        "CONDITION": 100,
        "SUPERSEDE": 80,
        "CONDITION+SUPERSEDE": 120,
        "CONDITION+VERIFY_PREFER": 100,
        "SUPERSEDE+VERIFY_PREFER": 18,
    }
    selected: list[dict[str, Any]] = []
    for key, quota in quotas.items():
        group = sorted(groups.get(key, []), key=lambda r: r["pair_id"])
        rng.shuffle(group)
        selected.extend(group[:quota])
    return sorted(selected, key=lambda r: r["pair_id"])


def prompt_for(row: dict[str, Any]) -> list[dict[str, str]]:
    system = """You are screening candidate items for a rigorous NLP pilot about compositional long-term-memory conflicts.
A valid candidate must satisfy all of the following:
1. The two questions target two independent memory conflict units, not two phrasings/subquestions of one update.
2. A realistic user could require both resolved values in one coherent assistant goal or decision.
3. Combining them must not change either original gold answer or required policy.
4. The combined query must not reveal the gold answers or name the policy labels.
Be conservative. Same persona/session alone does not imply natural composition. Do not approve a pair merely because a grammatical sentence can join it with 'and'.
Return JSON only with keys: independent_units (bool), one_coherent_goal (bool), gold_preserved (bool), naturalness_score (integer 1-5), combined_query (string or null), proposed_goal (string or null), rejection_reason (string or null), rationale (short string)."""
    user = json.dumps(
        {
            "persona_name": row["persona_name"],
            "date": row["date"],
            "event_types": row["event_types"],
            "session_outline": row["session_outline"],
            "question_1": row["questions"][0],
            "gold_answer_1": row["answers"][0],
            "policy_1": row["policies"][0],
            "question_2": row["questions"][1],
            "gold_answer_2": row["answers"][1],
            "policy_2": row["policies"][1],
        },
        ensure_ascii=False,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--base-url", default="http://localhost:8004/v1")
    ap.add_argument(
        "--model", default="mistralai/Mistral-Small-3.2-24B-Instruct-2506"
    )
    ap.add_argument("--seed", type=int, default=20260826)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    rows = sample_candidates(read_jsonl(args.input), args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    done: dict[str, dict[str, Any]] = {}
    if args.output.exists():
        for row in read_jsonl(args.output):
            done[row["pair_id"]] = row

    client = OpenAI(base_url=args.base_url, api_key="EMPTY")
    lock = Lock()

    def review(row: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = client.chat.completions.create(
                model=args.model,
                messages=prompt_for(row),
                temperature=0,
                max_tokens=900,
                seed=args.seed,
            )
            text = resp.choices[0].message.content or ""
            verdict = parse_json(text)
            valid = (
                verdict.get("independent_units") is True
                and verdict.get("one_coherent_goal") is True
                and verdict.get("gold_preserved") is True
                and int(verdict.get("naturalness_score", 0)) >= 4
                and bool(verdict.get("combined_query"))
            )
            return {
                **row,
                "review_model": args.model,
                "review_seed": args.seed,
                "review": verdict,
                "llm_first_pass_valid": valid,
                "usage": resp.usage.model_dump() if resp.usage else None,
                "raw_response": text,
            }
        except Exception as exc:  # noqa: BLE001
            return {**row, "review_model": args.model, "error": str(exc)}

    todo = [row for row in rows if row["pair_id"] not in done]
    with args.output.open("a", encoding="utf-8") as out:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(review, row): row["pair_id"] for row in todo}
            for future in as_completed(futures):
                result = future.result()
                with lock:
                    out.write(json.dumps(result, ensure_ascii=False) + "\n")
                    out.flush()

    final = list(done.values()) + [r for r in read_jsonl(args.output) if r["pair_id"] not in done]
    errors = sum("error" in r for r in final)
    valid = sum(r.get("llm_first_pass_valid") is True for r in final)
    print(json.dumps({"reviewed": len(final), "valid": valid, "errors": errors}))


if __name__ == "__main__":
    main()
