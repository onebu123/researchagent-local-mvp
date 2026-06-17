from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.tools.auto_scientist.generated_code_approval import list_generated_code_proposals, record_generated_code_approval
from app.tools.auto_scientist.generated_code_sandbox import run_generated_code_experiment


def test_generated_code_proposal_listing_supports_ui_review(demo_project_dir: Path) -> None:
    result = run_generated_code_experiment(
        demo_project_dir,
        "demo_project",
        "ui_review_run",
        "ui_generated_exp",
        {
            "topic": "ui review gate",
            "research_question": "Can the frontend inspect generated-code proposals?",
            "generated_code_source_mode": "deterministic",
            "generated_code_requires_approval": True,
            "generated_code_strategy": "claim_support_matrix",
            "generated_code_timeout_seconds": 5,
            "generated_code_max_memory_mb": 512,
        },
    )

    assert result["status"] == "pending_human_approval"
    proposals = list_generated_code_proposals(demo_project_dir)
    proposal = next(item for item in proposals if item["experiment_id"] == "ui_generated_exp")

    assert proposal["source_hash"] == result["source_hash"]
    assert proposal["static_scan_safe"] is True
    assert proposal["approval_decision"] is None
    assert "source_excerpt" in proposal
    assert proposal["relative_path"].endswith("code_proposal.json")

    record_generated_code_approval(
        demo_project_dir,
        "demo_project",
        "ui_review_run",
        "ui_generated_exp",
        "approved",
        "frontend user reviewed static scan and source hash",
        source_hash=result["source_hash"],
    )
    proposals_after = list_generated_code_proposals(demo_project_dir)
    approved = next(item for item in proposals_after if item["experiment_id"] == "ui_generated_exp")
    assert approved["approval_decision"] == "approved"


def test_generated_code_proposals_api_returns_reviewable_records(demo_project_dir: Path) -> None:
    client = TestClient(app)
    response = client.get("/api/projects/demo_project/auto-scientist/generated-code/proposals")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, list)
    if payload:
        item = payload[0]
        assert "run_id" in item
        assert "experiment_id" in item
        assert "source_hash" in item
        assert "static_scan_safe" in item
        assert "relative_path" in item
