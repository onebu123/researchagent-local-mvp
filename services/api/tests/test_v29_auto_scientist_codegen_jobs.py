from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.tools.auto_scientist.generated_code_revision import run_generated_code_revision_loop
from app.tools.auto_scientist.generated_code_sandbox import run_generated_code_experiment
from app.tools.auto_scientist.generated_code_review import read_generated_code_review_rounds, review_generated_code_result
from app.tools.job_manager import list_project_jobs, read_project_job
from app.tools.human_review_queue import build_human_review_queue
from app.tools.evidence_trust_package import build_evidence_trust_package


def test_generated_code_writer_strategy_writes_reviewable_proposal(demo_project_dir: Path) -> None:
    result = run_generated_code_experiment(
        demo_project_dir,
        "demo_project",
        "writer_run",
        "retrieval_ablation_exp",
        {
            "topic": "retrieval diagnostics",
            "research_question": "Can local passages support the project claim?",
            "generated_code_strategy": "retrieval_ablation",
            "generated_code_timeout_seconds": 5,
            "generated_code_max_memory_mb": 512,
        },
    )

    assert result["status"] == "completed"
    assert result["metrics"]["strategy"] == "retrieval_ablation"
    assert result["source_mode"] == "deterministic"
    assert result["approval_required"] is False

    proposal_path = demo_project_dir / "auto_scientist" / "generated_code" / "writer_run" / "retrieval_ablation_exp" / "code_proposal.json"
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    assert proposal["writer"]["strategy"] == "retrieval_ablation"
    assert proposal["static_scan"]["safe"] is True

    input_payload = json.loads((proposal_path.parent / "input.json").read_text(encoding="utf-8"))
    assert input_payload["source_passages"]
    assert input_payload["generated_code_strategy"] == "retrieval_ablation"


def test_generated_code_reviewer_classifies_static_scan_failure(demo_project_dir: Path) -> None:
    result = run_generated_code_experiment(
        demo_project_dir,
        "demo_project",
        "reviewer_run",
        "unsafe_exp",
        {
            "generated_source": "import os\nprint(os.getcwd())\n",
            "generated_code_source_mode": "deterministic",
        },
    )
    record = {
        "run_id": "reviewer_run",
        "experiment_id": "unsafe_exp",
        "template_name": "generated_code_smoke_test",
        "status": result["status"],
        "generated_code_execution": True,
        "result": result,
    }

    review = review_generated_code_result(demo_project_dir, "demo_project", "reviewer_run", record)

    assert result["status"] == "rejected_by_static_scan"
    assert review["failure_class"] == "static_scan_policy_violation"
    assert review["recommended_revision_strategy"] == "deterministic_safe_diagnostic_fallback"
    assert read_generated_code_review_rounds(demo_project_dir)


def test_revision_loop_records_code_review_rounds_and_safe_rerun(demo_project_dir: Path) -> None:
    failed_record = {
        "run_id": "review_revision_run",
        "experiment_id": "unsafe_exp_for_revision",
        "template_name": "generated_code_smoke_test",
        "status": "rejected_by_static_scan",
        "generated_code_execution": True,
        "arbitrary_code_execution": False,
        "result": {
            "status": "rejected_by_static_scan",
            "sandbox": {"static_scan": {"safe": False, "findings": ["forbidden import: os"]}},
        },
    }

    summary = run_generated_code_revision_loop(
        demo_project_dir,
        "demo_project",
        "review_revision_run",
        [failed_record],
        max_rounds=1,
        generated_code_timeout_seconds=5,
        generated_code_max_memory_mb=512,
    )

    assert summary["revision_count"] == 1
    assert summary["revision_results"][0]["status"] == "completed"
    assert summary["code_review_rounds_file"] == "auto_scientist/code_review_rounds.jsonl"
    review_rounds = read_generated_code_review_rounds(demo_project_dir)
    assert any(item.get("failure_class") == "static_scan_policy_violation" for item in review_rounds)


def test_auto_scientist_job_api_records_progress_and_logs(demo_project_dir: Path) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/jobs/auto-scientist/run",
        json={
            "topic": "job based auto scientist",
            "max_ideas": 1,
            "max_experiments_per_idea": 1,
            "write_paper": False,
            "export_latex": False,
            "allow_generated_code_experiments": True,
            "generated_code_strategy": "claim_support_matrix",
            "enable_generated_code_revision_loop": False,
        },
    )

    assert response.status_code == 200, response.text
    job = response.json()
    assert job["status"] == "completed"
    assert job["progress"] == 1.0
    assert job["job_type"] == "auto_scientist_run"
    assert job["result"]["run"]["generated_code_strategy"] == "claim_support_matrix"

    job_id = job["job_id"]
    assert client.get(f"/api/projects/demo_project/jobs/{job_id}").json()["job_id"] == job_id
    log_payload = client.get(f"/api/projects/demo_project/jobs/{job_id}/log").json()
    assert "auto scientist loop completed" in log_payload["content"]
    assert any(item["job_id"] == job_id for item in list_project_jobs("demo_project"))
    assert read_project_job("demo_project", job_id)["status"] == "completed"

    queue = build_human_review_queue(demo_project_dir, "demo_project")
    assert any(item["review_id"] == "auto_scientist_job_review" for item in queue["items"])


def test_trust_package_includes_jobs_and_code_review_rounds(demo_project_dir: Path) -> None:
    # Ensure the package sees v29 artifacts generated by earlier tests in this module.
    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    paths = {item["relative_path"] for item in package["files"]}
    assert "auto_scientist/code_review_rounds.jsonl" in paths
    assert "jobs/jobs.jsonl" in paths
    assert "jobs/latest_job.json" in paths
