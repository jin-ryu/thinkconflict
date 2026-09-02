from __future__ import annotations

import importlib.util
import json
from pathlib import Path

STUDY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = STUDY_ROOT / "src" / "prepare_pilot_a_data.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_pilot_a_data", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_triplet_parser_and_normalization():
    module = load_module()
    assert module.parse_triplet("(A | related to | B)") == ("A", "related to", "B")
    assert module.parse_triplet("(A | relation | fragment | B)") == (
        "A",
        "relation | fragment",
        "B",
    )
    assert module.normalize("Pyrénées-Orientales") == "pyrenees orientales"
    assert module.triplet_list("(A | r | B)") == ["(A | r | B)"]
    assert module.triplet_list(["(A | r | B)", "(C | r | D)"]) == [
        "(A | r | B)",
        "(C | r | D)",
    ]
    assert module.triplet_list([["(A | r | B)"], ["(C | r | D)"]]) == [
        "(A | r | B)",
        "(C | r | D)",
    ]


def test_built_manifest_has_planned_counts_and_no_raw_text():
    manifest_path = STUDY_ROOT / "data" / "pilot_a" / "sample_manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    primary = [record for record in manifest["records"] if record["role"] == "primary"]
    reserve = [record for record in manifest["records"] if record["role"] == "reserve"]
    assert len(primary) == 76
    assert len(reserve) == 38
    assert len({record["instance_id"] for record in manifest["records"]}) == 114
    assert all("context1" not in record and "context2" not in record for record in manifest["records"])
