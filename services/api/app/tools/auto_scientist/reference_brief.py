from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.auto_scientist.contracts import (
    SCHEMA_PREFIX,
    ensure_auto_scientist_dirs,
    utc_now,
    write_project_json,
    write_project_text,
)
from app.tools.literature_index import load_literature_index
from app.tools.literature_rag import build_literature_rag, read_rag_chunks

REFERENCE_BRIEF_JSON = "auto_scientist/reference_brief.json"
REFERENCE_BRIEF_MD = "auto_scientist/reference_brief.md"
MAX_REFERENCE_LITERATURE_IDS = 10


def _normalize_literature_ids(literature_ids: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for item in literature_ids or []:
        value = str(item).strip()
        if not value:
            continue
        if "/" in value or "\\" in value or ".." in value:
            raise ValueError("reference_literature_ids must contain literature identifiers, not paths")
        if value not in cleaned:
            cleaned.append(value)
    if len(cleaned) > MAX_REFERENCE_LITERATURE_IDS:
        raise ValueError(f"reference_literature_ids supports at most {MAX_REFERENCE_LITERATURE_IDS} entries")
    return cleaned


def _metadata_warnings(entry: dict[str, Any], source_passage_count: int) -> list[str]:
    warnings: list[str] = []
    metadata_status = str(entry.get("metadata_status") or "unknown")
    if metadata_status != "verified":
        warnings.append("metadata is placeholder, extracted, or otherwise not verified")
    if entry.get("human_verified") is not True:
        warnings.append("metadata has not been human verified")
    if entry.get("reference_verification_status") != "approved":
        warnings.append("reference metadata has not been approved for formal References")
    if source_passage_count <= 0:
        warnings.append("no local RAG source passage is available for this reference")
    if entry.get("source_type") == "pdf" and (
        entry.get("quality_label") in {"low", "failed"} or entry.get("needs_manual_review") is True
    ):
        warnings.append("PDF parser quality requires manual review")
    return warnings


def _verified_source(entry: dict[str, Any]) -> bool:
    return (
        entry.get("metadata_status") == "verified"
        and entry.get("human_verified") is True
        and entry.get("reference_verification_status") == "approved"
    )


def _passage_excerpt(text: Any) -> str:
    cleaned = " ".join(str(text or "").split())
    return cleaned[:600]


def _record_for_reference(entry: dict[str, Any], chunks: list[dict[str, Any]]) -> dict[str, Any]:
    literature_id = str(entry.get("literature_id") or "")
    related_chunks = [chunk for chunk in chunks if str(chunk.get("literature_id") or "") == literature_id]
    source_passages = [
        {
            "chunk_id": chunk.get("chunk_id"),
            "source_file": chunk.get("source_file"),
            "title": chunk.get("title"),
            "position_label": chunk.get("position_label"),
            "source_locator": chunk.get("source_locator"),
            "metadata_status": chunk.get("metadata_status"),
            "human_verified": bool(chunk.get("human_verified")),
            "metadata_trust_level": chunk.get("metadata_trust_level"),
            "evidence_warning_flags": chunk.get("evidence_warning_flags", []),
            "excerpt": _passage_excerpt(chunk.get("text")),
        }
        for chunk in related_chunks[:3]
    ]
    warnings = _metadata_warnings(entry, len(source_passages))
    return {
        "literature_id": literature_id,
        "title": entry.get("title"),
        "authors": entry.get("authors") if isinstance(entry.get("authors"), list) else [],
        "year": entry.get("year"),
        "doi": entry.get("doi"),
        "journal": entry.get("journal"),
        "source_file": entry.get("source_file"),
        "source_type": entry.get("source_type"),
        "metadata_status": entry.get("metadata_status"),
        "human_verified": bool(entry.get("human_verified")),
        "reference_verification_status": entry.get("reference_verification_status"),
        "reference_verification_id": entry.get("reference_verification_id"),
        "verified_source": _verified_source(entry),
        "coverage": {
            "source_passage_count": len(source_passages),
            "has_local_source_passages": bool(source_passages),
            "placeholder_or_unverified_metadata": bool(warnings),
        },
        "source_passages": source_passages,
        "warnings": warnings,
    }


def _markdown_report(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Auto Scientist Reference Brief",
        "",
        "> This brief is bounded to user-selected local references. It is not novelty review, citation verification, peer review, scientific proof, or publication readiness.",
        "",
        "## Summary",
        "",
        f"- Selected references: {summary.get('reference_count', 0)}",
        f"- Verified sources: {summary.get('verified_source_count', 0)}",
        f"- Placeholder or unverified records: {summary.get('placeholder_metadata_count', 0)}",
        f"- Local source passages: {summary.get('source_passage_count', 0)}",
        "",
        "## References",
        "",
    ]
    for record in payload.get("records", []):
        if not isinstance(record, dict):
            continue
        lines.extend(
            [
                f"### {record.get('literature_id')}: {record.get('title') or 'Untitled local reference'}",
                "",
                f"- Source file: {record.get('source_file')}",
                f"- Metadata status: {record.get('metadata_status')} / human_verified={record.get('human_verified')}",
                f"- Approved formal reference: {record.get('reference_verification_status') == 'approved'}",
                f"- Local source passages: {(record.get('coverage') or {}).get('source_passage_count', 0)}",
            ]
        )
        warnings = [str(item) for item in record.get("warnings", []) if item]
        if warnings:
            lines.append(f"- Review warning: {'; '.join(warnings)}")
        passages = [item for item in record.get("source_passages", []) if isinstance(item, dict)]
        for passage in passages[:2]:
            lines.append(
                f"- Passage {passage.get('chunk_id')} ({passage.get('position_label') or passage.get('source_locator')}): {passage.get('excerpt')}"
            )
        lines.append("")
    lines.extend(
        [
            "## Limitations",
            "",
            "- Only local `literature_index.json`, parsed literature text, and local RAG chunks are used.",
            "- Placeholder, extracted, or unapproved metadata remains a review warning.",
            "- This brief does not add, modify, or approve formal references.",
        ]
    )
    return "\n".join(lines)


def build_reference_brief(
    project_dir: Path,
    project_id: str,
    reference_literature_ids: list[str] | None,
) -> dict[str, Any]:
    selected_ids = _normalize_literature_ids(reference_literature_ids)
    ensure_auto_scientist_dirs(project_dir)
    index = load_literature_index(project_dir)
    by_id = {str(entry.get("literature_id") or ""): entry for entry in index if isinstance(entry, dict)}
    missing = [literature_id for literature_id in selected_ids if literature_id not in by_id]
    if missing:
        raise ValueError(f"literature_id not found: {', '.join(missing)}")

    chunks = read_rag_chunks(project_dir)
    if selected_ids and not chunks:
        build_literature_rag(project_dir, project_id)
        chunks = read_rag_chunks(project_dir)

    records = [_record_for_reference(by_id[literature_id], chunks) for literature_id in selected_ids]
    warning_count = sum(len(record["warnings"]) for record in records)
    source_passage_count = sum(int(record["coverage"]["source_passage_count"]) for record in records)
    payload = {
        "schema_version": f"{SCHEMA_PREFIX}.reference_brief.v1",
        "project_id": project_id,
        "created_at": utc_now(),
        "relative_path": REFERENCE_BRIEF_JSON,
        "markdown_file": REFERENCE_BRIEF_MD,
        "source_index_file": "literature/literature_index.json",
        "source_chunks_file": "literature/rag/chunks.jsonl",
        "reference_literature_ids": selected_ids,
        "records": records,
        "summary": {
            "reference_count": len(records),
            "verified_source_count": sum(1 for record in records if record["verified_source"]),
            "placeholder_metadata_count": sum(1 for record in records if record["warnings"]),
            "source_passage_count": source_passage_count,
            "review_warning_count": warning_count,
        },
        "warnings": [
            warning
            for record in records
            for warning in [f"{record['literature_id']}: {item}" for item in record["warnings"]]
        ],
        "limitations": [
            "Reference-based ideation uses only user-selected local literature records and local source passages.",
            "Reference coverage is a local review signal, not novelty review, scientific validity, citation verification, peer review, or publication readiness.",
            "The brief never modifies literature_index.json and never approves candidate references.",
        ],
    }
    write_project_json(project_dir, REFERENCE_BRIEF_JSON, payload)
    write_project_text(project_dir, REFERENCE_BRIEF_MD, _markdown_report(payload))
    append_audit_event(
        project_dir,
        project_id,
        "build_auto_scientist_reference_brief",
        "Auto Scientist reference brief was generated from selected local literature records.",
        {
            "reference_brief_file": REFERENCE_BRIEF_JSON,
            "reference_count": len(records),
            "review_warning_count": warning_count,
            "source_passage_count": source_passage_count,
            "literature_index_modified": False,
        },
        source="api",
        event_category="agent",
        risk_level="medium" if warning_count else "low",
        entity_type="auto_scientist",
        entity_id="reference_brief",
    )
    return payload
