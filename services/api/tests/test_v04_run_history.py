from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.services.workflow_service import workflow_service
from main import app


def test_run_history_records_completed_workflow(demo_project_dir: Path) -> None:
    history_path = demo_project_dir / "runs" / "run_history.json"
    history = json.loads(history_path.read_text(encoding="utf-8"))
    runs = history["runs"]

    assert runs
    assert any(run["run_type"] == "workflow" and run["status"] == "completed" for run in runs)
    for run in runs:
        assert run["run_id"].startswith("run_")
        assert "duration_seconds" in run
        assert isinstance(run["outputs"], list)
        assert isinstance(run["errors"], list)
        assert isinstance(run["warnings"], list)


def test_run_history_records_step_runs(demo_project_dir: Path) -> None:
    workflow_service.run_step("demo_project", "reviewer")
    history = json.loads((demo_project_dir / "runs" / "run_history.json").read_text(encoding="utf-8"))

    assert any(
        run["run_type"] == "step" and run["step"] == "reviewer" and run["status"] == "completed"
        for run in history["runs"]
    )


def test_run_history_api_returns_runs() -> None:
    client = TestClient(app)
    response = client.get("/api/projects/demo_project/runs")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["runs"], list)
    assert payload["runs"]
