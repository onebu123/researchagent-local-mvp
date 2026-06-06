from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


STRONG_CONCLUSION_TERMS = [
    "statistically significant",
    "significantly",
    "significant",
    "prove",
    "proves",
    "proved",
    "causal",
    "causality",
    "causal effect",
    "demonstrated that",
    "confirmed that",
    "显著",
    "证明",
    "证实",
    "因果",
]

P_VALUE_PATTERNS = [
    r"\bp\s*[-_ ]?value\b",
    r"\bp\s*[<=>]\s*0?\.\d+",
    r"\bp\s*[<=>]\s*\d+(?:\.\d+)?e-\d+",
]

DOI_PATTERNS = [
    r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b",
    r"\bdoi\b",
]


def extract_numbers(text: str) -> list[str]:
    normalized = re.sub(r"\bclaim_\d{3,}\b", "claim_ID", text)
    return re.findall(r"[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?%?", normalized, flags=re.IGNORECASE)


def extract_units(text: str) -> list[str]:
    normalized = re.sub(r"\bclaim_\d{3,}\b", "claim_ID", text)
    units: list[str] = []
    for match in re.finditer(
        r"[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?\s*(%|[A-Za-z][A-Za-z0-9/%._-]*)",
        normalized,
        flags=re.IGNORECASE,
    ):
        units.append(match.group(1))
    return units


def _contains_pattern(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def contains_p_value(text: str) -> bool:
    return _contains_pattern(text, P_VALUE_PATTERNS)


def contains_doi(text: str) -> bool:
    return _contains_pattern(text, DOI_PATTERNS)


def strong_terms(text: str) -> list[str]:
    lower = text.lower()
    found: set[str] = set()
    for term in STRONG_CONCLUSION_TERMS:
        if term.isascii():
            if re.search(r"\b" + re.escape(term.lower()) + r"\b", lower):
                found.add(term)
        elif term in text:
            found.add(term)
    return sorted(found)


def _read_evidence_claim_ids(project_dir: Path) -> set[str]:
    path = project_dir / "provenance" / "evidence.json"
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    if not isinstance(payload, list):
        return set()
    return {
        str(item["claim_id"])
        for item in payload
        if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
    }


def check_patch_item(
    project_dir: Path,
    item: dict[str, Any],
    source_manuscript: str = "manuscript/draft.md",
    evidence_claim_ids: set[str] | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    blocked_reasons: list[str] = []

    before = str(item.get("before") or "")
    after = str(item.get("after") or "")
    draft_path = project_dir / source_manuscript
    draft_text = draft_path.read_text(encoding="utf-8", errors="replace") if draft_path.exists() else ""

    if not draft_path.exists():
        blocked_reasons.append(f"source manuscript does not exist: {source_manuscript}")
    elif before not in draft_text:
        blocked_reasons.append("before text was not found in source manuscript")

    if not after.strip():
        blocked_reasons.append("after text is empty")

    before_numbers = extract_numbers(before)
    after_numbers = extract_numbers(after)
    if before_numbers != after_numbers:
        blocked_reasons.append("numbers were changed or new numbers were introduced")

    before_units = extract_units(before)
    after_units = extract_units(after)
    if before_units != after_units:
        blocked_reasons.append("units were changed or new units were introduced")

    if contains_p_value(after):
        blocked_reasons.append("after text contains p-value wording")

    if contains_doi(after):
        blocked_reasons.append("after text contains DOI wording")

    terms = strong_terms(after)
    if terms:
        blocked_reasons.append(f"after text contains strong conclusion terms: {terms}")

    claim_id = item.get("related_claim_id")
    if isinstance(claim_id, str) and claim_id:
        claim_ids = evidence_claim_ids if evidence_claim_ids is not None else _read_evidence_claim_ids(project_dir)
        if claim_id not in claim_ids:
            blocked_reasons.append(f"related_claim_id not found in evidence.json: {claim_id}")
    else:
        warnings.append("patch item is not linked to a related_claim_id")

    return {
        "safe": not blocked_reasons,
        "warnings": warnings,
        "blocked_reasons": blocked_reasons,
    }
