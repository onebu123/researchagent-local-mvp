from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.tools.auto_scientist.phase_gates import PHASE_GATES_JSON
from app.tools.auto_scientist.scientist_loop import run_auto_scientist
from app.tools.evidence_trust_package import build_evidence_trust_package
from app.tools.human_review_queue import DECISIONS_FILE, QUEUE_FILE, build_human_review_queue


def _clear_phase_gate_state(project_dir: Path) -> None:
    for relative_path in [PHASE_GATES_JSON, DECISIONS_FILE, QUEUE_FILE]:
        (project_dir / relative_path).unlink(missing_ok=True)


def test_auto_scientist_default_copilot_mode_remains_completed(demo_project_dir: Path) -> None:
    _clear_phase_gate_state(demo_project_dir)

    payload = run_auto_scientist(
        "demo_project",
        topic="default copilot off",
        max_ideas=1,
        max_experiments_per_idea=1,
        write_paper=False,
        export_latex=False,
    )

    assert payload["run"]["status"] == "completed"
    assert payload["run"]["copilot_mode"] == "off"
    assert payload["phase_gates"] == {}


def test_advisory_copilot_phase_gates_do_not_block(demo_project_dir: Path) -> None:
    _clear_phase_gate_state(demo_project_dir)

    payload = run_auto_scientist(
        "demo_project",
        topic="advisory phase gates",
        max_ideas=1,
        max_experiments_per_idea=1,
        write_paper=False,
        export_latex=False,
        copilot_mode="advisory",
    )

    assert payload["run"]["status"] == "completed"
    gates = payload["phase_gates"]
    assert gates["copilot_mode"] == "advisory"
    assert gates["status"] == "advisory"
    assert gates["summary"]["total"] == 2
    assert gates["summary"]["blocking_pending"] == 0

    queue = build_human_review_queue(demo_project_dir, "demo_project")
    review_ids = {item["review_id"] for item in queue["items"] if item["review_type"] == "auto_scientist_phase_gate"}
    assert {"auto_scientist_phase_gate_ideas", "auto_scientist_phase_gate_experiment_plan"}.issubset(review_ids)


def test_strict_copilot_phase_gate_blocks_and_resumes_after_decisions(demo_project_dir: Path) -> None:
    _clear_phase_gate_state(demo_project_dir)
    client = TestClient(app)

    blocked = client.post(
        "/api/projects/demo_project/auto-scientist/run",
        json={
            "topic": "strict phase gates",
            "max_ideas": 1,
            "max_experiments_per_idea": 1,
            "write_paper": False,
            "export_latex": False,
            "copilot_mode": "strict",
        },
    )

    assert blocked.status_code == 200, blocked.text
    blocked_payload = blocked.json()
    assert blocked_payload["run"]["status"] == "awaiting_human_review"
    assert blocked_payload["awaiting_human_review"] is True
    assert blocked_payload["phase_gates"]["blocking_gate"]["phase"] == "ideas"
    gate_review_ids = [gate["review_id"] for gate in blocked_payload["phase_gates"]["gates"]]

    phase_gates_response = client.get("/api/projects/demo_project/auto-scientist/phase-gates")
    assert phase_gates_response.status_code == 200, phase_gates_response.text
    assert phase_gates_response.json()["relative_path"] == PHASE_GATES_JSON

    for review_id in gate_review_ids:
        decision = client.post(
            f"/api/projects/demo_project/human-review-queue/{review_id}/decision",
            json={"decision": "approved", "reason": "unit test approves local phase gate"},
        )
        assert decision.status_code == 200, decision.text

    resumed = client.post(
        "/api/projects/demo_project/auto-scientist/run",
        json={
            "topic": "strict phase gates",
            "max_ideas": 1,
            "max_experiments_per_idea": 1,
            "write_paper": False,
            "export_latex": False,
            "copilot_mode": "strict",
        },
    )

    assert resumed.status_code == 200, resumed.text
    resumed_payload = resumed.json()
    assert resumed_payload["run"]["status"] == "completed"
    assert resumed_payload["phase_gates"]["summary"]["approved"] == len(gate_review_ids)


def test_trust_package_includes_phase_gate_artifact(demo_project_dir: Path) -> None:
    _clear_phase_gate_state(demo_project_dir)
    run_auto_scientist(
        "demo_project",
        topic="phase gates trust package",
        max_ideas=1,
        max_experiments_per_idea=1,
        write_paper=False,
        export_latex=False,
        copilot_mode="advisory",
    )

    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    paths = {item["relative_path"] for item in package["files"]}
    assert PHASE_GATES_JSON in paths
