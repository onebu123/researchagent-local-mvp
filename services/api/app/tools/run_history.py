from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.file_tools import ensure_dir, write_json


def run_history_path(project_dir: Path) -> Path:
    return project_dir / "runs" / "run_history.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def read_run_history(project_dir: Path) -> dict[str, list[dict[str, Any]]]:
    path = run_history_path(project_dir)
    if not path.exists():
        return {"runs": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"runs": []}
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        return {"runs": []}
    return {"runs": [_with_diagnostics(item) for item in payload["runs"] if isinstance(item, dict)]}


def _empty_failure_diagnostics() -> dict[str, Any]:
    return {
        "error_type": None,
        "error_message": None,
        "failed_step": None,
        "likely_cause": None,
        "suggested_recovery": [],
    }


def _failure_diagnostics(
    status: str,
    step: str | None,
    errors: list[str],
) -> tuple[dict[str, Any], bool, str | None]:
    if status == "completed" and not errors:
        return _empty_failure_diagnostics(), True, None

    first_error = errors[0] if errors else "Unknown workflow error"
    failed_step = step or "workflow"
    diagnostics = {
        "error_type": "workflow_error",
        "error_message": first_error,
        "failed_step": failed_step,
        "likely_cause": (
            "A local workflow step returned an error. Check the failed_step output and rerun after "
            "fixing missing files or invalid inputs."
        ),
        "suggested_recovery": [
            "Inspect the project output files for the failed step.",
            "Fix missing or invalid local input files.",
            "Rerun the failed step or the full workflow after manual correction.",
        ],
    }
    retry_hint = "rerun_step" if step else "rerun_workflow"
    return diagnostics, True, retry_hint


def _with_diagnostics(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    if "failure_diagnostics" not in normalized or not isinstance(
        normalized.get("failure_diagnostics"), dict
    ):
        status = str(normalized.get("status") or "")
        errors = [
            str(item)
            for item in normalized.get("errors", [])
            if isinstance(item, str) and item
        ]
        diagnostics, recoverable, retry_hint = _failure_diagnostics(
            status,
            normalized.get("step") if isinstance(normalized.get("step"), str) else None,
            errors,
        )
        normalized["failure_diagnostics"] = diagnostics
        normalized["recoverable"] = recoverable
        normalized["retry_hint"] = retry_hint
    else:
        normalized.setdefault("recoverable", True)
        normalized.setdefault("retry_hint", None)
    return normalized


def append_run_history(
    project_dir: Path,
    run_type: str,
    step: str | None,
    status: str,
    start_time: str,
    end_time: str,
    outputs: list[str],
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    history = read_run_history(project_dir)
    start = parse_time(start_time)
    end = parse_time(end_time)
    diagnostics, recoverable, retry_hint = _failure_diagnostics(
        status,
        step,
        list(errors or []),
    )
    record = {
        "run_id": f"run_{len(history['runs']) + 1:04d}",
        "run_type": run_type,
        "step": step,
        "status": status,
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": round(max(0.0, (end - start).total_seconds()), 3),
        "outputs": outputs,
        "errors": list(errors or []),
        "warnings": list(warnings or []),
        "failure_diagnostics": diagnostics,
        "recoverable": recoverable,
        "retry_hint": retry_hint,
    }
    history["runs"].append(record)
    ensure_dir(run_history_path(project_dir).parent)
    write_json(run_history_path(project_dir), history)
    return record
