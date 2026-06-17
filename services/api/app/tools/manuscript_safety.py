from __future__ import annotations

import re
from typing import Any


RISK_PATTERNS: list[tuple[str, str, str]] = [
    ("causal_overclaim", "causal effect", r"\bcausal effect\b"),
    ("causal_overclaim", "caused by", r"\bcaused by\b"),
    ("causal_overclaim", "causal conclusion", r"\bcausal conclusions?\b"),
    ("causal_overclaim", "causal interpretation", r"\bcausal interpretations?\b"),
    ("causal_overclaim", "causal claim", r"\bcausal claims?\b"),
    ("causal_overclaim", "causality", r"\bcausality\b"),
    ("proof_overclaim", "proves", r"\bproves?\b|\bproved\b"),
    ("proof_overclaim", "demonstrated that", r"\bdemonstrated that\b"),
    ("proof_overclaim", "confirmed that", r"\bconfirmed that\b"),
    ("statistical_overclaim", "statistically significant", r"\bstatistically significant\b"),
    ("statistical_overclaim", "significantly", r"\bsignificantly\b"),
    ("statistical_overclaim", "significant", r"\bsignificant\b"),
    ("statistical_overclaim", "p-value", r"\bp\s*(?:=|<|<=|>|>=)\s*0?\.\d+\b"),
    ("statistical_overclaim", "显著", r"显著"),
    ("proof_overclaim", "证明", r"证明"),
    ("proof_overclaim", "证实", r"证实"),
    ("causal_overclaim", "因果", r"因果"),
]

NEGATED_PATTERNS = [
    r"\bno\s+(?:\w+\s+){0,4}{term}",
    r"\bnot\s+(?:\w+\s+){0,4}{term}",
    r"\bwithout\s+(?:\w+\s+){0,4}{term}",
    r"\bdoes\s+not\s+(?:\w+\s+){0,4}{term}",
    r"\bdo\s+not\s+(?:\w+\s+){0,4}{term}",
    r"\bmust\s+not\s+(?:\w+\s+){0,4}{term}",
    r"\bcannot\s+(?:\w+\s+){0,4}{term}",
    r"\bnot\s+evidence\s+of\s+(?:\w+\s+){0,2}{term}",
    r"\b{term}\s+is\s+not\s+claimed\b",
    r"\b{term}\s+is\s+not\s+(?:\w+\s+){0,3}claimed\b",
]


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", normalized) if item.strip()]


def _is_negated(sentence: str, term_pattern: str) -> bool:
    lower = sentence.lower()
    grouped_term = f"(?:{term_pattern})"
    for pattern in NEGATED_PATTERNS:
        combined = pattern.replace("{term}", grouped_term)
        if re.search(combined, lower, flags=re.IGNORECASE):
            return True
    return False


def safety_issues_for_sentence(sentence: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for issue_type, term, pattern in RISK_PATTERNS:
        if not re.search(pattern, sentence, flags=re.IGNORECASE):
            continue
        if _is_negated(sentence, pattern):
            continue
        issues.append(
            {
                "issue_type": issue_type,
                "term": term,
                "severity": "major",
                "sentence": sentence,
            }
        )
    return issues


def unsafe_terms_in_sentence(sentence: str) -> list[str]:
    return sorted({issue["term"] for issue in safety_issues_for_sentence(sentence)})


def check_manuscript_safety(text: str) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    for sentence in _split_sentences(text):
        issues.extend(safety_issues_for_sentence(sentence))
    return {
        "safe": not issues,
        "issues": issues,
        "blocked_reasons": [
            f"{issue['issue_type']}: {issue['term']}" for issue in issues
        ],
    }
