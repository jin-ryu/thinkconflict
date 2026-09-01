"""MemConflict audit and same-session pair-pool construction for Pilot 2."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

POLICY = {
    "dynamic_conflict": "SUPERSEDE",
    "static_conflict": "VERIFY_PREFER",
    "conditional_conflict": "CONDITION",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def question_uid(persona_id: str, session_id: int, question_id: str) -> str:
    return f"{persona_id}:S{session_id}:{question_id}"


def normalize_questions(people: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for person in people:
        persona_id = person["ID"]
        for session in person["Full_Session_Chain"]:
            for q in session["Session_Questions"]:
                conflict_type = q["conflict_type"]
                rows.append(
                    {
                        "question_uid": question_uid(
                            persona_id, session["Session_ID"], q["question_id"]
                        ),
                        "persona_id": persona_id,
                        "persona_name": person["Fixed_Profile"].get("Name"),
                        "persona_seed": person.get("metadata", {}).get("persona_seed"),
                        "life_goal": person.get("Life_Goal"),
                        "session_id": session["Session_ID"],
                        "date": session["Date"],
                        "session_type": session["Session_Type"],
                        "event_types": session["Event_Types"],
                        "session_outline": session["Session_Outline"],
                        "question_id": q["question_id"],
                        "question": q["question"],
                        "answer": q["answer"],
                        "conflict_type": conflict_type,
                        "policy": POLICY[conflict_type],
                        "ability_target": q["ability_target"],
                        "difficulty": q["difficulty"],
                        "question_trigger_types": session["Question_Trigger_Types"],
                        "updated_attributes": session.get("Updated_Attributes", []),
                        "static_conflict_information": session[
                            "Static_Conflict_Information"
                        ],
                        "conditional_conflict_information": session[
                            "Conditional_Conflict_Information"
                        ],
                    }
                )
    return rows


def build_pair_pool(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_session: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for q in questions:
        by_session.setdefault((q["persona_id"], q["session_id"]), []).append(q)

    pairs: list[dict[str, Any]] = []
    for (persona_id, session_id), qs in by_session.items():
        for left, right in combinations(qs, 2):
            policies = sorted({left["policy"], right["policy"]})
            h = len(policies)
            pair_id = (
                f"{persona_id}:S{session_id}:"
                f"{left['question_id']}+{right['question_id']}"
            )
            pairs.append(
                {
                    "pair_id": pair_id,
                    "persona_id": persona_id,
                    "persona_name": left["persona_name"],
                    "session_id": session_id,
                    "date": left["date"],
                    "event_types": left["event_types"],
                    "session_outline": left["session_outline"],
                    "question_uids": [left["question_uid"], right["question_uid"]],
                    "questions": [left["question"], right["question"]],
                    "answers": [left["answer"], right["answer"]],
                    "conflict_types": [
                        left["conflict_type"],
                        right["conflict_type"],
                    ],
                    "policies": [left["policy"], right["policy"]],
                    "K_candidate": 2,
                    "H": h,
                    "condition": "heterogeneous" if h == 2 else "homogeneous",
                    "same_session": True,
                    "needs_independence_review": True,
                    "needs_naturalness_review": True,
                }
            )
    return pairs


def persona_audit(people: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for person in people:
        q_counter: Counter[str] = Counter()
        multi_type_sessions = 0
        question_sessions = 0
        for session in person["Full_Session_Chain"]:
            types = {q["conflict_type"] for q in session["Session_Questions"]}
            q_counter.update(q["conflict_type"] for q in session["Session_Questions"])
            question_sessions += bool(types)
            multi_type_sessions += len(types) > 1
        rows.append(
            {
                "persona_id": person["ID"],
                "persona_name": person["Fixed_Profile"].get("Name"),
                "persona_seed": person.get("metadata", {}).get("persona_seed"),
                "session_count": len(person["Full_Session_Chain"]),
                "question_session_count": question_sessions,
                "question_count": sum(q_counter.values()),
                "question_count_by_type": dict(sorted(q_counter.items())),
                "distinct_question_types": len(q_counter),
                "multi_type_session_count": multi_type_sessions,
            }
        )
    return rows


def build_report(
    people: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    revision: str,
) -> str:
    qtypes = Counter(q["conflict_type"] for q in questions)
    policies = Counter(q["policy"] for q in questions)
    question_sessions: dict[tuple[str, int], set[str]] = {}
    for q in questions:
        question_sessions.setdefault((q["persona_id"], q["session_id"]), set()).add(
            q["conflict_type"]
        )
    combo_counts = Counter(tuple(sorted(v)) for v in question_sessions.values())
    pair_conditions = Counter(p["condition"] for p in pairs)
    pair_policy_sets = Counter(tuple(sorted(set(p["policies"]))) for p in pairs)
    all_three = sum(
        set(row["question_count_by_type"])
        == {"dynamic_conflict", "static_conflict", "conditional_conflict"}
        for row in persona_audit(people)
    )

    lines = [
        "# Pilot 2 MemConflict schema audit",
        "",
        "> 자동 집계 결과. 자연성·독립 conflict-unit 여부는 아직 판정하지 않은 pair pool이다.",
        "",
        "## Source",
        "",
        f"- revision: `{revision}`",
        "- file: `Data/Step4_4.jsonl`",
        f"- personas: {len(people)}",
        f"- sessions: {sum(len(p['Full_Session_Chain']) for p in people):,}",
        f"- questions: {len(questions):,}",
        "",
        "## Question distribution",
        "",
        "| Conflict type | Policy | Questions |",
        "|---|---|---:|",
    ]
    for t in sorted(qtypes):
        lines.append(f"| `{t}` | `{POLICY[t]}` | {qtypes[t]:,} |")
    lines += [
        "",
        f"- all three types를 가진 personas: {all_three}/{len(people)}",
        f"- question-bearing sessions: {len(question_sessions):,}",
        f"- multi-type sessions: {sum(len(v) > 1 for v in question_sessions.values()):,}",
        "",
        "## Session type combinations",
        "",
        "| Conflict types in one session | Sessions |",
        "|---|---:|",
    ]
    for combo, count in combo_counts.most_common():
        lines.append(f"| `{'+'.join(combo)}` | {count:,} |")
    lines += [
        "",
        "## Raw same-session pair pool",
        "",
        f"- total pairs: {len(pairs):,}",
        f"- homogeneous-policy pairs: {pair_conditions['homogeneous']:,}",
        f"- heterogeneous-policy pairs: {pair_conditions['heterogeneous']:,}",
        "",
        "| Distinct policy set | Pairs |",
        "|---|---:|",
    ]
    for combo, count in pair_policy_sets.most_common():
        lines.append(f"| `{'+'.join(combo)}` | {count:,} |")
    lines += [
        "",
        "## Interpretation",
        "",
        "- 세 conflict type의 atomic question은 모든 persona에 존재한다.",
        "- 서로 다른 type의 question이 같은 session에 함께 있는 사례도 존재한다.",
        "- 그러나 같은 session이라는 사실은 하나의 자연스러운 goal이나 독립 `K=2`를 보장하지 않는다.",
        "- 특히 동일 dynamic event의 ‘변경 여부/변경 내용’ 질문은 두 질문이어도 하나의 conflict unit일 수 있다.",
        "- 따라서 pair pool은 prevalence 결과가 아니라 LLM 초벌과 연구자 검토를 위한 후보 모집단이다.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()

    people = read_jsonl(args.input)
    questions = normalize_questions(people)
    pairs = build_pair_pool(questions)
    audits = persona_audit(people)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "source_audit.jsonl", audits)
    write_jsonl(args.out_dir / "question_index.jsonl", questions)
    write_jsonl(args.out_dir / "same_session_pair_pool.jsonl", pairs)
    (args.out_dir / "schema_report.md").write_text(
        build_report(people, questions, pairs, args.revision), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
