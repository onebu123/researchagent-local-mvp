from __future__ import annotations

import re
from typing import Any


def _normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _tokens(value: Any) -> set[str]:
    return set(_normalize_text(value).split())


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def _token_score(left: Any, right: Any) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    if _normalize_text(left) == _normalize_text(right):
        return 1.0
    overlap = len(left_tokens & right_tokens)
    denominator = max(len(left_tokens), len(right_tokens))
    return _clamp(overlap / denominator)


def _normalize_doi(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text)
    return text


def _author_score(query_authors: Any, candidate_authors: Any) -> float:
    if not isinstance(query_authors, list) or not isinstance(candidate_authors, list):
        return 0.0
    query_names = {_normalize_text(author) for author in query_authors if _normalize_text(author)}
    candidate_names = {
        _normalize_text(author) for author in candidate_authors if _normalize_text(author)
    }
    if not query_names or not candidate_names:
        return 0.0
    overlap = len(query_names & candidate_names)
    return _clamp(overlap / max(len(query_names), len(candidate_names)))


def calculate_match_scores(query: dict[str, Any], candidate: dict[str, Any] | None) -> dict[str, Any]:
    candidate = candidate or {}
    title_match_score = _token_score(query.get("title"), candidate.get("title"))
    author_match_score = _author_score(query.get("authors"), candidate.get("authors"))
    journal_match_score = _token_score(query.get("journal"), candidate.get("journal"))

    query_year = query.get("year")
    candidate_year = candidate.get("year")
    year_matches = (
        query_year is not None
        and candidate_year is not None
        and str(query_year).strip() == str(candidate_year).strip()
    )
    if query_year is None or candidate_year is None:
        year_match = "missing"
    elif year_matches:
        year_match = "match"
    else:
        year_match = "mismatch"

    query_doi = _normalize_doi(query.get("doi"))
    candidate_doi = _normalize_doi(candidate.get("doi"))
    doi_matches = bool(query_doi and candidate_doi and query_doi == candidate_doi)
    doi_mismatch = bool(query_doi and candidate_doi and query_doi != candidate_doi)
    doi_missing = not bool(query_doi and candidate_doi)
    if doi_missing:
        doi_match = "missing"
    elif doi_matches:
        doi_match = "match"
    else:
        doi_match = "mismatch"
    year_mismatch = year_match == "mismatch"

    doi_score = 1.0 if doi_matches else 0.0
    year_score = 1.0 if year_matches else 0.0
    confidence = (
        title_match_score * 0.35
        + author_match_score * 0.2
        + doi_score * 0.25
        + journal_match_score * 0.1
        + year_score * 0.1
    )
    if doi_mismatch:
        confidence -= 0.2
    if year_mismatch:
        confidence -= 0.1
    if doi_missing:
        confidence = min(confidence, 0.72)
    if title_match_score < 0.4 and not doi_matches:
        confidence = min(confidence, 0.35)

    return {
        "title_match_score": _clamp(title_match_score),
        "author_match_score": _clamp(author_match_score),
        "year_match": year_match,
        "doi_match": doi_match,
        "journal_match_score": _clamp(journal_match_score),
        "overall_confidence": _clamp(confidence),
    }
