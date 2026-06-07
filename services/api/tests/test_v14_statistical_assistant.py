from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.tools.statistical_assistant import generate_statistical_assistant_report
from main import app


def test_statistical_assistant_generates_report_and_notes(demo_project_dir: Path) -> None:
    report = generate_statistical_assistant_report(demo_project_dir, "demo_project")

    assert report["report_id"] == "statistical_assistant_001"
    assert report["dataset"]["row_count"] > 0
    assert "temperature" in report["dataset"]["numeric_columns"]
    assert report["variable_roles"]
    assert report["descriptive_cards"]
    assert report["method_suggestions"]
    assert report["data_health"]["missing_value_columns"] >= 0
    assert report["data_health"]["outlier_flagged_columns"] >= 0
    assert report["limitations"]
    assert (demo_project_dir / "analysis" / "statistical_assistant_report.json").exists()
    assert (demo_project_dir / "analysis" / "statistical_assistant_notes.md").exists()


def test_statistical_assistant_api_contracts(demo_project_dir: Path) -> None:
    client = TestClient(app)

    generated = client.post("/api/projects/demo_project/analysis/statistical-assistant/generate")
    assert generated.status_code == 200
    assert generated.json()["relative_path"] == "analysis/statistical_assistant_report.json"

    fetched = client.get("/api/projects/demo_project/analysis/statistical-assistant")
    assert fetched.status_code == 200
    payload = fetched.json()
    assert payload["report_id"] == "statistical_assistant_001"
    assert payload["source_files"]["summary"] == "analysis/result_summary.json"
    assert payload["source_files"]["processed_data"] == "analysis/processed_data.csv"


def test_statistical_assistant_records_only_relative_paths(demo_project_dir: Path) -> None:
    report = generate_statistical_assistant_report(demo_project_dir, "demo_project")
    payload = str(report)

    assert str(demo_project_dir) not in payload
    assert "analysis/result_summary.json" in payload
    assert "analysis/processed_data.csv" in payload
