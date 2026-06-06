from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.services.workflow_service import workflow_service
from app.tools.revision_diff import build_revision_diff
from main import app


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_sentence_issues_include_revision_diff(demo_project_dir: Path) -> None:
    report = _read_json(demo_project_dir / "reviews" / "review_report.json")
    issues = report["sentence_issues"]
    assert issues
    diff = issues[0]["revision_diff"]
    for field in [
        "can_auto_suggest",
        "before",
        "after",
        "change_type",
        "preserved_claim_id",
        "preserved_numbers",
        "preserved_units",
        "requires_human_approval",
        "warnings",
    ]:
        assert field in diff
    assert diff["requires_human_approval"] is True


def test_revision_diff_removes_overclaim_without_changing_numbers() -> None:
    diff = build_revision_diff(
        {
            "sentence": "The method significantly improved efficiency by 5%.",
            "issue_type": "overclaim",
            "related_claim_id": None,
        }
    )
    assert diff["change_type"] == "remove_overclaim"
    assert "significantly" not in diff["after"].lower()
    assert diff["preserved_numbers"] is True
    assert diff["requires_human_approval"] is True


def test_reviewer_overclaim_issue_has_revision_diff(demo_project_dir: Path) -> None:
    draft_path = demo_project_dir / "manuscript" / "draft.md"
    original = draft_path.read_text(encoding="utf-8")
    try:
        draft_path.write_text(
            original + "\n\nThe method significantly improved efficiency by 5%.\n",
            encoding="utf-8",
        )
        workflow_service.run_step("demo_project", "claim_alignment")
        workflow_service.run_step("demo_project", "reviewer")
        report = _read_json(demo_project_dir / "reviews" / "review_report.json")
        overclaim_issues = [
            issue for issue in report["sentence_issues"] if issue["issue_type"] == "overclaim"
        ]
        assert overclaim_issues
        diff = overclaim_issues[0]["revision_diff"]
        assert "significantly" not in diff["after"].lower()
        assert diff["requires_human_approval"] is True
    finally:
        draft_path.write_text(original, encoding="utf-8")
        workflow_service.run_step("demo_project", "claim_alignment")
        workflow_service.run_step("demo_project", "reviewer")


def test_revision_decision_api_records_without_modifying_draft(demo_project_dir: Path) -> None:
    client = TestClient(app)
    report = _read_json(demo_project_dir / "reviews" / "review_report.json")
    issue_id = report["sentence_issues"][0]["issue_id"]
    draft_path = demo_project_dir / "manuscript" / "draft.md"
    original_draft = draft_path.read_text(encoding="utf-8")

    response = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue_id}/decision",
        json={"decision": "accepted", "reason": "pytest v0.4 decision"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["issue_id"] == issue_id
    assert payload["decision"] == "accepted"
    assert payload["applied_to_manuscript"] is False
    assert draft_path.read_text(encoding="utf-8") == original_draft

    list_response = client.get("/api/projects/demo_project/review/revision-decisions")
    assert list_response.status_code == 200
    assert any(item["issue_id"] == issue_id for item in list_response.json())
