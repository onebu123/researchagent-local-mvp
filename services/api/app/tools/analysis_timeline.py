from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.analysis_compare import list_analysis_comparisons
from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.run_history import read_run_history


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def analysis_timeline_path(project_dir: Path) -> Path:
    return project_dir / "analysis" / "analysis_timeline.json"


def _comparison_summary(comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "parameters_changed": sum(
            int(item.get("summary", {}).get("parameters_changed") or 0)
            for item in comparisons
            if isinstance(item.get("summary"), dict)
        ),
        "input_hash_changed": any(
            item.get("summary", {}).get("input_hash_changed") is True
            for item in comparisons
            if isinstance(item.get("summary"), dict)
        ),
        "output_hash_changes": sum(
            int(item.get("summary", {}).get("output_hash_changes") or 0)
            for item in comparisons
            if isinstance(item.get("summary"), dict)
        ),
        "warnings_changed": sum(
            int(item.get("summary", {}).get("warnings_changed") or 0)
            for item in comparisons
            if isinstance(item.get("summary"), dict)
        ),
    }


def _change_summary(
    runs: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    changes_detected: int,
) -> dict[str, Any]:
    return {
        "runs_total": len(runs),
        "failed_runs": sum(1 for run in runs if run.get("status") == "failed"),
        "comparisons_total": len(comparisons),
        "comparisons_with_changes": changes_detected,
        "parameter_changes_total": sum(
            int(item.get("summary", {}).get("parameters_changed") or 0)
            for item in comparisons
            if isinstance(item.get("summary"), dict)
        ),
        "input_hash_changes_total": sum(
            1
            for item in comparisons
            if isinstance(item.get("summary"), dict)
            and item["summary"].get("input_hash_changed") is True
        ),
        "output_hash_changes_total": sum(
            int(item.get("summary", {}).get("output_hash_changes") or 0)
            for item in comparisons
            if isinstance(item.get("summary"), dict)
        ),
        "warning_changes_total": sum(
            int(item.get("summary", {}).get("warnings_changed") or 0)
            for item in comparisons
            if isinstance(item.get("summary"), dict)
        ),
    }


def _failed_run_diagnostics(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for run in runs:
        if run.get("status") != "failed":
            continue
        failure = run.get("failure_diagnostics")
        failure = failure if isinstance(failure, dict) else {}
        diagnostics.append(
            {
                "run_id": run.get("run_id"),
                "run_type": run.get("run_type"),
                "step": run.get("step"),
                "failed_step": failure.get("failed_step") or run.get("step"),
                "error_type": failure.get("error_type"),
                "error_message": failure.get("error_message"),
                "likely_cause": failure.get("likely_cause"),
                "suggested_recovery": failure.get("suggested_recovery") or [],
                "recoverable": run.get("recoverable"),
                "retry_hint": run.get("retry_hint"),
                "is_fixture": run.get("is_fixture") is True,
            }
        )
    return diagnostics


def generate_analysis_timeline(project_dir: Path, project_id: str) -> dict[str, Any]:
    run_history = read_run_history(project_dir)
    runs = [item for item in run_history.get("runs", []) if isinstance(item, dict)]
    comparisons = [
        item for item in list_analysis_comparisons(project_dir) if isinstance(item, dict)
    ]
    comparison_ids = [
        str(item.get("comparison_id"))
        for item in comparisons
        if isinstance(item.get("comparison_id"), str)
    ]

    timeline: list[dict[str, Any]] = []
    unlinked_comparisons: list[dict[str, Any]] = []
    if runs:
        latest_run = runs[-1]
        linked_comparisons = comparisons
        timeline.append(
            {
                "timeline_id": "analysis_timeline_001",
                "run_id": latest_run.get("run_id"),
                "analysis_provenance": "analysis/analysis_provenance.json",
                "comparison_ids": comparison_ids,
                "comparisons": linked_comparisons,
                "created_at": latest_run.get("end_time") or latest_run.get("start_time") or _utc_now(),
                "summary": _comparison_summary(linked_comparisons),
            }
        )
    else:
        unlinked_comparisons = comparisons

    changes_detected = sum(
        1
        for item in comparisons
        if isinstance(item.get("summary"), dict)
        and (
            int(item["summary"].get("parameters_changed") or 0) > 0
            or item["summary"].get("input_hash_changed") is True
            or int(item["summary"].get("output_hash_changes") or 0) > 0
            or int(item["summary"].get("warnings_changed") or 0) > 0
            or int(item["summary"].get("limitations_changed") or 0) > 0
        )
    )
    payload = {
        "generated_at": _utc_now(),
        "relative_path": "analysis/analysis_timeline.json",
        "timeline": timeline,
        "unlinked_comparisons": unlinked_comparisons,
        "change_summary": _change_summary(runs, comparisons, changes_detected),
        "failed_run_diagnostics": _failed_run_diagnostics(runs),
        "summary": {
            "runs": len(runs),
            "comparisons": len(comparisons),
            "changes_detected": changes_detected,
            "failed_runs": sum(1 for run in runs if run.get("status") == "failed"),
        },
    }
    write_json(analysis_timeline_path(project_dir), payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_analysis_timeline",
        "Analysis timeline was generated from run history and existing comparison files.",
        {
            "timeline_file": "analysis/analysis_timeline.json",
            "runs": len(runs),
            "comparisons": len(comparisons),
            "changes_detected": changes_detected,
        },
        source="api",
    )
    return payload


def generate_enhanced_analysis_timeline(project_dir: Path, project_id: str) -> dict[str, Any]:
    return generate_analysis_timeline(project_dir, project_id)
