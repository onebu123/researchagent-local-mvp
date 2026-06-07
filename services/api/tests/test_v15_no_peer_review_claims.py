from __future__ import annotations

import json
from pathlib import Path

from app.tools.workspace_export import build_workspace_export


FORBIDDEN_POSITIVE_CLAIMS = [
    "is peer-review-ready",
    "are peer-review-ready",
    "peer-review ready",
    "is production-ready",
    "are production-ready",
    "production ready",
    "is compliance-ready",
    "are compliance-ready",
    "compliance ready",
    "proves scientific truth",
    "scientifically proven",
    "statistically significant",
    "causal effect",
    "caused by",
]


def test_workspace_export_does_not_claim_peer_review_or_production_readiness(
    demo_project_dir: Path,
) -> None:
    build_workspace_export(demo_project_dir, "demo_project")
    combined = "\n".join(
        (demo_project_dir / relative_path).read_text(encoding="utf-8")
        for relative_path in [
            "exports/workspace/research_workspace_export.tex",
            "exports/workspace/trust_report.md",
            "exports/workspace/trust_report.json",
            "exports/workspace/workspace_export_manifest.json",
        ]
    ).lower()

    for marker in FORBIDDEN_POSITIVE_CLAIMS:
        assert marker not in combined, f"workspace export must not include positive claim: {marker}"

    assert "not a production compliance archive" in combined
    assert "not scientific or compliance validation" in combined


def test_workspace_trust_report_keeps_local_mvp_scope(demo_project_dir: Path) -> None:
    build_workspace_export(demo_project_dir, "demo_project")
    payload = json.loads(
        (demo_project_dir / "exports" / "workspace" / "trust_report.json").read_text(
            encoding="utf-8"
        )
    )

    assert payload["scope"] == "local_mvp_workspace_export"
    assert any("local ResearchAgent artifacts" in caveat for caveat in payload["caveats"])
    assert any("not a production compliance archive" in caveat for caveat in payload["caveats"])
