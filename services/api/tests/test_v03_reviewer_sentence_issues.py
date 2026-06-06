from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.services.workflow_service import workflow_service
from main import app


def test_review_report_contains_sentence_issues(demo_project_dir: Path) -> None:
    report = json.loads(
        (demo_project_dir / "reviews" / "review_report.json").read_text(encoding="utf-8")
    )

    assert "sentence_issues" in report
    assert isinstance(report["sentence_issues"], list)
    if report["sentence_issues"]:
        issue = report["sentence_issues"][0]
        for field in [
            "issue_id",
            "section",
            "sentence",
            "issue_type",
            "severity",
            "related_claim_id",
            "suggested_revision",
        ]:
            assert field in issue


def test_sentence_issues_api_returns_list(demo_project_dir: Path) -> None:
    response = TestClient(app).get("/api/projects/demo_project/review/sentence-issues")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_reviewer_detects_sentence_level_overclaim(demo_project_dir: Path) -> None:
    draft_path = demo_project_dir / "manuscript" / "draft.md"
    original = draft_path.read_text(encoding="utf-8")
    inserted = "The material significantly improved efficiency."
    try:
        draft_path.write_text(
            original.replace("# Discussion", f"{inserted}\n\n# Discussion", 1),
            encoding="utf-8",
        )
        response = workflow_service.run_step("demo_project", "reviewer")
        assert response.workflow_status == "completed"
        report = json.loads(
            (demo_project_dir / "reviews" / "review_report.json").read_text(encoding="utf-8")
        )
        assert report["overclaims"]
        assert any(
            issue.get("issue_type") == "overclaim"
            and "significantly improved" in issue.get("sentence", "")
            and issue.get("severity") == "major"
            for issue in report["sentence_issues"]
        )
        assert report["overall_decision"] in {"major_revision", "reject"}
    finally:
        draft_path.write_text(original, encoding="utf-8")
        workflow_service.run_step("demo_project", "reviewer")
