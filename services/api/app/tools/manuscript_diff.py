from __future__ import annotations

import difflib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json, write_text
from app.tools.manuscript_patch import load_patch, read_version_history


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def diffs_dir(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "diffs"


def _safe_diff_id(diff_id: str) -> str:
    if not re.fullmatch(r"diff_\d{3,}", diff_id):
        raise ValueError("invalid diff_id")
    return diff_id


def _next_diff_id(project_dir: Path) -> tuple[str, Path, Path]:
    numbers: list[int] = []
    for path in diffs_dir(project_dir).glob("diff_*.json"):
        match = re.fullmatch(r"diff_(\d+)\.json", path.name)
        if match:
            numbers.append(int(match.group(1)))
    number = (max(numbers) + 1) if numbers else 1
    diff_id = f"diff_{number:03d}"
    return diff_id, diffs_dir(project_dir) / f"{diff_id}.json", diffs_dir(project_dir) / f"{diff_id}.md"


def _safe_relative_file(value: str, allowed_prefixes: tuple[str, ...]) -> str:
    cleaned = value.strip().replace("\\", "/")
    if not cleaned or cleaned.startswith("/") or ".." in cleaned.split("/"):
        raise ValueError("file path must stay inside project")
    if not cleaned.startswith(allowed_prefixes):
        raise ValueError(f"file path must start with one of: {allowed_prefixes}")
    return cleaned


def _version_record(project_dir: Path, version_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"manuscript_v\d{3,}", version_id):
        raise ValueError("invalid version_id")
    history = read_version_history(project_dir)
    record = next(
        (item for item in history["versions"] if item.get("version_id") == version_id),
        None,
    )
    if not record:
        raise FileNotFoundError(f"version does not exist: {version_id}")
    return record


def _related_ids(project_dir: Path, record: dict[str, Any]) -> tuple[list[str], list[str]]:
    issue_ids = [
        str(item)
        for item in record.get("source_issue_ids", [])
        if isinstance(item, str) and item
    ]
    claim_ids: set[str] = set()
    patch_id = record.get("source_patch_id")
    if isinstance(patch_id, str) and patch_id:
        try:
            patch = load_patch(project_dir, patch_id)
        except (FileNotFoundError, ValueError):
            patch = {}
        for item in patch.get("items", []):
            if isinstance(item, dict) and isinstance(item.get("related_claim_id"), str):
                claim_ids.add(str(item["related_claim_id"]))
    return sorted(set(issue_ids)), sorted(claim_ids)


def _build_hunks(
    base_lines: list[str],
    version_lines: list[str],
    related_issue_ids: list[str],
    related_claim_ids: list[str],
) -> list[dict[str, Any]]:
    matcher = difflib.SequenceMatcher(a=base_lines, b=version_lines)
    hunks: list[dict[str, Any]] = []
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        removed = base_lines[old_start:old_end]
        added = version_lines[new_start:new_end]
        hunks.append(
            {
                "hunk_id": f"hunk_{len(hunks) + 1:03d}",
                "old_start": old_start + 1,
                "old_lines": old_end - old_start,
                "new_start": new_start + 1,
                "new_lines": new_end - new_start,
                "removed": removed,
                "added": added,
                "related_issue_ids": related_issue_ids,
                "related_claim_ids": related_claim_ids,
            }
        )
    return hunks


def _build_markdown(diff: dict[str, Any]) -> str:
    lines = [
        "# Manuscript Diff",
        "",
        f"Diff ID: {diff['diff_id']}",
        f"Base file: {diff['base_file']}",
        f"Version file: {diff['version_file']}",
        "",
        "## Summary",
        "",
        json.dumps(diff["summary"], ensure_ascii=False, indent=2),
        "",
    ]
    for hunk in diff["hunks"]:
        lines.extend(
            [
                f"## {hunk['hunk_id']}",
                "",
                f"Related issues: {', '.join(hunk['related_issue_ids']) or '-'}",
                f"Related claims: {', '.join(hunk['related_claim_ids']) or '-'}",
                "",
                "### Removed",
                "",
            ]
        )
        lines.extend(f"- {line}" for line in hunk["removed"])
        lines.extend(["", "### Added", ""])
        lines.extend(f"+ {line}" for line in hunk["added"])
        lines.append("")
    if not diff["hunks"]:
        lines.extend(["No textual differences detected.", ""])
    return "\n".join(lines).rstrip() + "\n"


def generate_manuscript_diff(
    project_dir: Path,
    project_id: str,
    base_file: str,
    version_id: str,
) -> dict[str, Any]:
    safe_base_file = _safe_relative_file(base_file, ("manuscript/",))
    record = _version_record(project_dir, version_id)
    version_file = _safe_relative_file(str(record.get("file") or ""), ("manuscript/versions/",))
    base_path = project_dir / safe_base_file
    version_path = project_dir / version_file
    if not base_path.exists():
        raise FileNotFoundError(f"base file does not exist: {safe_base_file}")
    if not version_path.exists():
        raise FileNotFoundError(f"version file does not exist: {version_file}")

    base_lines = base_path.read_text(encoding="utf-8", errors="replace").splitlines()
    version_lines = version_path.read_text(encoding="utf-8", errors="replace").splitlines()
    issue_ids, claim_ids = _related_ids(project_dir, record)
    hunks = _build_hunks(base_lines, version_lines, issue_ids, claim_ids)
    diff_id, json_path, md_path = _next_diff_id(project_dir)
    diff = {
        "diff_id": diff_id,
        "base_file": safe_base_file,
        "version_id": version_id,
        "version_file": version_file,
        "created_at": _utc_now(),
        "relative_path": f"manuscript/diffs/{diff_id}.json",
        "preview_file": f"manuscript/diffs/{diff_id}.md",
        "summary": {
            "added_lines": sum(len(item["added"]) for item in hunks),
            "removed_lines": sum(len(item["removed"]) for item in hunks),
            "changed_hunks": len(hunks),
        },
        "hunks": hunks,
    }
    write_json(json_path, diff)
    write_text(md_path, _build_markdown(diff))
    append_audit_event(
        project_dir,
        project_id,
        "generate_manuscript_diff",
        "Manuscript diff was generated without modifying manuscript files.",
        {
            "diff_id": diff_id,
            "base_file": safe_base_file,
            "version_id": version_id,
            "changed_hunks": len(hunks),
        },
        source="api",
    )
    return diff


def list_manuscript_diffs(project_dir: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(diffs_dir(project_dir).glob("diff_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("diff_id"):
            result.append(payload)
    return result


def load_manuscript_diff(project_dir: Path, diff_id: str) -> dict[str, Any]:
    safe_diff_id = _safe_diff_id(diff_id)
    path = diffs_dir(project_dir) / f"{safe_diff_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"diff does not exist: {diff_id}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("diff JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("diff JSON must be an object")
    return payload


def load_manuscript_diff_preview(project_dir: Path, diff_id: str) -> str:
    safe_diff_id = _safe_diff_id(diff_id)
    path = diffs_dir(project_dir) / f"{safe_diff_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"diff preview does not exist: {diff_id}")
    return path.read_text(encoding="utf-8")

