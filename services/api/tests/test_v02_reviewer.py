from __future__ import annotations

import json
from pathlib import Path

from app.services.workflow_service import workflow_service


def test_reviewer_reports_placeholder_literature(demo_project_dir: Path) -> None:
    report = json.loads(
        (demo_project_dir / "reviews" / "review_report.json").read_text(encoding="utf-8")
    )

    assert report["overall_decision"] in {"major_revision", "reject"}
    assert report["citation_issues"]
    assert "placeholder" in " ".join(report["citation_issues"])


def test_reviewer_detects_overclaim_in_draft(demo_project_dir: Path) -> None:
    draft_path = demo_project_dir / "manuscript" / "draft.md"
    original = draft_path.read_text(encoding="utf-8")
    try:
        draft_path.write_text(
            original + "\n\nThe material significantly improved efficiency.\n",
            encoding="utf-8",
        )
        response = workflow_service.run_step("demo_project", "reviewer")
        assert response.workflow_status == "completed"
        report = json.loads(
            (demo_project_dir / "reviews" / "review_report.json").read_text(encoding="utf-8")
        )
        assert report["overclaims"]
        assert "significantly" in str(report["overclaims"])
    finally:
        draft_path.write_text(original, encoding="utf-8")
        workflow_service.run_step("demo_project", "reviewer")


def test_reviewer_reports_missing_figure_provenance(demo_project_dir: Path) -> None:
    figure_path = demo_project_dir / "figures" / "figure_provenance.json"
    original = figure_path.read_text(encoding="utf-8")
    try:
        figure_path.unlink()
        response = workflow_service.run_step("demo_project", "reviewer")
        assert response.workflow_status == "completed"
        report = json.loads(
            (demo_project_dir / "reviews" / "review_report.json").read_text(encoding="utf-8")
        )
        assert report["figure_issues"]
    finally:
        figure_path.write_text(original, encoding="utf-8")
        workflow_service.run_step("demo_project", "reviewer")
