from composite_conflict.finalize_pilot2_codex_reviews import JUDGE
from composite_conflict.pilot2_memory import build_pair_pool, normalize_questions


def _person():
    return {
        "ID": "p1",
        "Fixed_Profile": {"Name": "A"},
        "Life_Goal": {},
        "metadata": {"persona_seed": "seed"},
        "Full_Session_Chain": [
            {
                "Session_ID": 1,
                "Date": "2026-01-01",
                "Session_Type": "update",
                "Event_Types": [],
                "Session_Outline": "outline",
                "Question_Trigger_Types": [],
                "Updated_Attributes": [],
                "Static_Conflict_Information": [],
                "Conditional_Conflict_Information": [],
                "Session_Questions": [
                    {
                        "question_id": "Q1",
                        "question": "q1",
                        "answer": "a1",
                        "conflict_type": "dynamic_conflict",
                        "ability_target": "track_state_over_time",
                        "difficulty": "easy",
                    },
                    {
                        "question_id": "Q2",
                        "question": "q2",
                        "answer": "a2",
                        "conflict_type": "conditional_conflict",
                        "ability_target": "bind_condition",
                        "difficulty": "medium",
                    },
                ],
            }
        ],
    }


def test_normalize_and_pair_heterogeneity():
    questions = normalize_questions([_person()])
    assert len(questions) == 2
    pairs = build_pair_pool(questions)
    assert len(pairs) == 1
    assert pairs[0]["K_candidate"] == 2
    assert pairs[0]["H"] == 2
    assert pairs[0]["condition"] == "heterogeneous"
    assert set(pairs[0]["policies"]) == {"SUPERSEDE", "CONDITION"}


def test_codex_judge_metadata_is_explicitly_exploratory():
    assert JUDGE["protocol"] == "pilot2-codex-direct-v1"
    assert JUDGE["deployment_checkpoint"] == "not exposed by the interface"
    assert JUDGE["intended_use"] == "exploratory feasibility only"
