from composite_conflict.run_pilot2_baselines import payload


def _instance():
    return {
        "target_date": "2026-01-01",
        "query": "q",
        "memory_context": [{"memory_id": "m1", "claim": "c"}],
        "gold_units": [
            {"unit_id": "u1", "policy": "SUPERSEDE", "gold_atomic_answer": "secret1", "evidence_ids": ["m1"]},
            {"unit_id": "u2", "policy": "CONDITION", "gold_atomic_answer": "secret2", "evidence_ids": ["m2"]},
        ],
    }


def test_non_oracle_payload_does_not_leak_gold_or_policy():
    body = payload(_instance(), "taxonomy_cot")
    assert "relevant_units" not in body
    assert "secret1" not in str(body)
    assert "SUPERSEDE" not in str(body)


def test_oracle_units_hides_policy_and_answer():
    body = payload(_instance(), "oracle_units")
    assert body["relevant_units"][0] == {"unit_id": "u1", "evidence_ids": ["m1"]}
    assert "secret1" not in str(body)


def test_oracle_policy_exposes_behavior_but_not_answer():
    body = payload(_instance(), "oracle_unit_policies")
    assert body["relevant_units"][0]["required_behavior"] == "SUPERSEDE"
    assert "secret1" not in str(body)
