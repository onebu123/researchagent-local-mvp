from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json


EXPORT_ROOTS = [
    "manuscript",
    "provenance",
    "reviews",
    "trust",
    "analysis",
    "figures",
    "llm",
]
EXPORT_SINGLE_FILES = [
    "literature/literature_index.json",
    "literature/pdf_quality_report.json",
    "literature/references.bib",
    "literature/bibtex_report.json",
    "literature/reference_approvals.jsonl",
    "literature/reference_approval_summary.json",
    "manuscript/references_status.json",
    "manuscript/references_section_preview.md",
    "provenance/citation_grounding_report.json",
    "runs/run_history.json",
    "audit/audit_log.jsonl",
]
EXPORT_PREFIXES = [
    "audit/exports",
    "audit/filtered_exports",
    "literature/parsed",
    "literature/rag",
    "literature/reference_verification",
]
EXPORT_GLOBS = [
    "literature/metadata*.json",
    "literature/metadata*.jsonl",
]
EXCLUDED_DIR_NAMES = {
    ".cache",
    ".git",
    ".next",
    ".pytest_cache",
    ".runtime",
    "__pycache__",
    "blob-report",
    "cache",
    "dist",
    "build",
    "node_modules",
    "playwright-report",
    "test-results",
}
EXCLUDED_FILE_NAMES = {".env", ".ds_store"}
SENSITIVE_FILE_MARKERS = {
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "credential",
}
TEXT_SUFFIXES = {
    ".csv",
    ".bib",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".svg",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"OPENAI_API_KEY\s*[:=]", re.IGNORECASE),
    re.compile(r"(api[_-]?key|secret|token|password)\s*[:=]\s*[\"']?[^\"'\s,;]{8,}", re.IGNORECASE),
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY"),
]
ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:[\\/][^\s\"']+"),
    re.compile(r"/(?:home|Users|var|tmp|mnt)/[^\s\"']+"),
]


class ProjectExportError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_for_filename() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _is_env_file(path: Path) -> bool:
    name = path.name.lower()
    return name == ".env" or name.startswith(".env.")


def _has_sensitive_name(path: Path) -> bool:
    lowered = path.name.lower()
    return any(marker in lowered for marker in SENSITIVE_FILE_MARKERS)


def _should_skip_path(path: Path, project_dir: Path) -> tuple[bool, str | None]:
    relative_parts = tuple(part.lower() for part in path.resolve().relative_to(project_dir.resolve()).parts)
    if any(part in EXCLUDED_DIR_NAMES for part in relative_parts[:-1]):
        return True, "excluded_directory"
    if path.is_dir() and path.name.lower() in EXCLUDED_DIR_NAMES:
        return True, "excluded_directory"
    if _is_env_file(path):
        return True, "environment_file"
    if path.name.lower() in EXCLUDED_FILE_NAMES:
        return True, "excluded_file"
    if path.suffix.lower() in {".pyc", ".pyo"}:
        return True, "python_cache"
    if _has_sensitive_name(path):
        return True, "sensitive_filename"
    return False, None


def _iter_files(folder: Path) -> Iterable[Path]:
    if not folder.exists():
        return []
    return (path for path in sorted(folder.rglob("*")) if path.is_file())


def _candidate_files(project_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for root in EXPORT_ROOTS:
        candidates.extend(_iter_files(project_dir / root))
    for relative_path in EXPORT_SINGLE_FILES:
        path = project_dir / relative_path
        if path.exists() and path.is_file():
            candidates.append(path)
    for prefix in EXPORT_PREFIXES:
        candidates.extend(_iter_files(project_dir / prefix))
    for pattern in EXPORT_GLOBS:
        candidates.extend(path for path in sorted(project_dir.glob(pattern)) if path.is_file())
    unique: dict[str, Path] = {}
    for path in candidates:
        unique[_relative_posix(path, project_dir)] = path
    return [unique[key] for key in sorted(unique)]


def _scan_text_file(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "unreadable_text_file"
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return "secret_pattern"
    for pattern in ABSOLUTE_PATH_PATTERNS:
        if pattern.search(text):
            return "absolute_path_pattern"
    return None


def _safe_archive_name(path: Path, project_dir: Path) -> str:
    archive_name = _relative_posix(path, project_dir)
    if archive_name.startswith("../") or archive_name == ".." or "/../" in archive_name:
        raise ProjectExportError(f"Unsafe archive path: {archive_name}")
    if Path(archive_name).is_absolute() or re.search(r"^[A-Za-z]:", archive_name):
        raise ProjectExportError(f"Absolute archive path rejected: {archive_name}")
    return archive_name


def _readme_export(project_id: str, created_at: str, file_count: int) -> str:
    return (
        f"# ResearchAgent Local MVP Export\n\n"
        f"- Project ID: `{project_id}`\n"
        f"- Created at: `{created_at}`\n"
        f"- Included files: `{file_count}`\n\n"
        "This archive contains local MVP artifacts only: manuscripts, provenance, review "
        "records, trust/readiness outputs, analysis outputs, figures, selected literature "
        "metadata, audit exports, and run history.\n\n"
        "It intentionally excludes environment files, API keys, secrets, dependency folders, "
        "runtime caches, Playwright reports, and machine-specific absolute paths.\n\n"
        "Limitations: this is not a production backup, compliance archive, peer-review "
        "certificate, DOI verification, OCR result, plagiarism report, or scientific "
        "validity certificate.\n"
    )


def build_project_export(project_dir: Path, project_id: str) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        raise FileNotFoundError(f"Project directory does not exist: {project_id}")

    created_at = _utc_now()
    timestamp = _timestamp_for_filename()
    exports_dir = ensure_dir(project_dir / "exports")
    zip_name = f"researchagent_{project_id}_local_mvp_export_{timestamp}.zip"
    zip_path = (exports_dir / zip_name).resolve()
    if project_dir not in zip_path.parents:
        raise ProjectExportError("Export path escaped the project directory.")

    warnings: list[dict[str, str]] = []
    included_files: list[dict[str, Any]] = []

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in _candidate_files(project_dir):
            skip, reason = _should_skip_path(path, project_dir)
            relative_path = _relative_posix(path, project_dir)
            if skip:
                warnings.append({"relative_path": relative_path, "reason": reason or "skipped"})
                continue
            scan_reason = _scan_text_file(path)
            if scan_reason:
                warnings.append({"relative_path": relative_path, "reason": scan_reason})
                continue
            archive_name = _safe_archive_name(path, project_dir)
            archive.write(path, archive_name)
            included_files.append(
                {
                    "relative_path": archive_name,
                    "size_bytes": path.stat().st_size,
                    "category": archive_name.split("/", 1)[0],
                }
            )
        archive.writestr("README_EXPORT.md", _readme_export(project_id, created_at, len(included_files)))

    category_counts: dict[str, int] = {}
    for item in included_files:
        category = str(item["category"])
        category_counts[category] = category_counts.get(category, 0) + 1

    metadata = {
        "available": True,
        "project_id": project_id,
        "created_at": created_at,
        "export_id": zip_path.stem,
        "file_name": zip_name,
        "relative_path": _relative_posix(zip_path, project_dir),
        "size_bytes": zip_path.stat().st_size,
        "included_file_count": len(included_files),
        "category_counts": category_counts,
        "included_files": included_files,
        "warnings": warnings,
        "excluded_patterns": sorted(EXCLUDED_DIR_NAMES | EXCLUDED_FILE_NAMES)
        + [".env.*", "*.pyc", "sensitive filename/content", "absolute path content"],
        "local_mvp_caveats": [
            "Local MVP export only; not a production backup or compliance archive.",
            "No DOI verification, OCR execution, plagiarism detection, or scientific validity check is performed.",
            "Returned paths are project-relative and safe to display in the local dashboard.",
        ],
    }
    metadata_path = exports_dir / f"{zip_path.stem}.json"
    write_json(metadata_path, metadata)
    append_audit_event(
        project_dir,
        project_id,
        "create_project_export_zip",
        "Local MVP project zip export was created.",
        {
            "export_file": metadata["relative_path"],
            "metadata_file": _relative_posix(metadata_path, project_dir),
            "included_file_count": len(included_files),
            "warning_count": len(warnings),
        },
        source="api",
        event_category="audit",
        risk_level="low",
        entity_type="audit_export",
        entity_id=metadata["export_id"],
    )
    return metadata


def latest_project_export_info(project_dir: Path, project_id: str) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    exports_dir = project_dir / "exports"
    if not exports_dir.exists():
        return {
            "available": False,
            "project_id": project_id,
            "relative_path": None,
            "category_counts": {},
            "included_files": [],
            "warnings": [],
            "local_mvp_caveats": [],
            "message": "No project zip export has been created yet.",
        }
    zip_files = sorted(exports_dir.glob("researchagent_*_local_mvp_export_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not zip_files:
        return {
            "available": False,
            "project_id": project_id,
            "relative_path": None,
            "category_counts": {},
            "included_files": [],
            "warnings": [],
            "local_mvp_caveats": [],
            "message": "No project zip export has been created yet.",
        }
    latest_zip = zip_files[0].resolve()
    metadata_path = latest_zip.with_suffix(".json")
    if metadata_path.exists():
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        payload["available"] = True
        return payload
    return {
        "available": True,
        "project_id": project_id,
        "created_at": datetime.fromtimestamp(latest_zip.stat().st_mtime, tz=timezone.utc).isoformat(),
        "export_id": latest_zip.stem,
        "file_name": latest_zip.name,
        "relative_path": _relative_posix(latest_zip, project_dir),
        "size_bytes": latest_zip.stat().st_size,
        "included_file_count": None,
        "category_counts": {},
        "included_files": [],
        "warnings": [],
        "local_mvp_caveats": [
            "Metadata file was not found; zip path is available but summary is partial.",
        ],
    }
