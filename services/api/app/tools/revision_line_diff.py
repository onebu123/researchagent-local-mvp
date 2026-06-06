from __future__ import annotations

import difflib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json
from app.tools.manuscript_patch import load_patch, read_version_history


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def revision_diffs_dir(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "revision_diffs"


def _safe_revision_diff_id(revision_diff_id: str) -> str:
    if not re.fullmatch(r"revision_diff_\d{3,}", revision_diff_id):
        raise ValueError("invalid revision_diff_id")
    return revision_diff_id


def _next_revision_diff_id(project_dir: Path) -> tuple[str, Path]:
    numbers: list[int] = []
    for path in revision_diffs_dir(project_dir).glob("revision_diff_*.json"):
        match = re.fullmatch(r"revision_diff_(\d+)\.json", path.name)
        if match:
            numbers.append(int(match.group(1)))
    number = (max(numbers) + 1) if numbers else 1
    revision_diff_id = f"revision_diff_{number:03d}"
    return revision_diff_id, revision_diffs_dir(project_dir) / f"{revision_diff_id}.json"


def _safe_manuscript_file(value: str, *, target: bool = False) -> str:
    cleaned = value.strip().replace("\\", "/")
    if not cleaned or cleaned.startswith("/") or ".." in cleaned.split("/"):
        raise ValueError("manuscript file path must stay inside project")
    if target:
        if not cleaned.startswith("manuscript/versions/") or not cleaned.endswith(".md"):
            raise ValueError("target_file must be a manuscript version markdown file")
    elif not cleaned.startswith("manuscript/") or not cleaned.endswith(".md"):
        raise ValueError("base_file must stay under manuscript and end with .md")
    return cleaned


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _target_version_record(project_dir: Path, target_file: str) -> dict[str, Any]:
    history = read_version_history(project_dir)
    for record in history["versions"]:
        if isinstance(record, dict) and record.get("file") == target_file:
            return record
    raise FileNotFoundError(f"version history record does not exist for target_file: {target_file}")


def _claim_ids_from_patch(project_dir: Path, patch_id: str | None) -> set[str]:
    if not patch_id:
        return set()
    try:
        patch = load_patch(project_dir, patch_id)
    except (FileNotFoundError, ValueError):
        return set()
    claim_ids: set[str] = set()
    for item in patch.get("items", []):
        if isinstance(item, dict) and isinstance(item.get("related_claim_id"), str):
            claim_ids.add(str(item["related_claim_id"]))
    return claim_ids


def _related_ids(project_dir: Path, record: dict[str, Any]) -> tuple[list[str], list[str]]:
    issue_ids = {
        str(item)
        for item in record.get("source_issue_ids", [])
        if isinstance(item, str) and item
    }
    claim_ids: set[str] = set()

    patch_id = record.get("source_patch_id")
    if isinstance(patch_id, str):
        claim_ids.update(_claim_ids_from_patch(project_dir, patch_id))

    for patch_id in record.get("source_patch_ids", []):
        if isinstance(patch_id, str):
            claim_ids.update(_claim_ids_from_patch(project_dir, patch_id))

    evidence = _read_json(project_dir / "provenance" / "evidence.json", [])
    if not claim_ids and isinstance(evidence, list):
        claim_ids.update(
            str(item["claim_id"])
            for item in evidence
            if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
        )

    return sorted(issue_ids), sorted(claim_ids)


def _sentence_count(text: str) -> int:
    parts = [item for item in re.split(r"(?<=[.!?。！？])\s+", text.strip()) if item.strip()]
    return max(1, len(parts)) if text.strip() else 0


def _line_context(lines: list[str]) -> dict[int, dict[str, Any]]:
    context: dict[int, dict[str, Any]] = {}
    section = "Document"
    paragraph_index = 0
    sentence_index = 0
    in_paragraph = False
    paragraph_text = ""

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            section = heading.group(2).strip()
            paragraph_index = 0
            sentence_index = 0
            in_paragraph = False
            paragraph_text = ""
            context[index] = {
                "section": section,
                "paragraph_index": 0,
                "sentence_index": 0,
            }
            continue

        if not stripped:
            in_paragraph = False
            paragraph_text = ""
            context[index] = {
                "section": section,
                "paragraph_index": paragraph_index,
                "sentence_index": sentence_index,
            }
            continue

        if not in_paragraph:
            paragraph_index += 1
            sentence_index = 1
            paragraph_text = stripped
            in_paragraph = True
        else:
            paragraph_text = f"{paragraph_text} {stripped}".strip()
            sentence_index = max(1, _sentence_count(paragraph_text))

        context[index] = {
            "section": section,
            "paragraph_index": paragraph_index,
            "sentence_index": sentence_index,
        }
    return context


def _context_for_line(
    context: dict[int, dict[str, Any]],
    line_number: int,
) -> dict[str, Any]:
    if line_number in context:
        return context[line_number]
    lower = [key for key in context if key < line_number]
    if lower:
        return context[max(lower)]
    return {"section": "Document", "paragraph_index": 0, "sentence_index": 0}


def _infer_change_type(before: str, after: str) -> str:
    overclaim_terms = (
        "significant",
        "significantly",
        "statistically significant",
        "prove",
        "proved",
        "causal",
        "显著",
        "证明",
        "因果",
    )
    before_lower = before.lower()
    after_lower = after.lower()
    if any(term in before_lower for term in overclaim_terms) and not any(
        term in after_lower for term in overclaim_terms
    ):
        return "remove_overclaim"
    if before and after:
        return "revise_text"
    if after:
        return "add_text"
    return "remove_text"


def _safety_status(after: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    risky_terms = (" p<", "p =", "p-value", "significantly", "proved", "causal", "证明", "因果")
    lowered = after.lower()
    if any(term in lowered for term in risky_terms):
        notes.append("Changed text contains terms that may require patch_safety or reviewer follow-up.")
        return "needs_human_review", notes
    return "safe", notes


def _build_changes(
    base_lines: list[str],
    target_lines: list[str],
    related_issue_ids: list[str],
    related_claim_ids: list[str],
) -> list[dict[str, Any]]:
    matcher = difflib.SequenceMatcher(a=base_lines, b=target_lines)
    context = _line_context(base_lines)
    changes: list[dict[str, Any]] = []
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        before_lines = base_lines[old_start:old_end]
        after_lines = target_lines[new_start:new_end]
        before = "\n".join(before_lines)
        after = "\n".join(after_lines)
        line_start = old_start + 1
        line_end = max(line_start, old_end)
        line_context = _context_for_line(context, line_start)
        safety_status, notes = _safety_status(after)
        changes.append(
            {
                "change_id": f"change_{len(changes) + 1:03d}",
                "section": line_context["section"],
                "paragraph_index": line_context["paragraph_index"],
                "sentence_index": line_context["sentence_index"],
                "line_start": line_start,
                "line_end": line_end,
                "before": before,
                "after": after,
                "change_type": _infer_change_type(before, after),
                "related_issue_ids": related_issue_ids,
                "related_claim_ids": related_claim_ids,
                "safety_status": safety_status,
                "notes": notes,
            }
        )
    return changes


def generate_revision_line_diff(
    project_dir: Path,
    project_id: str,
    base_file: str,
    target_file: str,
) -> dict[str, Any]:
    safe_base = _safe_manuscript_file(base_file)
    safe_target = _safe_manuscript_file(target_file, target=True)
    base_path = project_dir / safe_base
    target_path = project_dir / safe_target
    if not base_path.exists():
        raise FileNotFoundError(f"base file does not exist: {safe_base}")
    if not target_path.exists():
        raise FileNotFoundError(f"target file does not exist: {safe_target}")

    record = _target_version_record(project_dir, safe_target)
    related_issue_ids, related_claim_ids = _related_ids(project_dir, record)
    base_lines = base_path.read_text(encoding="utf-8", errors="replace").splitlines()
    target_lines = target_path.read_text(encoding="utf-8", errors="replace").splitlines()
    changes = _build_changes(base_lines, target_lines, related_issue_ids, related_claim_ids)
    revision_diff_id, path = _next_revision_diff_id(project_dir)
    payload = {
        "revision_diff_id": revision_diff_id,
        "base_file": safe_base,
        "target_file": safe_target,
        "created_at": _utc_now(),
        "relative_path": f"manuscript/revision_diffs/{revision_diff_id}.json",
        "summary": {
            "sections_checked": len({item["section"] for item in changes}),
            "paragraphs_checked": len(
                {(item["section"], item["paragraph_index"]) for item in changes}
            ),
            "sentences_changed": len(
                {
                    (item["section"], item["paragraph_index"], item["sentence_index"])
                    for item in changes
                }
            ),
            "lines_changed": sum(
                max(1, int(item["line_end"]) - int(item["line_start"]) + 1)
                for item in changes
            ),
            "issues_linked": len(related_issue_ids),
            "claims_linked": len(related_claim_ids),
        },
        "changes": changes,
    }
    ensure_dir(path.parent)
    write_json(path, payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_revision_line_diff",
        "Revision line diff was generated without modifying manuscript files.",
        {
            "revision_diff_id": revision_diff_id,
            "base_file": safe_base,
            "target_file": safe_target,
            "changes": len(changes),
        },
        source="api",
    )
    return payload


def list_revision_line_diffs(project_dir: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(revision_diffs_dir(project_dir).glob("revision_diff_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("revision_diff_id"):
            result.append(payload)
    return result


def load_revision_line_diff(project_dir: Path, revision_diff_id: str) -> dict[str, Any]:
    safe_id = _safe_revision_diff_id(revision_diff_id)
    path = revision_diffs_dir(project_dir) / f"{safe_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"revision diff does not exist: {revision_diff_id}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("revision diff JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("revision diff JSON must be an object")
    return payload

