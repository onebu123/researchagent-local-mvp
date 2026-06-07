from __future__ import annotations

from pathlib import Path

from app.tools.statistical_assistant import generate_statistical_assistant_report


FORBIDDEN_CLAIM_MARKERS = [
    "p<",
    "p =",
    "statistically significant",
    "significant difference",
    "caused by",
    "causal effect",
    "causation",
    "proves",
    "confirmed hypothesis",
]


def test_statistical_assistant_does_not_generate_inference_claims(
    demo_project_dir: Path,
) -> None:
    report = generate_statistical_assistant_report(demo_project_dir, "demo_project")
    notes = (demo_project_dir / "analysis" / "statistical_assistant_notes.md").read_text(
        encoding="utf-8"
    )

    combined = f"{report}\n{notes}".lower()
    for marker in FORBIDDEN_CLAIM_MARKERS:
        assert marker not in combined

    assert "association candidate" in combined or "association_candidate" in combined
    assert "does not generate p-values" in combined
    assert "does not perform causal inference" in combined
