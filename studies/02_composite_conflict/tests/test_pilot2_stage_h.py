from composite_conflict.run_pilot2_stage_h import assign_groups, payload


def _instance():
    return {
        "instance_id": "stageh:test:original",
        "target_date": "2026-01-02",
        "K": 2,
        "H": 2,
        "query": "1. Current job?\n2. Preferred drink while working?",
        "memory_context": [
            {"memory_id": "p:S1:Job:prior", "source": "user_profile_history", "claim": "old"},
            {"memory_id": "p:S2:C1:1", "source": "user_preference_statement", "claim": {"item": "tea", "condition": "working"}},
            {"memory_id": "p:S1:Job:update", "source": "user_update", "claim": "new"},
            {"memory_id": "p:S2:C1:2", "source": "user_preference_statement", "claim": {"item": "juice", "condition": "weekend"}},
            {"memory_id": "p:S2:C1:3", "source": "other_person_statement", "claim": {"item": "coffee"}},
        ],
        "gold_units": [
            {
                "unit_id": "u1",
                "policy": "SUPERSEDE",
                "atomic_question": "Current job?",
                "unit_target_date": "2026-01-02",
                "gold_atomic_answer": "new",
                "evidence_ids": ["p:S1:Job:prior", "p:S1:Job:update"],
            },
            {
                "unit_id": "u2",
                "policy": "CONDITION",
                "atomic_question": "Preferred drink while working?",
                "unit_target_date": "2026-01-02",
                "gold_atomic_answer": "tea",
                "evidence_ids": ["p:S2:C1:1", "p:S2:C1:2", "p:S2:C1:3"],
            },
        ],
    }


def test_assign_groups_recovers_interleaved_ownership():
    groups = assign_groups(_instance())
    assert [record["memory_id"] for record in groups[0]["records"]] == [
        "p:S1:Job:prior",
        "p:S1:Job:update",
    ]
    assert len(groups[1]["records"]) == 3


def test_shared_distractor_is_copied_to_each_matching_group():
    instance = _instance()
    instance["gold_units"][0]["evidence_ids"] = ["p:S2:C1:a"]
    instance["gold_units"][1]["evidence_ids"] = ["p:S2:C1:b"]
    instance["memory_context"] = [
        {"memory_id": "p:S2:C1:a", "source": "verified_profile_record", "claim": "a"},
        {"memory_id": "p:S2:C1:b", "source": "verified_profile_record", "claim": "b"},
        {"memory_id": "p:S2:C1:c", "source": "other_person_statement", "claim": "shared"},
    ]
    groups = assign_groups(instance)
    assert groups[0]["records"][-1]["claim"] == "shared"
    assert groups[1]["records"][-1]["claim"] == "shared"


def test_grouped_only_hides_policy_and_gold_answer():
    body = payload(_instance(), "grouped_only")
    assert "required_behavior" not in str(body)
    assert "gold_answer" not in str(body)


def test_owner_and_target_filters_remove_expected_records():
    owner = payload(_instance(), "owner_filter")
    assert "other_person_statement" not in str(owner)
    assert "juice" in str(owner)

    target = payload(_instance(), "target_filter")
    assert "other_person_statement" not in str(target)
    assert "tea" in str(target)
    assert "juice" not in str(target)


def test_full_local_exposes_policy_but_not_gold_answer():
    body = payload(_instance(), "full_local")
    assert "SUPERSEDE" in str(body)
    assert "CONDITION" in str(body)
    assert "gold_answer" not in str(body)
    assert "juice" not in str(body)
