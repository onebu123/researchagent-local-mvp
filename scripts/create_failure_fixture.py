from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.services.storage_service import storage_service
from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json
from app.tools.run_history import run_history_path, utc_now


def _read_history(path: Path) -> dict[str, list[dict]]:
    if not path.exists():
        return {"runs": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"runs": []}
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        return {"runs": []}
    return {"runs": [item for item in payload["runs"] if isinstance(item, dict)]}


def create_failure_fixture(project_id: str = "demo_project") -> dict:
    project_dir = storage_service.ensure_project_structure(project_id)
    path = run_history_path(project_dir)
    history = _read_history(path)
    existing = next(
        (run for run in history["runs"] if run.get("run_id") == "run_failure_fixture_001"),
        None,
    )
    if existing:
        return existing

    end_time = utc_now()
    start_time = (datetime.fromisoformat(end_time) - timedelta(seconds=2)).isoformat()
    record = {
        "run_id": "run_failure_fixture_001",
        "run_type": "step",
        "step": "analysis",
        "status": "failed",
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": 2.0,
        "outputs": [],
        "errors": ["Fixture failure: missing input file data/missing_fixture.csv."],
        "warnings": ["This failed run is an explicit v0.10 fixture."],
        "failure_diagnostics": {
            "error_type": "missing_input",
            "error_message": "data/missing_fixture.csv does not exist.",
            "failed_step": "analysis",
            "likely_cause": "A required local CSV input was missing for the analysis step.",
            "suggested_recovery": [
                "Upload or regenerate the missing CSV file.",
                "Rerun the analysis step after the local input exists.",
            ],
        },
        "recoverable": True,
        "retry_hint": "rerun_step",
        "is_fixture": True,
    }
    history["runs"].append(record)
    ensure_dir(path.parent)
    write_json(path, history)
    append_audit_event(
        project_dir,
        project_id,
        "create_run_history_failure_fixture",
        "Run history failure fixture was created for local diagnostics testing.",
        {
            "run_id": record["run_id"],
            "status": record["status"],
            "failed_step": "analysis",
            "is_fixture": True,
        },
        source="script",
        event_category="analysis",
        risk_level="low",
        entity_type="analysis",
        entity_id=record["run_id"],
    )
    return record


def main() -> None:
    project_id = sys.argv[1] if len(sys.argv) > 1 else "demo_project"
    record = create_failure_fixture(project_id)
    print(f"Created or reused failure fixture: {record['run_id']}")


if __name__ == "__main__":
    main()
