import random

from composite_conflict.prepare_audit import _sample


def test_audit_sampling_rounds_up_and_is_deterministic():
    records = [{"instance_id": str(index)} for index in range(11)]
    first = _sample(records, 0.20, random.Random(7))
    second = _sample(records, 0.20, random.Random(7))
    assert len(first) == 3
    assert first == second
