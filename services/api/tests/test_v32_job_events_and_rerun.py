from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from main import app
from app.tools.auto_scientist.generated_code_approval import record_generated_code_approval
from app.tools.auto_scientist.generated_code_sandbox import run_generated_code_experiment
from app.tools.evidence_trust_package import build_evidence_trust_package
from app.tools.job_manager import read_project_job, read_project_job_events, start_project_job_background


def _wait_for_terminal(project_id: str, job_id: str, timeout_seconds: float = 5.0) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last = read_project_job(project_id, job_id)
    while time.time() < deadline:
        last = read_project_job(project_id, job_id)
        if last.get("status") in {"completed", "failed", "cancelled"}:
            return last
        time.sleep(0.05)
    return last


def test_job_event_timeline_and_sse_contract(demo_project_dir: Path) -> None:
    def runner(update):
        update("timeline step one", 0.25)
        update("timeline step two", 0.75)
        return {"run": {"manuscript_file": "manuscript/evented.md"}}

    job = start_project_job_background("demo_project", "unit_event_timeline", {}, runner)
    final = _wait_for_terminal("demo_project", job["job_id"])
    assert final["status"] == "completed"

    events_payload = read_project_job_events("demo_project", job["job_id"])
    events = events_payload["events"]
    assert events_payload["events_file"].endswith(".events.jsonl")
    assert [event["sequence"] for event in events] == sorted(event["sequence"] for event in events)
    assert any(event["event_type"] == "created" for event in events)
    assert any(event["event_type"] == "progress" and event["message"] == "timeline step two" for event in events)
    assert events[-1]["event_type"] == "terminal"

    client = TestClient(app)
    response = client.get(f"/api/projects/demo_project/jobs/{job['job_id']}/events")
    assert response.status_code == 200, response.text
    assert response.json()["latest_sequence"] >= 3

    stream = client.get(f"/api/projects/demo_project/jobs/{job['job_id']}/events/stream?max_events=20")
    assert stream.status_code == 200, stream.text
    assert "text/event-stream" in stream.headers.get("content-type", "")
    assert "event: progress" in stream.text or "event: terminal" in stream.text


def test_auto_scientist_job_events_include_loop_checkpoints(demo_project_dir: Path) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/jobs/auto-scientist/start",
        json={
            "topic": "job event callbacks",
            "research_question": "Do job events expose Auto Scientist checkpoints?",
            "max_ideas": 1,
            "max_experiments_per_idea": 1,
            "write_paper": False,
            "export_latex": False,
            "allow_generated_code_experiments": False,
            "enable_experiment_tree_search": False,
        },
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["job_id"]
    final = _wait_for_terminal("demo_project", job_id, timeout_seconds=15)
    assert final["status"] == "completed"
    events = read_project_job_events("demo_project", job_id)["events"]
    messages = [str(event.get("message")) for event in events]
    assert any("auto scientist: generating ideas" in message for message in messages)
    assert any("auto scientist: analyzing experiment results" in message for message in messages)


def test_approved_generated_code_proposal_can_rerun_via_api(demo_project_dir: Path) -> None:
    initial = run_generated_code_experiment(
        demo_project_dir,
        "demo_project",
        "rerun_ui_run",
        "rerun_generated_exp",
        {
            "topic": "rerun approved generated code",
            "research_question": "Can approved generated-code proposals be rerun?",
            "generated_code_source_mode": "deterministic",
            "generated_code_requires_approval": True,
            "generated_code_strategy": "lexical_diagnostics",
            "generated_code_timeout_seconds": 5,
            "generated_code_max_memory_mb": 512,
        },
    )
    assert initial["status"] == "pending_human_approval"
    record_generated_code_approval(
        demo_project_dir,
        "demo_project",
        "rerun_ui_run",
        "rerun_generated_exp",
        "approved",
        "static scan and source hash reviewed",
        source_hash=initial["source_hash"],
    )

    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/auto-scientist/generated-code/rerun",
        json={
            "run_id": "rerun_ui_run",
            "experiment_id": "rerun_generated_exp",
            "source_hash": initial["source_hash"],
            "sandbox_mode": "subprocess",
            "timeout_seconds": 5,
            "max_memory_mb": 512,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["rerun"]["status"] in {"completed", "failed", "timeout"}
    assert payload["rerun"]["source_hash"] == initial["source_hash"]
    assert (demo_project_dir / "auto_scientist" / "generated_code_reruns.jsonl").exists()


def test_trust_package_includes_job_events_and_generated_code_reruns(demo_project_dir: Path) -> None:
    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    paths = {item["relative_path"] for item in package["files"]}
    assert any(path.startswith("jobs/job_") and path.endswith(".events.jsonl") for path in paths)
    assert "auto_scientist/generated_code_reruns.jsonl" in paths
