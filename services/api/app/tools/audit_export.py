from __future__ import annotations

import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event, read_audit_log, verify_audit_hash_chain
from app.tools.file_tools import write_json, write_text


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def audit_exports_dir(project_dir: Path) -> Path:
    return project_dir / "audit" / "exports"


def _manifest_path(project_dir: Path, export_id: str) -> Path:
    number = _safe_export_id(export_id).removeprefix("audit_export_")
    return audit_exports_dir(project_dir) / f"audit_file_manifest_{number}.json"


def _safe_export_id(export_id: str) -> str:
    if not re.fullmatch(r"audit_export_\d{3,}", export_id):
        raise ValueError("invalid export_id")
    return export_id


def _next_export_id(project_dir: Path) -> tuple[str, Path, Path]:
    numbers: list[int] = []
    for path in audit_exports_dir(project_dir).glob("audit_export_*.json"):
        match = re.fullmatch(r"audit_export_(\d+)\.json", path.name)
        if match:
            numbers.append(int(match.group(1)))
    number = (max(numbers) + 1) if numbers else 1
    export_id = f"audit_export_{number:03d}"
    return (
        export_id,
        audit_exports_dir(project_dir) / f"{export_id}.json",
        audit_exports_dir(project_dir) / f"audit_integrity_report_{number:03d}.md",
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


def _relative_posix(path: Path, project_dir: Path) -> str:
    return path.resolve().relative_to(project_dir.resolve()).as_posix()


def _category_for_path(relative_path: str) -> str:
    if relative_path.startswith("manuscript/versions/"):
        return "manuscript_version"
    if relative_path.startswith("manuscript/patches/merges/"):
        return "patch_merge"
    if relative_path.startswith("manuscript/patches/"):
        return "manuscript_patch"
    if relative_path.startswith("manuscript/diffs/"):
        return "manuscript_diff"
    if relative_path.startswith("manuscript/"):
        return "manuscript"
    if relative_path.startswith("provenance/"):
        return "provenance"
    if relative_path.startswith("reviews/"):
        return "review"
    if relative_path.startswith("figures/"):
        return "figure"
    if relative_path.startswith("analysis/"):
        return "analysis"
    if relative_path.startswith("literature/"):
        return "literature"
    if relative_path.startswith("audit/exports/"):
        return "audit_export"
    if relative_path.startswith("audit/"):
        return "audit"
    if relative_path.startswith("runs/"):
        return "run_history"
    return "project_file"


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_record(project_dir: Path, path: Path) -> dict[str, Any]:
    relative_path = _relative_posix(path, project_dir)
    return {
        "relative_path": relative_path,
        "category": _category_for_path(relative_path),
        "size_bytes": path.stat().st_size,
        "sha256": _hash_file(path),
    }


def build_audit_file_manifest(
    project_dir: Path,
    project_id: str,
    export_id: str,
) -> dict[str, Any]:
    manifest_path = _manifest_path(project_dir, export_id)
    files: list[dict[str, Any]] = []
    warnings: list[str] = []
    category_counts: dict[str, int] = {}

    for path in sorted(project_dir.rglob("*")):
        if not path.is_file():
            continue
        relative_path = _relative_posix(path, project_dir)
        if relative_path.startswith("."):
            continue
        if relative_path.startswith("audit/exports/audit_file_manifest_"):
            continue
        if relative_path.startswith("audit/exports/audit_integrity_report_"):
            continue
        try:
            record = _manifest_record(project_dir, path)
        except OSError as exc:
            warnings.append(f"Failed to hash {relative_path}: {exc}")
            continue
        files.append(record)
        category = str(record["category"])
        category_counts[category] = category_counts.get(category, 0) + 1

    required_files = [
        "manuscript/draft.md",
        "manuscript/versions/version_history.json",
        "manuscript/versions/version_lineage.json",
        "provenance/evidence.json",
        "reviews/review_report.json",
        "reviews/issue_resolution.json",
        "audit/audit_log.jsonl",
    ]
    present = {item["relative_path"] for item in files}
    for relative_path in required_files:
        if relative_path not in present:
            warnings.append(f"Required audit manifest file is missing: {relative_path}")

    payload = {
        "manifest_id": f"manifest_{export_id.removeprefix('audit_export_')}",
        "project_id": project_id,
        "export_id": export_id,
        "created_at": _utc_now(),
        "relative_path": _relative_posix(manifest_path, project_dir),
        "file_count": len(files),
        "category_counts": category_counts,
        "files": files,
        "warnings": warnings,
        "notes": [
            "This manifest records local file hashes for traceability and is not a remote notarization system."
        ],
    }
    write_json(manifest_path, payload)
    return payload


def _build_report(
    project_id: str,
    export_payload: dict[str, Any],
    manifest: dict[str, Any] | None = None,
) -> str:
    first_invalid = export_payload.get("first_invalid_index")
    first_invalid_text = "none" if first_invalid is None else str(first_invalid)
    manifest_section = ""
    if manifest:
        manifest_section = (
            "\n## File Manifest Summary\n\n"
            f"Manifest file: {manifest.get('relative_path')}\n"
            f"Files hashed: {manifest.get('file_count')}\n"
            f"Categories: {json.dumps(manifest.get('category_counts', {}), ensure_ascii=False)}\n"
            f"Warnings: {len(manifest.get('warnings') or [])}\n"
        )
    return (
        "# Audit Integrity Report\n\n"
        f"Project: {project_id}\n"
        f"Export ID: {export_payload['export_id']}\n"
        f"Entries checked: {export_payload['entry_count']}\n"
        f"Hash chain valid: {str(export_payload['hash_chain_valid']).lower()}\n"
        f"First invalid index: {first_invalid_text}\n"
        f"{manifest_section}\n"
        "## Notes\n\n"
        "This is a local integrity report, not a production-grade tamper-proof audit system.\n"
    )


def export_audit_log(project_dir: Path, project_id: str) -> dict[str, Any]:
    verify = verify_audit_hash_chain(project_dir)
    entries = _sanitize_export_value(read_audit_log(project_dir, limit=0))
    export_id, json_path, report_path = _next_export_id(project_dir)
    payload = {
        "export_id": export_id,
        "created_at": _utc_now(),
        "source_file": "audit/audit_log.jsonl",
        "report_file": f"audit/exports/{report_path.name}",
        "manifest_file": f"audit/exports/{_manifest_path(project_dir, export_id).name}",
        "entry_count": len(entries),
        "hash_chain_valid": bool(verify.get("valid")),
        "first_invalid_index": verify.get("first_invalid_index"),
        "entries": entries,
    }
    write_json(json_path, payload)
    manifest = build_audit_file_manifest(project_dir, project_id, export_id)
    write_text(report_path, _build_report(project_id, payload, manifest))
    append_audit_event(
        project_dir,
        project_id,
        "export_audit_log",
        "Audit log export and local integrity report were generated.",
        {
            "export_id": export_id,
            "entry_count": len(entries),
            "hash_chain_valid": payload["hash_chain_valid"],
        },
        source="api",
    )
    return payload


def list_audit_exports(project_dir: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(audit_exports_dir(project_dir).glob("audit_export_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("export_id"):
            result.append(
                {
                    "export_id": payload.get("export_id"),
                    "created_at": payload.get("created_at"),
                    "entry_count": payload.get("entry_count"),
                    "hash_chain_valid": payload.get("hash_chain_valid"),
                    "source_file": payload.get("source_file"),
                    "report_file": payload.get("report_file"),
                    "manifest_file": payload.get("manifest_file"),
                }
            )
    return result


def load_audit_export(project_dir: Path, export_id: str) -> dict[str, Any]:
    safe_export_id = _safe_export_id(export_id)
    path = audit_exports_dir(project_dir) / f"{safe_export_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"audit export does not exist: {export_id}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("audit export JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("audit export JSON must be an object")
    return payload


def load_audit_export_report(project_dir: Path, export_id: str) -> str:
    safe_export_id = _safe_export_id(export_id)
    number = safe_export_id.removeprefix("audit_export_")
    path = audit_exports_dir(project_dir) / f"audit_integrity_report_{number}.md"
    if not path.exists():
        raise FileNotFoundError(f"audit export report does not exist: {export_id}")
    return path.read_text(encoding="utf-8")


def load_audit_file_manifest(project_dir: Path, export_id: str) -> dict[str, Any]:
    path = _manifest_path(project_dir, export_id)
    if not path.exists():
        raise FileNotFoundError(f"audit file manifest does not exist: {export_id}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("audit file manifest JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("audit file manifest JSON must be an object")
    return payload
