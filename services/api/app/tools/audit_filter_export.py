from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import (
    ENTITY_TYPES,
    EVENT_CATEGORIES,
    RISK_LEVELS,
    append_audit_event,
    read_audit_log,
)
from app.tools.file_tools import ensure_dir, write_json, write_text


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def filtered_exports_dir(project_dir: Path) -> Path:
    return project_dir / "audit" / "filtered_exports"


def _safe_filtered_export_id(export_id: str) -> str:
    if not re.fullmatch(r"audit_filtered_export_\d{3,}", export_id):
        raise ValueError("invalid filtered audit export id")
    return export_id


def _next_filtered_export_paths(project_dir: Path) -> tuple[str, Path, Path]:
    ensure_dir(filtered_exports_dir(project_dir))
    numbers: list[int] = []
    for path in filtered_exports_dir(project_dir).glob("audit_filtered_export_*.json"):
        match = re.fullmatch(r"audit_filtered_export_(\d+)\.json", path.name)
        if match:
            numbers.append(int(match.group(1)))
    number = (max(numbers) + 1) if numbers else 1
    export_id = f"audit_filtered_export_{number:03d}"
    return (
        export_id,
        filtered_exports_dir(project_dir) / f"{export_id}.json",
        filtered_exports_dir(project_dir) / f"audit_filtered_report_{number:03d}.md",
    )


def _sanitize_export_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize_export_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_export_value(item) for item in value]
    if isinstance(value, str):
        if "sk_live_" in value or "api_key" in value.lower() or "api key" in value.lower():
            return "<secret_removed>"
        normalized = value.replace("\\", "/")
        if re.search(r"[A-Za-z]:/", normalized) or normalized.startswith("/"):
            return "<absolute_path_removed>"
        return normalized
    return value


def _validate_filters(filters: dict[str, Any]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    event_category = filters.get("event_category")
    if event_category is not None:
        if event_category not in EVENT_CATEGORIES:
            raise ValueError("event_category is not supported")
        cleaned["event_category"] = str(event_category)

    risk_level = filters.get("risk_level")
    if risk_level is not None:
        if risk_level not in RISK_LEVELS:
            raise ValueError("risk_level is not supported")
        cleaned["risk_level"] = str(risk_level)

    entity_type = filters.get("entity_type")
    if entity_type is not None:
        if entity_type not in ENTITY_TYPES:
            raise ValueError("entity_type is not supported")
        cleaned["entity_type"] = str(entity_type)

    entity_id = filters.get("entity_id")
    if entity_id is not None:
        entity_id_text = str(entity_id).strip()
        if not entity_id_text:
            raise ValueError("entity_id must not be empty")
        if "/" in entity_id_text or "\\" in entity_id_text or ".." in entity_id_text:
            raise ValueError("entity_id must be an identifier, not a path")
        cleaned["entity_id"] = entity_id_text
    return cleaned


def _entry_matches(entry: dict[str, Any], filters: dict[str, str]) -> bool:
    for key, expected in filters.items():
        if str(entry.get(key) or "") != expected:
            return False
    return True


def _build_markdown_report(
    project_id: str,
    export_id: str,
    filters: dict[str, str],
    entries: list[dict[str, Any]],
) -> str:
    lines = [
        "# Filtered Audit Report",
        "",
        f"Project: {project_id}",
        f"Export ID: {export_id}",
        f"Created entries matched: {len(entries)}",
        f"Filters: `{json.dumps(filters, ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Entries",
        "",
    ]
    if not entries:
        lines.append("No audit entries matched the selected filters.")
    for entry in entries:
        lines.append(
            f"- `{entry.get('audit_id')}` `{entry.get('event_category')}` "
            f"`{entry.get('risk_level')}` `{entry.get('entity_type')}` "
            f"`{entry.get('entity_id')}`: {entry.get('summary')}"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "This report is a local filtered audit view and is not a production-grade compliance export.",
        ]
    )
    return "\n".join(lines) + "\n"


def export_filtered_audit_log(
    project_dir: Path,
    project_id: str,
    filters: dict[str, Any],
) -> dict[str, Any]:
    cleaned_filters = _validate_filters(filters)
    entries = [
        entry for entry in read_audit_log(project_dir, limit=0) if _entry_matches(entry, cleaned_filters)
    ]
    sanitized_entries = _sanitize_export_value(entries)
    export_id, json_path, report_path = _next_filtered_export_paths(project_dir)
    payload = {
        "export_id": export_id,
        "created_at": _utc_now(),
        "source_file": "audit/audit_log.jsonl",
        "report_file": f"audit/filtered_exports/{report_path.name}",
        "filters": cleaned_filters,
        "matching_entry_count": len(sanitized_entries),
        "entries": sanitized_entries,
        "warnings": [],
    }
    write_json(json_path, payload)
    write_text(report_path, _build_markdown_report(project_id, export_id, cleaned_filters, sanitized_entries))
    append_audit_event(
        project_dir,
        project_id,
        "export_filtered_audit_log",
        "Filtered audit report was generated.",
        {
            "export_id": export_id,
            "filters": cleaned_filters,
            "matching_entry_count": len(sanitized_entries),
        },
        source="api",
        event_category="audit",
        risk_level="low",
        entity_type="audit_export",
        entity_id=export_id,
    )
    return payload


def list_filtered_audit_exports(project_dir: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(filtered_exports_dir(project_dir).glob("audit_filtered_export_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("export_id"):
            result.append(
                {
                    "export_id": payload.get("export_id"),
                    "created_at": payload.get("created_at"),
                    "source_file": payload.get("source_file"),
                    "report_file": payload.get("report_file"),
                    "filters": payload.get("filters") or {},
                    "matching_entry_count": payload.get("matching_entry_count", 0),
                }
            )
    return result


def load_filtered_audit_export(project_dir: Path, export_id: str) -> dict[str, Any]:
    safe_id = _safe_filtered_export_id(export_id)
    path = filtered_exports_dir(project_dir) / f"{safe_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"filtered audit export not found: {safe_id}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid filtered audit export JSON: {safe_id}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"invalid filtered audit export payload: {safe_id}")
    return payload


def load_filtered_audit_report(project_dir: Path, export_id: str) -> str:
    payload = load_filtered_audit_export(project_dir, export_id)
    report_file = str(payload.get("report_file") or "")
    report_name = Path(report_file).name
    if not report_name.startswith("audit_filtered_report_"):
        raise ValueError("invalid filtered audit report path")
    path = filtered_exports_dir(project_dir) / report_name
    if not path.exists():
        raise FileNotFoundError(f"filtered audit report not found: {export_id}")
    return path.read_text(encoding="utf-8")
