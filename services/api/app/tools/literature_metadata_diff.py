from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.literature_index import literature_index_path, load_literature_index
from app.tools.metadata_history import read_metadata_history


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def metadata_diff_report_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "metadata_diff_report.json"


def metadata_review_batch_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "metadata_review_batch.json"


def _change_type(old_value: Any, new_value: Any) -> str:
    if old_value is None and new_value is not None:
        return "added"
    if old_value is not None and new_value is None:
        return "removed"
    if old_value != new_value:
        return "modified"
    return "unchanged"


def _revert_warning(field: str, revert_to: Any) -> str:
    if field == "doi":
        return "Reverting DOI may move this record away from verified-reference readiness."
    if field == "metadata_status":
        return "Reverting metadata_status is only a suggestion and must be applied manually."
    if field == "human_verified" and revert_to is not True:
        return "Reverting human verification may require a new manual review."
    return "Review the source history record before applying this revert manually."


def _build_revert_suggestion(field: str, old_value: Any) -> dict[str, Any]:
    return {
        "can_revert": True,
        "revert_to": old_value,
        "warning": _revert_warning(field, old_value),
    }


def generate_metadata_diff_report(
    project_dir: Path,
    project_id: str,
    *,
    write_audit: bool = True,
) -> dict[str, Any]:
    entries = load_literature_index(project_dir)
    valid_ids = {
        str(entry["literature_id"])
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("literature_id"), str)
    }
    grouped: dict[str, list[dict[str, Any]]] = {literature_id: [] for literature_id in valid_ids}

    for history in read_metadata_history(project_dir):
        literature_id = str(history.get("literature_id") or "")
        if literature_id not in valid_ids:
            continue
        old_values = history.get("old_values") if isinstance(history.get("old_values"), dict) else {}
        new_values = history.get("new_values") if isinstance(history.get("new_values"), dict) else {}
        changed_fields = [
            str(field)
            for field in history.get("changed_fields", [])
            if isinstance(field, str) and field
        ]
        for field in changed_fields:
            old_value = old_values.get(field)
            new_value = new_values.get(field)
            grouped.setdefault(literature_id, []).append(
                {
                    "field": field,
                    "old_value": old_value,
                    "new_value": new_value,
                    "change_type": _change_type(old_value, new_value),
                    "source_history_id": history.get("history_id"),
                    "revert_suggestion": _build_revert_suggestion(field, old_value),
                }
            )

    records: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        literature_id = str(entry.get("literature_id") or "")
        changes = grouped.get(literature_id, [])
        summary = {
            "added": sum(1 for change in changes if change["change_type"] == "added"),
            "modified": sum(1 for change in changes if change["change_type"] == "modified"),
            "removed": sum(1 for change in changes if change["change_type"] == "removed"),
        }
        records.append(
            {
                "literature_id": literature_id,
                "source_file": entry.get("source_file"),
                "title": entry.get("title"),
                "changes": changes,
                "summary": summary,
            }
        )

    report = {
        "generated_at": _utc_now(),
        "relative_path": "literature/metadata_diff_report.json",
        "records": records,
    }
    write_json(metadata_diff_report_path(project_dir), report)
    if write_audit:
        append_audit_event(
            project_dir,
            project_id,
            "generate_literature_metadata_diff",
            "Literature metadata field diff report was generated.",
            {
                "report_file": "literature/metadata_diff_report.json",
                "record_count": len(records),
                "change_count": sum(len(record["changes"]) for record in records),
            },
            source="api",
        )
    return report


def build_revert_suggestion(
    project_dir: Path,
    project_id: str,
    literature_id: str,
    field: str,
    source_history_id: str,
) -> dict[str, Any]:
    entries = load_literature_index(project_dir)
    if not any(
        isinstance(entry, dict) and entry.get("literature_id") == literature_id for entry in entries
    ):
        raise FileNotFoundError(f"literature_id not found: {literature_id}")

    for history in read_metadata_history(project_dir, literature_id):
        if history.get("history_id") != source_history_id:
            continue
        old_values = history.get("old_values") if isinstance(history.get("old_values"), dict) else {}
        new_values = history.get("new_values") if isinstance(history.get("new_values"), dict) else {}
        if field not in old_values and field not in new_values:
            raise ValueError("field is not present in the selected history record")
        suggestion = {
            "literature_id": literature_id,
            "field": field,
            "source_history_id": source_history_id,
            "old_value": old_values.get(field),
            "new_value": new_values.get(field),
            "change_type": _change_type(old_values.get(field), new_values.get(field)),
            "revert_suggestion": _build_revert_suggestion(field, old_values.get(field)),
            "applied": False,
            "literature_index_modified": False,
        }
        append_audit_event(
            project_dir,
            project_id,
            "suggest_literature_metadata_revert",
            "Literature metadata revert suggestion was generated without applying changes.",
            {
                "literature_id": literature_id,
                "field": field,
                "source_history_id": source_history_id,
                "literature_index_modified": False,
            },
            source="api",
        )
        return suggestion

    raise FileNotFoundError(f"metadata history record does not exist: {source_history_id}")


def _recommended_action(entry: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    status = entry.get("metadata_status")
    human_verified = entry.get("human_verified") is True
    if status == "verified" and human_verified:
        return "no_action", []
    if status == "placeholder":
        reasons.append("metadata_status is placeholder")
        return "manual_review_required", reasons
    if status == "verified" and not human_verified:
        reasons.append("verified metadata still lacks human_verified=true")
        return "human_verification_required", reasons
    reasons.append("metadata has not been manually verified")
    return "manual_review_recommended", reasons


def generate_metadata_review_batch(project_dir: Path, project_id: str) -> dict[str, Any]:
    entries = load_literature_index(project_dir)
    records: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        action, reasons = _recommended_action(entry)
        records.append(
            {
                "literature_id": entry.get("literature_id"),
                "title": entry.get("title"),
                "metadata_status": entry.get("metadata_status"),
                "human_verified": entry.get("human_verified") is True,
                "recommended_action": action,
                "reasons": reasons,
            }
        )

    summary = {
        "total_records": len(records),
        "placeholder": sum(1 for record in records if record["metadata_status"] == "placeholder"),
        "extracted": sum(1 for record in records if record["metadata_status"] == "extracted"),
        "verified": sum(1 for record in records if record["metadata_status"] == "verified"),
        "needs_review": sum(
            1 for record in records if record["recommended_action"] != "no_action"
        ),
    }
    payload = {
        "batch_id": "metadata_batch_001",
        "created_at": _utc_now(),
        "relative_path": "literature/metadata_review_batch.json",
        "source_index": "literature/literature_index.json",
        "literature_index_modified": False,
        "summary": summary,
        "records": records,
    }
    if not literature_index_path(project_dir).exists():
        raise FileNotFoundError("literature/literature_index.json does not exist")
    write_json(metadata_review_batch_path(project_dir), payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_literature_metadata_review_batch",
        "Literature metadata batch review report was generated without modifying metadata.",
        {
            "batch_id": payload["batch_id"],
            "total_records": summary["total_records"],
            "needs_review": summary["needs_review"],
            "literature_index_modified": False,
        },
        source="api",
    )
    return payload


def load_metadata_diff_report(project_dir: Path) -> dict[str, Any]:
    path = metadata_diff_report_path(project_dir)
    if not path.exists():
        raise FileNotFoundError("literature/metadata_diff_report.json does not exist")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("metadata_diff_report.json is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("metadata_diff_report.json must be an object")
    return payload

