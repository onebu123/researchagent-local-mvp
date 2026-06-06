from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from scripts.create_failure_fixture import create_failure_fixture


def test_run_history_failure_fixture_is_idempotent_and_visible_in_api(
    demo_project_dir: Path,
) -> None:
    first = create_failure_fixture("demo_project")
    second = create_failure_fixture("demo_project")
    assert first["run_id"] == "run_failure_fixture_001"
    assert second["run_id"] == first["run_id"]
    assert first["is_fixture"] is True

    client = TestClient(app)
    response = client.get("/api/projects/demo_project/runs")

    assert response.status_code == 200
    fixtures = [
        run
        for run in response.json()["runs"]
        if run.get("run_id") == "run_failure_fixture_001"
    ]
    assert len(fixtures) == 1
    assert fixtures[0]["status"] == "failed"
    assert fixtures[0]["failure_diagnostics"]["error_type"] == "missing_input"
    assert fixtures[0]["retry_hint"] == "rerun_step"
