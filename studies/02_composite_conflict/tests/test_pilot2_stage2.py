from composite_conflict.evaluate_pilot2_outputs import evaluate
from composite_conflict.run_pilot2_baselines import prompt_for


def _single_instance():
    return {
        "instance_id": "x::single::u1",
        "target_date": "2026-01-01",
        "condition": "single_unit",
        "K": 1,
        "H": 1,
        "policies": ["SUPERSEDE"],
        "query": "What is current?",
        "memory_context": [{"memory_id": "m1", "claim": "New value"}],
        "gold_units": [{
            "unit_id": "u1",
            "policy": "SUPERSEDE",
            "gold_atomic_answer": "New value",
            "evidence_ids": ["m1"],
        }],
    }


def test_prompt_uses_dynamic_unit_count():
    prompt = prompt_for(_single_instance(), "direct")
    assert "exactly 1 objects" in prompt[0]["content"]
    assert "every requested part" in prompt[0]["content"]


def test_evaluator_accepts_one_resolved_unit():
    output = {
        "run_id": "r1",
        "instance_id": "x::single::u1",
        "baseline_condition": "direct",
        "response": {
            "analysis_summary": "New value",
            "resolved_units": [{"unit_id": "u1", "resolution": "New value", "used_memory_ids": ["m1"]}],
            "final_answer": "New value",
        },
    }
    result = evaluate(output, _single_instance())
    assert result["automatic_all_unit_success"] is True
    assert result["unit_omission"] is False
