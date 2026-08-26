from composite_conflict.prepare_pilot1 import natconfqa_view


def test_natconfqa_answer_evidence_indices_are_mapped_to_document_ids():
    record = {
        "question_id": "example.1",
        "topic_id": "example",
        "question": "Example?",
        "paragraphs": ["p0", "p1", "p2"],
        "evidences": [
            {"text": "e0", "label": "Supports", "paragraph_id": 2},
            {"text": "e1", "label": "Refutes", "paragraph_id": 0},
            {"text": "e2", "label": "Neutral", "paragraph_id": 2},
        ],
        "answers": [
            {"answer": "a", "evidence_ids": [0, 2]},
            {"answer": "b", "evidence_ids": [1, 99]},
        ],
    }

    view = natconfqa_view(record)

    assert view["answer_candidates"][0]["source_evidence_ids"] == [0, 2]
    assert view["answer_candidates"][0]["doc_ids"] == ["2"]
    assert view["answer_candidates"][1]["source_evidence_ids"] == [1, 99]
    assert view["answer_candidates"][1]["doc_ids"] == ["0"]


def test_natconfqa_candidate_doc_ids_always_exist_in_view():
    record = {
        "question_id": "example.2",
        "topic_id": "example",
        "question": "Example?",
        "paragraphs": ["p0", "p1"],
        "evidences": [
            {"text": "e0", "label": "Supports", "paragraph_id": 1},
        ],
        "answers": [{"answer": "a", "evidence_ids": [0, 4]}],
    }

    view = natconfqa_view(record)
    document_ids = {document["doc_id"] for document in view["documents"]}

    for candidate in view["answer_candidates"]:
        assert set(candidate["doc_ids"]) <= document_ids
