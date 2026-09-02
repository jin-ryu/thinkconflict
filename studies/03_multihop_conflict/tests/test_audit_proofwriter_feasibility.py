import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "src/audit_proofwriter_feasibility.py"
SPEC = importlib.util.spec_from_file_location("audit_proofwriter_feasibility", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_polarity_round_trip():
    positive = '("cow" "is" "blue" "+")'
    negative = '("cow" "is" "blue" "-")'
    assert MODULE.target_polarity(positive) == "+"
    assert MODULE.flip_polarity(positive) == negative
    assert MODULE.flip_polarity(negative) == positive


def test_rule_application_count():
    proof = "((((triple1) -> (rule3 % int2))) -> (rule2 % int1))"
    assert MODULE.rule_application_count(proof) == 2
