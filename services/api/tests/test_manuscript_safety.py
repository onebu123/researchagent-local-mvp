from __future__ import annotations

import pytest

from app.tools.manuscript_safety import check_manuscript_safety


@pytest.mark.parametrize(
    "sentence",
    [
        "The draft makes no causal interpretations.",
        "The manuscript does not make causal conclusions.",
        "The trend is not interpreted as causal.",
        "The summary is written without causal claims.",
        "No causal effect is claimed.",
        "This association is not evidence of causality.",
    ],
)
def test_manuscript_safety_allows_negated_causal_safety_statements(sentence: str) -> None:
    result = check_manuscript_safety(sentence)

    assert result["safe"] is True
    assert result["issues"] == []


@pytest.mark.parametrize(
    "sentence",
    [
        "The intervention had a causal effect on efficiency.",
        "The improvement was caused by the treatment.",
        "This proves the mechanism.",
        "The experiment demonstrated that the process improves stability.",
        "The result was statistically significant.",
        "The comparison reported p = 0.03.",
        "The comparison reported p < 0.05.",
    ],
)
def test_manuscript_safety_blocks_positive_overclaims(sentence: str) -> None:
    result = check_manuscript_safety(sentence)

    assert result["safe"] is False
    assert result["issues"]
