import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "src/proofwriter_logic.py"
SPEC = importlib.util.spec_from_file_location("proofwriter_logic", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_two_hop_forward_chain_and_opposite():
    fact = MODULE.parse_atom('(\"Alan\" \"is\" \"young\" \"+\")')
    rule1 = MODULE.parse_rule('(((\"someone\" \"is\" \"young\" \"+\")) -> (\"someone\" \"is\" \"blue\" \"+\"))')
    rule2 = MODULE.parse_rule('(((\"someone\" \"is\" \"blue\" \"+\")) -> (\"someone\" \"is\" \"kind\" \"+\"))')
    target = MODULE.parse_atom('(\"Alan\" \"is\" \"kind\" \"+\")')
    derived = MODULE.closure([fact], [rule1, rule2])
    assert target in derived
    assert MODULE.opposite(target) not in derived
    assert MODULE.contradictions(derived | {MODULE.opposite(target)})
