from composite_conflict.agreement import _kappa_or_none


def test_kappa_is_undefined_for_single_observed_class():
    assert _kappa_or_none([False, False], [False, False]) is None


def test_kappa_is_computed_when_two_classes_exist():
    assert _kappa_or_none([False, True], [False, True]) == 1.0
