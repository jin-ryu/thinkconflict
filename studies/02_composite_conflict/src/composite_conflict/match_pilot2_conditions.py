"""Create a transparent one-to-one draft match between Pilot 2 H=2 and H=1."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment


DOMAINS = {
    "work": r"\b(?:work|workload|career|job|employment|employed|company|industry|business|professional|research|coding|rehearsal|writing)\w*",
    "health": r"\b(?:health|stress|fatigue|fatigued|unwell|recovery|self-care|exercise|workout)\w*",
    "social": r"\b(?:social|friend|relationship|marital|dating|single|group|people|connected)\w*",
    "family": r"\b(?:child|children|childcare|baby|family|parent)\w*",
    "residence_travel": r"\b(?:residence|relocation|moved|city|travel|trip|hotel|hostel|resort|camping)\w*",
    "reading_media": r"\b(?:read|reading|book|journal|newspaper|movie|film|game|music|watch|entertainment)\w*",
    "food_drink": r"\b(?:food|meal|dinner|breakfast|snack|drink|tea|coffee|juice|soup)\w*",
    "clothing": r"\b(?:clothing|outfits?|shirts?|tanks?|business suit|evening dress|shoes)\b",
    "schedule": r"\b(?:schedule|routine|week|weekend|morning|evening|break|plan|priority|priorities)\w*",
}

STOP = {
    "the", "a", "an", "and", "or", "to", "for", "my", "me", "of", "in", "on",
    "with", "that", "what", "when", "does", "user", "given", "current", "latest",
    "based", "suitable", "suggest", "plan", "preference", "preferences",
}


def load(path: Path) -> list[dict]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def text_of(row: dict) -> str:
    review = row["codex_review"]
    return " ".join([review["combined_query"], *row["questions"], *row["answers"]]).lower()


def domains(text: str) -> set[str]:
    return {name for name, pattern in DOMAINS.items() if re.search(pattern, text)}


def tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z][a-z-]+", text) if token not in STOP and len(token) > 2}


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left | right else 0.0


def pair_score(h2: dict, h1: dict) -> tuple[float, dict]:
    h2_text, h1_text = text_of(h2), text_of(h1)
    h2_domains, h1_domains = domains(h2_text), domains(h1_text)
    domain_score = jaccard(h2_domains, h1_domains)
    token_score = jaccard(tokens(h2_text), tokens(h1_text))
    query_len_2 = len(h2["codex_review"]["combined_query"].split())
    query_len_1 = len(h1["codex_review"]["combined_query"].split())
    answer_len_2 = sum(len(answer.split()) for answer in h2["answers"])
    answer_len_1 = sum(len(answer.split()) for answer in h1["answers"])
    query_ratio = min(query_len_1, query_len_2) / max(query_len_1, query_len_2)
    answer_ratio = min(answer_len_1, answer_len_2) / max(answer_len_1, answer_len_2)
    score = 0.50 * domain_score + 0.20 * token_score + 0.15 * query_ratio + 0.15 * answer_ratio
    details = {
        "domain_jaccard": round(domain_score, 4),
        "token_jaccard": round(token_score, 4),
        "query_length_ratio": round(query_ratio, 4),
        "answer_length_ratio": round(answer_ratio, 4),
        "h2_domains": sorted(h2_domains),
        "h1_domains": sorted(h1_domains),
    }
    return score, details


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("h2_reviews", type=Path)
    parser.add_argument("h1_reviews", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    h2 = [row for row in load(args.h2_reviews) if row["codex_review"]["codex_valid"]]
    h1 = [row for row in load(args.h1_reviews) if row["codex_review"]["codex_valid"]]
    if len(h2) != len(h1):
        raise ValueError(f"One-to-one matching requires equal sizes: H2={len(h2)}, H1={len(h1)}")

    scores = np.zeros((len(h2), len(h1)))
    detail_grid = {}
    for i, h2_row in enumerate(h2):
        for j, h1_row in enumerate(h1):
            score, details = pair_score(h2_row, h1_row)
            scores[i, j] = score
            detail_grid[(i, j)] = details

    row_indices, col_indices = linear_sum_assignment(-scores)
    matches = []
    for match_number, (i, j) in enumerate(zip(row_indices, col_indices), start=1):
        matches.append({
            "match_id": f"M{match_number:02d}",
            "h2_pair_id": h2[i]["pair_id"],
            "h1_pair_id": h1[j]["pair_id"],
            "h1_subgroup": h1[j]["codex_review"]["h1_subgroup"],
            "h2_query": h2[i]["codex_review"]["combined_query"],
            "h1_query": h1[j]["codex_review"]["combined_query"],
            "automatic_match_score": round(float(scores[i, j]), 4),
            "score_components": detail_grid[(i, j)],
            "match_status": "draft_needs_codex_review",
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        for row in matches:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({
        "matches": len(matches),
        "mean_score": round(float(np.mean([row["automatic_match_score"] for row in matches])), 4),
        "min_score": round(float(np.min([row["automatic_match_score"] for row in matches])), 4),
    }, indent=2))


if __name__ == "__main__":
    main()
