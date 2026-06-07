from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json, write_text
from app.tools.literature_index import load_literature_index
from app.tools.reference_approval import read_reference_approvals
from app.tools.reference_verification import read_reference_verification_results


def references_status_path(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "references_status.json"


def references_preview_path(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "references_section_preview.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _verification_by_literature(project_dir: Path) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in read_reference_verification_results(project_dir):
        literature_id = str(result.get("literature_id") or "")
        if literature_id:
            grouped.setdefault(literature_id, []).append(result)
    return grouped


def _latest_decision_by_literature(project_dir: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for approval in read_reference_approvals(project_dir):
        literature_id = str(approval.get("literature_id") or "")
        if literature_id:
            latest[literature_id] = approval
    return latest


def _is_verified_reference(entry: dict[str, Any]) -> bool:
    return (
        entry.get("metadata_status") == "verified"
        and entry.get("human_verified") is True
        and entry.get("reference_verification_status") == "approved"
    )


def _reference_record(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "literature_id": entry.get("literature_id"),
        "title": entry.get("title"),
        "authors": entry.get("authors") if isinstance(entry.get("authors"), list) else [],
        "year": entry.get("year"),
        "doi": entry.get("doi"),
        "journal": entry.get("journal"),
        "source_file": entry.get("source_file"),
        "metadata_status": entry.get("metadata_status"),
        "reference_verification_status": entry.get("reference_verification_status"),
        "reference_verification_id": entry.get("reference_verification_id"),
        "human_verified": bool(entry.get("human_verified")),
    }


def _format_reference(entry: dict[str, Any]) -> str:
    authors = entry.get("authors") if isinstance(entry.get("authors"), list) else []
    author_text = ", ".join(str(author) for author in authors if str(author).strip())
    parts: list[str] = []
    if author_text:
        parts.append(author_text)
    if entry.get("year"):
        parts.append(f"({entry['year']})")
    if entry.get("title"):
        parts.append(str(entry["title"]))
    if entry.get("journal"):
        parts.append(str(entry["journal"]))
    line = ". ".join(parts).rstrip(".") + "."
    if entry.get("doi"):
        line += f" DOI: {entry['doi']}."
    return line


def generate_manuscript_references(project_dir: Path, project_id: str) -> dict[str, Any]:
    entries = load_literature_index(project_dir)
    verification_map = _verification_by_literature(project_dir)
    latest_decisions = _latest_decision_by_literature(project_dir)
    verified_references: list[dict[str, Any]] = []
    candidate_references: list[dict[str, Any]] = []
    placeholder_records: list[dict[str, Any]] = []
    warnings: list[str] = []

    for entry in entries:
        literature_id = str(entry.get("literature_id") or "")
        latest_decision = latest_decisions.get(literature_id, {})
        if latest_decision.get("decision") == "rejected":
            placeholder_records.append(
                {
                    **_reference_record(entry),
                    "warning": "Latest reference approval decision is rejected.",
                }
            )
            continue
        if _is_verified_reference(entry):
            verified_references.append(_reference_record(entry))
            continue
        if verification_map.get(literature_id):
            candidate_references.append(
                {
                    **_reference_record(entry),
                    "verification_results": verification_map[literature_id],
                    "warning": "Candidate reference is not approved and cannot enter formal References.",
                }
            )
            continue
        placeholder_records.append(
            {
                **_reference_record(entry),
                "warning": "Placeholder or unverified record cannot enter formal References.",
            }
        )

    if not verified_references:
        warnings.append("No approved human-verified references are available for formal References.")
    if candidate_references:
        warnings.append("Candidate references require approval before formal use.")
    if placeholder_records:
        warnings.append("Placeholder/unverified records were excluded from formal References.")

    status = {
        "generated_at": _utc_now(),
        "relative_path": "manuscript/references_status.json",
        "preview_file": "manuscript/references_section_preview.md",
        "verified_references": verified_references,
        "candidate_references": candidate_references,
        "placeholder_records": placeholder_records,
        "warnings": warnings,
    }
    write_json(references_status_path(project_dir), status)
    preview_lines = ["# References Preview", ""]
    if verified_references:
        preview_lines.extend(
            f"{index}. {_format_reference(entry)}"
            for index, entry in enumerate(verified_references, start=1)
        )
    else:
        preview_lines.append(
            "No formal References entries are available. Approve and apply references first."
        )
    if candidate_references or placeholder_records:
        preview_lines.extend(
            [
                "",
                "## Excluded Records",
                "",
                "Candidate and placeholder records are excluded from formal References.",
            ]
        )
    write_text(references_preview_path(project_dir), "\n".join(preview_lines).rstrip() + "\n")
    append_audit_event(
        project_dir,
        project_id,
        "generate_manuscript_references",
        "Manuscript references preview was generated without modifying draft.md.",
        {
            "status_file": "manuscript/references_status.json",
            "preview_file": "manuscript/references_section_preview.md",
            "verified_references": len(verified_references),
            "candidate_references": len(candidate_references),
            "placeholder_records": len(placeholder_records),
            "draft_modified": False,
        },
        source="api",
        event_category="literature",
        risk_level="low",
        entity_type="literature",
        entity_id="manuscript_references",
    )
    return status


def read_references_status(project_dir: Path, project_id: str) -> dict[str, Any]:
    path = references_status_path(project_dir)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return generate_manuscript_references(project_dir, project_id)


def read_references_preview(project_dir: Path, project_id: str) -> dict[str, Any]:
    if not references_preview_path(project_dir).exists():
        generate_manuscript_references(project_dir, project_id)
    return {
        "relative_path": "manuscript/references_section_preview.md",
        "content": references_preview_path(project_dir).read_text(encoding="utf-8")
        if references_preview_path(project_dir).exists()
        else "",
    }
