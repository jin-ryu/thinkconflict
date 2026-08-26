from composite_conflict.review_case import render_case


def test_render_case_contains_question_evidence_and_draft():
    view = {
        "instance_id": "x-1",
        "dataset": "x",
        "question": "Which answer?",
        "answer_candidates": [{"answer": "A", "doc_ids": ["0"]}],
        "documents": [
            {
                "doc_id": "0",
                "url": "https://example.test",
                "content_preview": "supporting text",
            }
        ],
    }
    draft = {"instance_id": "x-1", "K": 1, "H": 1}

    rendered = render_case(view, draft)

    assert "QUESTION: Which answer?" in rendered
    assert "DOC 0" in rendered
    assert "supporting text" in rendered
    assert '"K": 1' in rendered
