from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json
from app.tools.literature_index import load_literature_index
from app.tools.metadata_history import read_metadata_history

ALLOWED_METADATA_REVIEW_ACTIONS = {
    "accept_change",
    "reject_change",
    "needs_verification",
    "request_revert",
}
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


def _actions_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "metadata_review_actions.jsonl"


def _summary_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "metadata_review_summary.json"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_metadata_review_actions(project_dir: Path) -> list[dict[str, Any]]:
    records = _read_jsonl(_actions_path(project_dir))
    for record in records:
        if "review_action_id" not in record and isinstance(record.get("action_id"), str):
            record["review_action_id"] = record["action_id"]
    return records


def _literature_exists(project_dir: Path, literature_id: str) -> bool:
    return any(
        isinstance(entry, dict) and entry.get("literature_id") == literature_id
        for entry in load_literature_index(project_dir)
    )


def _history_exists(project_dir: Path, literature_id: str, source_history_id: str) -> bool:
    return any(
        history.get("history_id") == source_history_id
        for history in read_metadata_history(project_dir, literature_id)
    )


def generate_metadata_review_summary(project_dir: Path) -> dict[str, Any]:
    actions = read_metadata_review_actions(project_dir)
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    counts: dict[tuple[str, str], int] = {}
    action_counts = {action: 0 for action in ALLOWED_METADATA_REVIEW_ACTIONS}
    for action in actions:
        action_value = action.get("action")
        if isinstance(action_value, str) and action_value in action_counts:
            action_counts[action_value] += 1
        key = (str(action.get("literature_id") or ""), str(action.get("field") or ""))
        counts[key] = counts.get(key, 0) + 1
        latest[key] = action

    records = [
        {
            "literature_id": literature_id,
            "field": field,
            "latest_action": record.get("action"),
            "review_count": counts[(literature_id, field)],
            "latest_reason": record.get("reason"),
            "source_history_id": record.get("source_history_id"),
        }
        for (literature_id, field), record in sorted(latest.items())
    ]
    payload = {
        "generated_at": _utc_now(),
        "relative_path": "literature/metadata_review_summary.json",
        "summary": {
            "total_actions": len(actions),
            "accept_change": action_counts["accept_change"],
            "reject_change": action_counts["reject_change"],
            "needs_verification": action_counts["needs_verification"],
            "request_revert": action_counts["request_revert"],
        },
        "records": records,
    }
    write_json(_summary_path(project_dir), payload)
    return payload


def record_metadata_review_action(
    project_dir: Path,
    project_id: str,
    literature_id: str,
    field: str,
    action: str,
    source_history_id: str,
    reason: str,
    *,
    source: str = "api",
) -> dict[str, Any]:
    clean_field = field.strip()
    clean_history_id = source_history_id.strip()
    if action not in ALLOWED_METADATA_REVIEW_ACTIONS:
        raise ValueError("invalid metadata review action")
    if clean_field not in EDITABLE_METADATA_FIELDS:
        raise ValueError("field is not editable literature metadata")
    if not clean_history_id.startswith("lit_hist_"):
        raise ValueError("source_history_id must start with lit_hist_")
    if not _literature_exists(project_dir, literature_id):
        raise FileNotFoundError(f"literature_id not found: {literature_id}")
    if not _history_exists(project_dir, literature_id, clean_history_id):
        raise FileNotFoundError(f"metadata history record does not exist: {clean_history_id}")

    records = read_metadata_review_actions(project_dir)
    action_id = f"metadata_review_{len(records) + 1:03d}"
    record = {
        "action_id": action_id,
        "review_action_id": action_id,
        "literature_id": literature_id,
        "field": clean_field,
        "action": action,
        "source_history_id": clean_history_id,
        "reason": reason,
        "created_at": _utc_now(),
        "source": source,
    }
    _append_jsonl(_actions_path(project_dir), record)
    summary = generate_metadata_review_summary(project_dir)
    append_audit_event(
        project_dir,
        project_id,
        "record_metadata_review_action",
        "Literature metadata review action was recorded without modifying literature_index.json.",
        {
            "action_id": record["action_id"],
            "review_action_id": record["review_action_id"],
            "literature_id": literature_id,
            "field": clean_field,
            "action": action,
            "source_history_id": clean_history_id,
            "literature_index_modified": False,
        },
        source=source,
    )
    return {**record, "summary": summary, "literature_index_modified": False}
