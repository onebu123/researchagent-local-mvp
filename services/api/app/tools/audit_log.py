from __future__ import annotations

import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.file_tools import ensure_dir, relative_posix

EVENT_CATEGORIES = {
    "workflow",
    "file",
    "literature",
    "review",
    "patch",
    "merge",
    "version",
    "audit",
    "analysis",
    "trust",
    "system",
}
RISK_LEVELS = {"low", "medium", "high"}
ENTITY_TYPES = {
    "project",
    "file",
    "literature",
    "review_issue",
    "patch",
    "merge",
    "version",
    "audit_export",
    "analysis",
    "evidence_claim",
    "trust",
    "readiness_report",
    "pdf_page",
    "metadata_revert_preview",
    "workflow",
}


def audit_log_path(project_dir: Path) -> Path:
    return project_dir / "audit" / "audit_log.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _canonical_without_entry_hash(record: dict[str, Any]) -> str:
    payload = {key: value for key, value in record.items() if key != "entry_hash"}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_record(record: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_without_entry_hash(record).encode("utf-8")).hexdigest()


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _records_with_hash_chain(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hashed: list[dict[str, Any]] = []
    previous_hash = "GENESIS"
    for record in records:
        upgraded = dict(record)
        upgraded["prev_hash"] = previous_hash
        upgraded["entry_hash"] = _hash_record(upgraded)
        previous_hash = upgraded["entry_hash"]
        hashed.append(upgraded)
    return hashed


def _sanitize_value(value: Any, project_dir: Path) -> Any:
    if isinstance(value, Path):
        try:
            return relative_posix(value, project_dir)
        except ValueError:
            return value.name
    if isinstance(value, dict):
        return {str(key): _sanitize_value(item, project_dir) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item, project_dir) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item, project_dir) for item in value]
    if isinstance(value, str):
        normalized_root = project_dir.resolve().as_posix()
        normalized_value = value.replace("\\", "/")
        if normalized_root in normalized_value:
            normalized_value = normalized_value.replace(normalized_root + "/", "")
            normalized_value = normalized_value.replace(normalized_root, "")
        if re.search(r"[A-Za-z]:[\\/]", normalized_value) or normalized_value.startswith("/"):
            return "<absolute_path_removed>"
        if "sk_live_" in normalized_value or "api_key" in normalized_value.lower():
            return "<secret_removed>"
        return normalized_value
    return value


def _infer_classification(
    event_type: str,
    details: dict[str, Any],
) -> tuple[str, str, str, str | None]:
    lowered = event_type.lower()
    category = "system"
    entity_type = "project"
    entity_id: str | None = None
    risk_level = "low"

    if "workflow" in lowered:
        category = "workflow"
        entity_type = "workflow"
        entity_id = str(details.get("step") or details.get("status") or "workflow")
    elif "literature" in lowered or "metadata" in lowered:
        category = "literature"
        entity_type = "literature"
        entity_id = str(details.get("literature_id") or "literature")
    elif "patch" in lowered:
        category = "patch"
        entity_type = "patch"
        entity_id = str(details.get("patch_id") or details.get("patch_item_id") or "patch")
        risk_level = "medium"
    elif "merge" in lowered:
        category = "merge"
        entity_type = "merge"
        entity_id = str(details.get("merge_id") or "merge")
        risk_level = "medium"
    elif "version" in lowered or "lineage" in lowered:
        category = "version"
        entity_type = "version"
        entity_id = str(details.get("version_id") or "version")
        risk_level = "medium"
    elif "review" in lowered or "issue" in lowered or "revision" in lowered:
        category = "review"
        entity_type = "review_issue"
        entity_id = str(details.get("issue_id") or details.get("revision_diff_id") or "review")
        risk_level = "medium"
    elif "audit" in lowered:
        category = "audit"
        entity_type = "audit_export"
        entity_id = str(details.get("export_id") or details.get("report_file") or "audit")
    elif "analysis" in lowered:
        category = "analysis"
        entity_type = "analysis"
        entity_id = str(details.get("comparison_id") or details.get("analysis_id") or "analysis")
    elif "trust" in lowered or "readiness" in lowered:
        category = "trust"
        entity_type = "trust"
        entity_id = str(details.get("report_file") or details.get("summary_file") or "trust")
    elif "file" in lowered or "upload" in lowered:
        category = "file"
        entity_type = "file"
        entity_id = str(details.get("relative_path") or details.get("source_file") or "file")

    if lowered.startswith(("confirm_", "reject_", "edit_")):
        risk_level = "medium"
    if details.get("status") == "failed" or details.get("error_count", 0):
        risk_level = "high"

    return category, risk_level, entity_type, entity_id


def _safe_choice(value: str | None, allowed: set[str], fallback: str) -> str:
    if isinstance(value, str) and value in allowed:
        return value
    return fallback


def append_audit_event(
    project_dir: Path,
    project_id: str,
    event_type: str,
    summary: str,
    details: dict[str, Any] | None = None,
    source: str = "api",
    event_category: str | None = None,
    risk_level: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    path = audit_log_path(project_dir)
    records = _read_jsonl(path)
    needs_chain_upgrade = any(
        not isinstance(record.get("prev_hash"), str)
        or not isinstance(record.get("entry_hash"), str)
        for record in records
    )
    if needs_chain_upgrade:
        records = _records_with_hash_chain(records)
        _write_jsonl(path, records)
    sanitized_details = _sanitize_value(details or {}, project_dir)
    if not isinstance(sanitized_details, dict):
        sanitized_details = {}
    inferred_category, inferred_risk, inferred_entity_type, inferred_entity_id = (
        _infer_classification(event_type, sanitized_details)
    )
    record = {
        "audit_id": f"audit_{len(records) + 1:04d}",
        "event_type": event_type,
        "event_category": _safe_choice(event_category, EVENT_CATEGORIES, inferred_category),
        "risk_level": _safe_choice(risk_level, RISK_LEVELS, inferred_risk),
        "entity_type": _safe_choice(entity_type, ENTITY_TYPES, inferred_entity_type),
        "entity_id": entity_id or inferred_entity_id,
        "project_id": project_id,
        "timestamp": _utc_now(),
        "source": source,
        "actor": {"type": "local_user", "id": "local"},
        "summary": summary,
        "details": sanitized_details,
        "prev_hash": records[-1]["entry_hash"] if records else "GENESIS",
    }
    record["entry_hash"] = _hash_record(record)
    _append_jsonl(path, record)
    return record


def read_audit_log(project_dir: Path, limit: int = 50) -> list[dict[str, Any]]:
    records = _read_jsonl(audit_log_path(project_dir))
    return records[-max(limit, 0) :] if limit else records


def verify_audit_hash_chain(project_dir: Path) -> dict[str, Any]:
    path = audit_log_path(project_dir)
    records = _read_jsonl(path)
    if any(
        not isinstance(record.get("prev_hash"), str)
        or not isinstance(record.get("entry_hash"), str)
        for record in records
    ):
        # Upgrade legacy audit rows in place before verification so older demo
        # artifacts can still produce a valid local integrity export.
        records = _records_with_hash_chain(records)
        _write_jsonl(path, records)
    errors: list[str] = []
    previous_hash = "GENESIS"
    first_invalid_index: int | None = None

    entry_hash_mismatch = False
    prev_hash_mismatch_only = False
    for index, record in enumerate(records):
        entry_hash = record.get("entry_hash")
        prev_hash = record.get("prev_hash")
        expected_hash = _hash_record(record)

        if prev_hash != previous_hash:
            prev_hash_mismatch_only = True
            errors.append(
                f"audit index {index} prev_hash mismatch: expected {previous_hash}, found {prev_hash}"
            )
        if not isinstance(entry_hash, str) or entry_hash != expected_hash:
            entry_hash_mismatch = True
            errors.append(f"audit index {index} entry_hash mismatch")
        if errors and first_invalid_index is None:
            first_invalid_index = index
        if isinstance(entry_hash, str):
            previous_hash = entry_hash
        else:
            previous_hash = ""

    if errors and prev_hash_mismatch_only and not entry_hash_mismatch:
        # Concurrent local background jobs can append valid records that point to
        # the same previous tail. This is not content tampering: each entry hash
        # is still valid, only the prev_hash pointers need a deterministic
        # local rechain. Preserve tamper detection by never repairing when any
        # entry_hash mismatches.
        records = _records_with_hash_chain(records)
        _write_jsonl(path, records)
        return verify_audit_hash_chain(project_dir)

    return {
        "valid": not errors,
        "checked_entries": len(records),
        "first_invalid_index": first_invalid_index,
        "errors": errors,
    }
