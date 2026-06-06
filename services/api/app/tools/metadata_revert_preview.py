from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.literature_index import load_literature_index
from app.tools.metadata_history import read_metadata_history

EDITABLE_METADATA_FIELDS = {
    "title",
    "authors",
    "year",
    "doi",
    "journal",
    "metadata_status",
    "human_verified",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_preview_path(project_dir: Path) -> tuple[str, Path]:
    numbers: list[int] = []
    for path in (project_dir / "literature").glob("metadata_revert_preview_*.json"):
        match = re.fullmatch(r"metadata_revert_preview_(\d+)\.json", path.name)
        if match:
            numbers.append(int(match.group(1)))
    number = (max(numbers) + 1) if numbers else 1
    preview_id = f"metadata_revert_preview_{number:03d}"
    return preview_id, project_dir / "literature" / f"{preview_id}.json"


def _warning(field: str, current_entry: dict[str, Any], revert_to: Any) -> str | None:
    if field == "doi":
        return "Reverting DOI may move this record away from verified-reference readiness."
    if field == "metadata_status":
        return "metadata_status changes affect readiness checks and must be applied manually."
    if field == "human_verified" and revert_to is not True:
        return "Reverting human_verified away from true requires another manual review."
    if current_entry.get("metadata_status") == "verified" or current_entry.get("human_verified") is True:
        return "This record has verified-reference fields; review carefully before applying manually."
    return None


def generate_metadata_revert_execution_preview(
    project_dir: Path,
    project_id: str,
    literature_id: str,
    field: str,
    source_history_id: str,
) -> dict[str, Any]:
    clean_field = field.strip()
    clean_history_id = source_history_id.strip()
    if clean_field not in EDITABLE_METADATA_FIELDS:
        raise ValueError("field is not editable literature metadata")
    if not clean_history_id.startswith("lit_hist_"):
        raise ValueError("source_history_id must start with lit_hist_")

    entries = load_literature_index(project_dir)
    current_entry = next(
        (entry for entry in entries if isinstance(entry, dict) and entry.get("literature_id") == literature_id),
        None,
    )
    if current_entry is None:
        raise FileNotFoundError(f"literature_id not found: {literature_id}")

    history = next(
        (
            record
            for record in read_metadata_history(project_dir, literature_id)
            if record.get("history_id") == clean_history_id
        ),
        None,
    )
    if history is None:
        raise FileNotFoundError(f"metadata history record does not exist: {clean_history_id}")

    old_values = history.get("old_values") if isinstance(history.get("old_values"), dict) else {}
    new_values = history.get("new_values") if isinstance(history.get("new_values"), dict) else {}
    if clean_field not in old_values and clean_field not in new_values:
        raise ValueError("field is not present in the selected history record")

    current_value = current_entry.get(clean_field)
    revert_to = old_values.get(clean_field)
    conflicts: list[dict[str, Any]] = []
    warning = _warning(clean_field, current_entry, revert_to)
    if warning:
        conflicts.append({"field": clean_field, "severity": "warning", "message": warning})

    preview_id, path = _next_preview_path(project_dir)
    payload = {
        "preview_id": preview_id,
        "generated_at": _utc_now(),
        "relative_path": f"literature/{preview_id}.json",
        "literature_id": literature_id,
        "field": clean_field,
        "source_history_id": clean_history_id,
        "current_value": current_value,
        "revert_to": revert_to,
        "history_new_value": new_values.get(clean_field),
        "would_change": current_value != revert_to,
        "safe_to_apply": True,
        "conflicts": conflicts,
        "applied": False,
        "literature_index_modified": False,
        "notes": ["Preview only. No changes were applied to literature_index.json."],
    }
    write_json(path, payload)
    append_audit_event(
        project_dir,
        project_id,
        "preview_literature_metadata_revert_execution",
        "Literature metadata revert execution preview was generated without applying changes.",
        {
            "preview_id": preview_id,
            "literature_id": literature_id,
            "field": clean_field,
            "source_history_id": clean_history_id,
            "literature_index_modified": False,
        },
        source="api",
        event_category="trust",
        risk_level="medium",
        entity_type="metadata_revert_preview",
        entity_id=preview_id,
    )
    return payload
