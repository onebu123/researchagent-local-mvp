from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from main import app
from app.tools.evidence_trust_package import build_evidence_trust_package
from app.tools.job_manager import (
    read_project_job,
    request_project_job_cancel,
    start_project_job_background,
)


def _wait_for_terminal(project_id: str, job_id: str, timeout_seconds: float = 5.0) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last = read_project_job(project_id, job_id)
    while time.time() < deadline:
        last = read_project_job(project_id, job_id)
        if last.get("status") in {"completed", "failed", "cancelled"}:
            return last
        time.sleep(0.05)
    return last


def test_background_job_contract_records_progress_and_terminal_state(demo_project_dir: Path) -> None:
    def runner(update):
        update("step one", 0.25)
        time.sleep(0.05)
        update("step two", 0.75)
        return {"run": {"manuscript_file": "manuscript/demo.md"}}

    job = start_project_job_background("demo_project", "unit_background_job", {"secret_token": "should-redact"}, runner)

    assert job["status"] in {"queued", "running", "completed"}
    assert job["payload"]["secret_token"] == "[redacted]"
    final = _wait_for_terminal("demo_project", job["job_id"])
    assert final["status"] == "completed"
    assert final["progress"] == 1.0
    assert final["outputs"] == ["manuscript/demo.md"]
    assert (demo_project_dir / "jobs" / f"{job['job_id']}.log").exists()


def test_background_job_cancel_is_cooperative_and_auditable(demo_project_dir: Path) -> None:
    def runner(update):
        update("before cancellable checkpoint", 0.2)
        time.sleep(0.15)
        update("after cancellable checkpoint", 0.5)
        return {"run": {}}

    job = start_project_job_background("demo_project", "unit_cancellable_job", {}, runner)
    cancel_record = request_project_job_cancel("demo_project", job["job_id"], reason="test cancellation")

    assert cancel_record["cancel_requested"] is True
    assert (demo_project_dir / "jobs" / f"{job['job_id']}.cancel.json").exists()
    final = _wait_for_terminal("demo_project", job["job_id"])
    assert final["status"] in {"cancelled", "completed"}
    assert final["cancel_requested"] is True


def test_jobs_api_start_cancel_and_log_contract(demo_project_dir: Path) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/jobs/auto-scientist/start",
        json={
            "topic": "async job contract",
            "max_ideas": 1,
            "max_experiments_per_idea": 1,
            "write_paper": False,
            "export_latex": False,
            "allow_generated_code_experiments": False,
            "enable_experiment_tree_search": False,
        },
    )

    assert response.status_code == 200, response.text
    job = response.json()
    assert job["execution_mode"] == "background"
    job_id = job["job_id"]

    cancel = client.post(f"/api/projects/demo_project/jobs/{job_id}/cancel", json={"reason": "contract test"})
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["cancel_requested"] is True

    final = _wait_for_terminal("demo_project", job_id, timeout_seconds=10)
    assert final["job_id"] == job_id
    log_payload = client.get(f"/api/projects/demo_project/jobs/{job_id}/log")
    assert log_payload.status_code == 200, log_payload.text
    assert "cancellation" in log_payload.json()["content"] or final["status"] == "completed"

    jobs = client.get("/api/projects/demo_project/jobs?limit=5").json()
    assert any(item["job_id"] == job_id for item in jobs)


def test_trust_package_includes_individual_job_artifacts(demo_project_dir: Path) -> None:
    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    paths = {item["relative_path"] for item in package["files"]}
    assert any(path.startswith("jobs/job_") and path.endswith(".json") for path in paths)
    assert any(path.startswith("jobs/job_") and path.endswith(".log") for path in paths)
