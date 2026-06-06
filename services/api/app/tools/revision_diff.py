from __future__ import annotations

import re
from typing import Any


CHANGE_TYPES = {
    "conservative_rewrite",
    "remove_overclaim",
    "add_evidence_note",
    "mark_as_limitation",
    "needs_human_rewrite",
}

STRONG_REPLACEMENTS = [
    (r"\bstatistically significant\b", "descriptive"),
    (r"\bsignificantly improved\b", "showed an observed increase in"),
    (r"\bsignificantly\b", "descriptively"),
    (r"\bsignificant\b", "observed"),
    (r"\bproved\b", "described"),
    (r"\bproves\b", "describes"),
    (r"\bprove\b", "describe"),
    (r"\bdemonstrated that\b", "described that"),
    (r"\bconfirmed that\b", "described that"),
    (r"\bcausality\b", "association"),
    (r"\bcausal\b", "associative"),
    ("显著提高", "观察到提高"),
    ("显著改善", "观察到改善"),
    ("显著", "观察到"),
    ("证明", "描述"),
    ("证实", "描述"),
    ("因果关系", "相关关系"),
    ("因果", "相关"),
]

BANNED_GENERATED_TERMS = [
    "doi",
    "p-value",
    "p value",
    "p<",
    "p <",
    "statistically significant",
    "causal effect",
]


def _numbers(text: str) -> list[str]:
    return re.findall(r"[-+]?\d+(?:\.\d+)?%?", text)


def _units(text: str) -> list[str]:
    return [
        match.group(0)
        for match in re.finditer(
            r"[-+]?\d+(?:\.\d+)?\s*(?:%|[A-Za-z][A-Za-z0-9/%._-]*)",
            text,
        )
    ]


def _contains_claim_id(text: str) -> str | None:
    match = re.search(r"\bclaim_\d{3,}\b", text)
    return match.group(0) if match else None


def _remove_overclaim(sentence: str) -> str:
    revised = sentence
    for pattern, replacement in STRONG_REPLACEMENTS:
        if pattern.startswith("\\b"):
            revised = re.sub(pattern, replacement, revised, flags=re.IGNORECASE)
        else:
            revised = revised.replace(pattern, replacement)
    revised = re.sub(r"\s+", " ", revised).strip()
    return revised


def _has_banned_generated_content(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in BANNED_GENERATED_TERMS)


def build_revision_diff(issue: dict[str, Any]) -> dict[str, Any]:
    sentence = str(issue.get("sentence") or "").strip()
    issue_type = str(issue.get("issue_type") or "needs_human_rewrite")
    related_claim_id = issue.get("related_claim_id")
    preserved_claim_id = related_claim_id if isinstance(related_claim_id, str) else _contains_claim_id(sentence)
    warnings = [
        "Suggestion is not applied to manuscript automatically.",
        "Human approval is required before any manuscript change.",
    ]

    if not sentence:
        return {
            "can_auto_suggest": False,
            "before": sentence,
            "after": "",
            "change_type": "needs_human_rewrite",
            "preserved_claim_id": preserved_claim_id,
            "preserved_numbers": True,
            "preserved_units": True,
            "requires_human_approval": True,
            "warnings": [*warnings, "Original sentence is empty."],
        }

    if issue_type == "overclaim":
        after = _remove_overclaim(sentence)
        change_type = "remove_overclaim"
        if after == sentence or _has_banned_generated_content(after):
            change_type = "needs_human_rewrite"
            warnings.append("Automatic rewrite could not safely remove all overclaim wording.")
    elif issue_type in {"missing_claim_alignment", "missing_evidence"}:
        after = (
            f"{sentence} This statement requires a supported claim_id or should be moved to "
            "limitations before submission."
        )
        change_type = "add_evidence_note"
    elif issue_type == "discussion_over_inference":
        after = (
            f"{sentence} Treat this as a limitation or future-work note unless direct evidence is added."
        )
        change_type = "mark_as_limitation"
    elif issue_type in {"placeholder_citation", "citation_placeholder"}:
        after = f"{sentence} Citation metadata requires manual verification before submission."
        change_type = "add_evidence_note"
    else:
        after = f"{sentence} Please revise conservatively and preserve the linked evidence."
        change_type = "conservative_rewrite"

    before_numbers = _numbers(sentence)
    after_numbers = _numbers(after)
    before_units = _units(sentence)
    after_units = _units(after)
    preserved_numbers = before_numbers == after_numbers[: len(before_numbers)]
    preserved_units = before_units == after_units[: len(before_units)]

    if preserved_claim_id and preserved_claim_id not in after:
        warnings.append(f"Linked claim_id {preserved_claim_id} is not present in the suggested text.")
    if not preserved_numbers:
        warnings.append("Numbers changed or were not fully preserved.")
    if not preserved_units:
        warnings.append("Units changed or were not fully preserved.")
    if _has_banned_generated_content(after):
        warnings.append("Suggested text still contains wording that needs manual review.")
        change_type = "needs_human_rewrite"

    if change_type not in CHANGE_TYPES:
        change_type = "needs_human_rewrite"

    return {
        "can_auto_suggest": change_type != "needs_human_rewrite",
        "before": sentence,
        "after": after,
        "change_type": change_type,
        "preserved_claim_id": preserved_claim_id,
        "preserved_numbers": preserved_numbers,
        "preserved_units": preserved_units,
        "requires_human_approval": True,
        "warnings": warnings,
    }
