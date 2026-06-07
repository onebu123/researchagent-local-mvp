from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json, write_text
from app.tools.literature_index import load_literature_index
from app.tools.prompt_registry import load_prompt

PROMPT_VERSION = "bibtex_generation_v1"


def references_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "references.bib"


def report_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "bibtex_report.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _escape_bibtex(value: str) -> str:
    return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _entry_key(entry: dict[str, Any]) -> str:
    literature_id = str(entry.get("literature_id") or "lit")
    title = re.sub(r"[^A-Za-z0-9]+", "", str(entry.get("title") or ""))[:24]
    return f"{literature_id}_{title or 'reference'}"


def _formal_entry(entry: dict[str, Any]) -> str:
    fields: list[tuple[str, str]] = []
    title = str(entry.get("title") or "").strip()
    if title:
        fields.append(("title", title))
    authors = entry.get("authors")
    if isinstance(authors, list) and authors:
        author_value = " and ".join(str(author) for author in authors if str(author).strip())
        if author_value:
            fields.append(("author", author_value))
    if entry.get("year") is not None:
        fields.append(("year", str(entry["year"])))
    if entry.get("journal"):
        fields.append(("journal", str(entry["journal"])))
    if entry.get("doi"):
        fields.append(("doi", str(entry["doi"])))
    lines = [f"@misc{{{_entry_key(entry)},"]
    for index, (key, value) in enumerate(fields):
        suffix = "," if index < len(fields) - 1 else ""
        lines.append(f"  {key} = {{{_escape_bibtex(value)}}}{suffix}")
    lines.append("}")
    return "\n".join(lines)


def generate_bibtex(project_dir: Path, project_id: str) -> dict[str, Any]:
    prompt = load_prompt(PROMPT_VERSION)
    entries = load_literature_index(project_dir)
    written: list[dict[str, Any]] = []
    candidate_records: list[dict[str, Any]] = []
    rejected_records: list[dict[str, Any]] = []
    placeholder_records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    bib_blocks: list[str] = [
        "% ResearchAgent v1.2 BibTeX draft.",
        "% Formal entries require metadata_status=verified, human_verified=true, and reference_verification_status=approved.",
        "% Candidate, rejected, placeholder, or unverified records are comments only.",
        "",
    ]
    for entry in entries:
        literature_id = str(entry.get("literature_id"))
        approved = (
            entry.get("metadata_status") == "verified"
            and bool(entry.get("human_verified"))
            and entry.get("reference_verification_status") == "approved"
        )
        if approved:
            bib_blocks.append(_formal_entry(entry))
            bib_blocks.append("")
            written.append(
                {
                    "literature_id": literature_id,
                    "source_file": entry.get("source_file"),
                    "entry_key": _entry_key(entry),
                }
            )
            continue
        if entry.get("reference_verification_status") == "rejected":
            reason = "reference verification was rejected"
            bucket = rejected_records
        elif entry.get("reference_verification_id") or (
            entry.get("metadata_status") == "verified" and bool(entry.get("human_verified"))
        ):
            reason = "reference candidate has not been approved and applied"
            bucket = candidate_records
        else:
            reason = "metadata is not approved by the reference verification workflow"
            bucket = placeholder_records
        skipped_record = {
            "literature_id": literature_id,
            "title": entry.get("title"),
            "source_file": entry.get("source_file"),
            "metadata_status": entry.get("metadata_status"),
            "human_verified": bool(entry.get("human_verified")),
            "reference_verification_status": entry.get("reference_verification_status"),
            "reason": reason,
        }
        skipped.append(skipped_record)
        bucket.append(skipped_record)
        bib_blocks.append(
            f"% Skipped {literature_id}: {entry.get('title') or 'untitled reference'}; "
            f"{reason}. Source: {entry.get('source_file')}"
        )
    write_text(references_path(project_dir), "\n".join(bib_blocks).rstrip() + "\n")
    report = {
        "generated_at": _utc_now(),
        "relative_path": "literature/bibtex_report.json",
        "bibtex_file": "literature/references.bib",
        "prompt_version": prompt["prompt_version"],
        "formal_entries": len(written),
        "approved_entries": len(written),
        "candidate_records": len(candidate_records),
        "rejected_records": len(rejected_records),
        "placeholder_records": len(placeholder_records),
        "skipped_records": len(skipped),
        "written": written,
        "skipped": skipped,
        "candidates": candidate_records,
        "rejected": rejected_records,
        "placeholders": placeholder_records,
        "warnings": [
            "Formal BibTeX entries are generated only from approved human-verified verified metadata.",
            "Reference verification candidates do not become formal entries until approval is applied.",
            "Missing authors, journal, year, pages, DOI, and publisher are not fabricated.",
        ],
    }
    write_json(report_path(project_dir), report)
    append_audit_event(
        project_dir,
        project_id,
        "generate_bibtex_draft",
        "BibTeX draft was generated with approved-reference-only formal entries.",
        {
            "bibtex_file": "literature/references.bib",
            "report_file": "literature/bibtex_report.json",
            "formal_entries": len(written),
            "skipped_records": len(skipped),
        },
        source="api",
        event_category="literature",
        risk_level="low",
        entity_type="literature",
        entity_id="bibtex",
    )
    return report


def read_bibtex(project_dir: Path, project_id: str) -> dict[str, Any]:
    if not references_path(project_dir).exists() or not report_path(project_dir).exists():
        report = generate_bibtex(project_dir, project_id)
    else:
        payload = json.loads(report_path(project_dir).read_text(encoding="utf-8"))
        report = payload if isinstance(payload, dict) else generate_bibtex(project_dir, project_id)
    return {
        "bibtex": references_path(project_dir).read_text(encoding="utf-8")
        if references_path(project_dir).exists()
        else "",
        "report": report,
    }
