from __future__ import annotations

from app.tools.reference_match_score import calculate_match_scores


def test_reference_match_score_rewards_exact_metadata_and_doi() -> None:
    source = {
        "title": "Adaptive Retrieval Improves Local Citation Grounding",
        "authors": ["Ada Lovelace", "Grace Hopper"],
        "year": 2026,
        "doi": "10.1234/local.2026",
        "journal": "Journal of Local Methods",
    }
    candidate = {
        "title": "Adaptive Retrieval Improves Local Citation Grounding",
        "authors": ["Ada Lovelace", "Grace Hopper"],
        "year": 2026,
        "doi": "https://doi.org/10.1234/local.2026",
        "journal": "Journal of Local Methods",
    }

    score = calculate_match_scores(source, candidate)

    assert score["doi_match"] == "match"
    assert score["year_match"] == "match"
    assert score["title_match_score"] == 1
    assert score["overall_confidence"] >= 0.9


def test_reference_match_score_caps_missing_doi_and_penalizes_mismatch() -> None:
    source = {
        "title": "Adaptive Retrieval Improves Local Citation Grounding",
        "authors": ["Ada Lovelace"],
        "year": 2026,
        "doi": "10.1234/local.2026",
    }

    missing_doi = calculate_match_scores(source, {"title": source["title"], "authors": source["authors"], "year": 2026})
    wrong_doi = calculate_match_scores(
        source,
        {
            "title": source["title"],
            "authors": source["authors"],
            "year": 2026,
            "doi": "10.9999/wrong",
        },
    )

    assert missing_doi["doi_match"] == "missing"
    assert missing_doi["overall_confidence"] <= 0.72
    assert wrong_doi["doi_match"] == "mismatch"
    assert wrong_doi["overall_confidence"] < missing_doi["overall_confidence"]
