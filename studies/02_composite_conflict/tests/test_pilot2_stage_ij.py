"""Regression tests for Stage I generators and Stage J analyses."""

from pathlib import Path

from composite_conflict.analyze_pilot2_stage_j_independence import (
    mcnemar_exact,
    paired_table,
    unit_judgments,
)
from composite_conflict.analyze_pilot2_stage_j_leakage import alternatives, attribute
from composite_conflict.prepare_pilot2_stage_i_anchor import matched_partners
from composite_conflict.prepare_pilot2_stage_i_controls import compact, control_units, gold_answer


def test_mcnemar_exact_symmetric_and_bounded():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 5) == 1.0
    assert mcnemar_exact(10, 0) == mcnemar_exact(0, 10)
    assert 0 < mcnemar_exact(10, 0) < 0.01


def test_paired_table_gap_and_retention():
    pairs = [(True, True), (True, False), (True, False), (False, False)]
    table = paired_table(pairs)
    assert table["atomic_only"] == 2 and table["composite_only"] == 0
    assert table["gap"] == 0.5
    assert table["retained_given_atomic_correct"]["rate"] == round(1 / 3, 4)


def test_unit_judgments_reads_unit_results():
    rows = [{"instance_id": "x", "judgment": {"unit_results": [{"unit_id": "u1", "correct": True}, {"unit_id": "u2", "correct": False}]}}]
    assert unit_judgments(rows) == {"x": {"u1": True, "u2": False}}


def test_control_units_skip_attributes_updated_immediately():
    person = {
        "ID": "p1",
        "Full_Session_Chain": [
            {"Session_ID": 0, "Date": "2022-01-01", "Revealed_Attributes": {"Residence": "Oslo", "Work_Status": {"Current_State": "Normal"}}},
            {"Session_ID": 1, "Date": "2022-02-01", "Updated_Attributes": [{"Attribute": "Work_Status", "Before": "Normal", "After": "Busy"}]},
            {"Session_ID": 2, "Date": "2022-03-01"},
            {"Session_ID": 3, "Date": "2022-04-01", "Updated_Attributes": [{"Attribute": "Residence", "Before": "Oslo", "After": "Bergen"}]},
        ],
    }
    units = control_units(person)
    assert [u["attribute"] for u in units] == ["Residence"]
    assert units[0]["target_date"] == "2022-03-01"  # session before the first update
    assert units[0]["gold_unit"]["policy"] == "LOOKUP"
    assert compact({"a": {"b": 1}, "c": "x"}) == "a: b: 1; c: x"
    career = {"Employment_Status": "Employed", "Company_Name": "Acme", "Job_Title": "Senior", "Industry": "Media", "Monthly_Income": "5000-10000"}
    assert gold_answer("Career_Status", career) == "Employment_Status: Employed; Company_Name: Acme; Job_Title: Senior; Industry: Media"
    assert gold_answer("Marital_Status", {"Status": "Dating", "Name": "X", "Birthdate": "2000-01-01"}) == "Status: Dating"
    assert gold_answer("Children_Status", {"Status": "Yes", "Child_1": {"Name": "Maya", "Birthdate": "2014-02-04"}}) == "Status: Yes; Children: Maya"


def _unit(uid, policy, attr, records):
    return {"memory_context": records, "gold_unit": {"unit_id": uid, "policy": policy, "target_attribute": attr}}


def test_matched_partners_respects_record_and_token_limits():
    small = [{"memory_id": f"m{i}", "claim": {"value": "x" * 20}} for i in range(2)]
    big = [{"memory_id": f"b{i}", "claim": {"value": "y" * 200}} for i in range(6)]
    anchor = _unit("a", "SUPERSEDE", "Residence", small)
    b_ok = _unit("b", "SUPERSEDE", "Career_Status", small)
    c_ok = _unit("c", "CONDITION", "CC_1", small)
    c_big = _unit("cb", "CONDITION", "CC_2", big)
    assert matched_partners(anchor, [anchor, b_ok], {"CONDITION": [c_big], "VERIFY_PREFER": []}, "CONDITION") is None
    match = matched_partners(anchor, [anchor, b_ok], {"CONDITION": [c_big, c_ok], "VERIFY_PREFER": []}, "CONDITION")
    assert match is not None and match[1]["gold_unit"]["unit_id"] == "c" and match[2] == "CONDITION"


def test_leakage_attribution_labels():
    records = {
        "p:S1:Residence:prior": {"memory_id": "p:S1:Residence:prior", "source": "user_profile_history", "claim": {"attribute": "Residence", "value": "Groningen"}},
        "p:S1:Residence:update": {"memory_id": "p:S1:Residence:update", "source": "user_update", "claim": {"attribute": "Residence", "value": "Amsterdam"}},
    }
    unit = {"unit_id": "u", "policy": "SUPERSEDE", "target_attribute": "Residence", "gold_atomic_answer": "They moved from Groningen to Amsterdam.", "evidence_ids": list(records)}
    gold, alts = alternatives(unit, records)
    assert gold == ["Amsterdam"] and alts[0]["label"] == "stale_kept" and alts[0]["strings"] == ["Groningen"]
    assert attribute("The user lives in Groningen.", gold, alts) == "stale_kept"
    assert attribute("They moved from Groningen to Amsterdam.", gold, alts) == "gold_and_alt"
    assert attribute("Amsterdam", gold, alts) == "gold_present_but_wrong"
    assert attribute("Unknown", gold, alts) == "unattributed"
