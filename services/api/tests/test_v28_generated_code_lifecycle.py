from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.tools.auto_scientist.generated_code_approval import record_generated_code_approval
from app.tools.auto_scientist.generated_code_revision import run_generated_code_revision_loop
from app.tools.auto_scientist.generated_code_sandbox import GENERATED_CODE_TEMPLATE, run_generated_code_experiment
from app.tools.auto_scientist.scientist_loop import run_auto_scientist
from app.tools.human_review_queue import build_human_review_queue


def test_llm_generated_code_candidate_requires_approval_before_execution(demo_project_dir: Path) -> None:
    result = run_generated_code_experiment(
        demo_project_dir,
        "demo_project",
        "approval_run",
        "approval_exp_001",
        {
            "topic": "approval gate",
            "research_question": "Can generated code be gated?",
            "generated_code_source_mode": "mock_llm",
            "generated_code_timeout_seconds": 5,
            "generated_code_max_memory_mb": 512,
        },
    )

    assert result["status"] == "pending_human_approval"
    assert result["generated_code_execution"] is True
    assert result["arbitrary_code_execution"] is False
    assert result["source_mode"] == "mock_llm"
    assert result["approval_required"] is True
    assert result["source_hash"]
    proposal = demo_project_dir / "auto_scientist" / "generated_code" / "approval_run" / "approval_exp_001" / "code_proposal.json"
    assert proposal.exists()

    record_generated_code_approval(
        demo_project_dir,
        "demo_project",
        "approval_run",
        "approval_exp_001",
        "approved",
        "reviewed safe fallback source for test",
        source_hash=result["source_hash"],
    )
    approved_result = run_generated_code_experiment(
        demo_project_dir,
        "demo_project",
        "approval_run",
        "approval_exp_001",
        {
            "topic": "approval gate",
            "research_question": "Can generated code be gated?",
            "generated_code_source_mode": "mock_llm",
            "generated_code_timeout_seconds": 5,
            "generated_code_max_memory_mb": 512,
        },
    )

    assert approved_result["status"] == "completed"
    assert approved_result["approval_required"] is True
    assert approved_result["source_hash"] == result["source_hash"]


def test_docker_image_allowlist_blocks_unapproved_images_before_docker_execution(demo_project_dir: Path, monkeypatch) -> None:
    # Even if docker were installed, the image policy should reject this image first.
    monkeypatch.setattr("app.tools.auto_scientist.generated_code_sandbox.shutil.which", lambda _name: "/usr/bin/docker")
    result = run_generated_code_experiment(
        demo_project_dir,
        "demo_project",
        "allowlist_run",
        "allowlist_exp_001",
        {
            "topic": "docker image policy",
            "research_question": "Should non-allowlisted images be rejected?",
            "generated_code_sandbox_mode": "docker",
            "generated_code_docker_image": "untrusted/python:latest",
            "generated_code_timeout_seconds": 5,
            "generated_code_max_memory_mb": 512,
        },
    )

    assert result["status"] == "docker_unavailable"
    sandbox = result["sandbox"]
    assert sandbox["docker_image_allowed"] is False
    assert "not allowed" in sandbox["docker_unavailable_reason"]
    assert (demo_project_dir / "auto_scientist" / "docker_image_policy.json").exists()


def test_generated_code_revision_loop_reruns_safe_diagnostic_after_failure(demo_project_dir: Path) -> None:
    failed_record = {
        "run_id": "revision_run",
        "experiment_id": "generated_failure",
        "template_name": GENERATED_CODE_TEMPLATE,
        "status": "failed",
        "generated_code_execution": True,
        "arbitrary_code_execution": False,
        "result": {"status": "failed", "metrics": {}, "claims": []},
    }
    summary = run_generated_code_revision_loop(
        demo_project_dir,
        "demo_project",
        "revision_run",
        [failed_record],
        max_rounds=1,
        generated_code_timeout_seconds=5,
        generated_code_max_memory_mb=512,
    )

    assert summary["revision_count"] == 1
    assert summary["revision_results"][0]["status"] == "completed"
    assert (demo_project_dir / "auto_scientist" / "code_revision_rounds.jsonl").exists()


def test_auto_scientist_run_can_gate_then_revise_generated_code(demo_project_dir: Path) -> None:
    payload = run_auto_scientist(
        "demo_project",
        topic="generated-code approval and revision",
        max_ideas=1,
        max_experiments_per_idea=1,
        write_paper=False,
        export_latex=False,
        allow_generated_code_experiments=True,
        generated_code_source_mode="mock_llm",
        generated_code_requires_approval=True,
        enable_generated_code_revision_loop=True,
        generated_code_revision_rounds=1,
    )

    assert payload["run"]["generated_code_source_mode"] == "mock_llm"
    assert payload["run"]["generated_code_revision_loop_enabled"] is True
    assert payload["generated_code_revision"]["revision_count"] >= 1
    statuses = {item["status"] for item in payload["experiment_results"] if item.get("generated_code_execution")}
    assert "pending_human_approval" in statuses
    assert "completed" in statuses

    queue = build_human_review_queue(demo_project_dir, "demo_project")
    review_ids = {item["review_id"] for item in queue["items"]}
    assert any(item.startswith("auto_scientist_code_approval_") for item in review_ids)
    assert "auto_scientist_code_revision_review" in review_ids


def test_generated_code_approval_api_records_decision(demo_project_dir: Path) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/auto-scientist/generated-code/approvals",
        json={
            "run_id": "api_approval_run",
            "experiment_id": "api_exp",
            "source_hash": "abc123",
            "decision": "approved",
            "reason": "local test approval",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["decision"] == "approved"
    assert payload["source_hash"] == "abc123"

    list_response = client.get("/api/projects/demo_project/auto-scientist/generated-code/approvals")
    assert list_response.status_code == 200
    assert any(item.get("approval_id") == payload["approval_id"] for item in list_response.json())
