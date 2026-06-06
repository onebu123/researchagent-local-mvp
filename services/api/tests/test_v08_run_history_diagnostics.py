from __future__ import annotations

import json
from pathlib import Path

from app.tools.run_history import append_run_history, utc_now


def test_run_history_entries_include_failure_diagnostics(demo_project_dir: Path) -> None:
    start = utc_now()
    end = utc_now()

    record = append_run_history(
        demo_project_dir,
        "step",
        "analysis",
        "failed",
        start,
        end,
        [],
        errors=["pytest simulated failure"],
        warnings=[],
    )

    assert "failure_diagnostics" in record
    assert record["failure_diagnostics"]["failed_step"] == "analysis"
    assert record["recoverable"] is True
    assert record["retry_hint"] == "rerun_step"

    payload = json.loads((demo_project_dir / "runs" / "run_history.json").read_text(encoding="utf-8"))
    assert payload["runs"]
    assert all("failure_diagnostics" in item for item in payload["runs"])
    assert all("recoverable" in item for item in payload["runs"])
    assert all("retry_hint" in item for item in payload["runs"])

