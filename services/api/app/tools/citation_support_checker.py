from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.literature_rag import read_rag_chunks
from app.tools.prompt_registry import load_prompt
from app.tools.source_passage_evidence import read_source_passage_evidence

PROMPT_VERSION = "citation_support_v1"


def citation_support_path(project_dir: Path) -> Path:
    return project_dir / "provenance" / "citation_support_report.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", text)
        if len(token) > 2
    }


def _read_evidence_claims(project_dir: Path) -> list[dict[str, Any]]:
    path = project_dir / "provenance" / "evidence.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _status_for_overlap(overlap: int, chunk: dict[str, Any] | None) -> str:
    if overlap <= 0 or chunk is None:
        return "unsupported"
    metadata_status = chunk.get("metadata_status")
    human_verified = bool(chunk.get("human_verified"))
    if metadata_status == "verified" and human_verified:
        return "supported" if overlap >= 3 else "partial"
    if metadata_status == "placeholder":
        return "needs_human_review"
    return "partial"


def generate_citation_support_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    prompt = load_prompt(PROMPT_VERSION)
    chunks = read_rag_chunks(project_dir)
    source_passage_evidence = read_source_passage_evidence(project_dir, project_id)
    source_evidence_by_chunk = {
        str(record.get("chunk_id")): record
        for record in source_passage_evidence.get("records", [])
        if isinstance(record, dict)
    }
    records: list[dict[str, Any]] = []
    for claim in _read_evidence_claims(project_dir):
        claim_text = str(claim.get("claim") or "")
        claim_tokens = _tokens(claim_text)
        best_chunk: dict[str, Any] | None = None
        best_overlap = 0
        for chunk in chunks:
            overlap = len(claim_tokens & _tokens(str(chunk.get("text") or "")))
            if overlap > best_overlap:
                best_overlap = overlap
                best_chunk = chunk
        status = _status_for_overlap(best_overlap, best_chunk)
        matched_chunk_ids = [str(best_chunk["chunk_id"])] if best_chunk and best_overlap > 0 else []
        notes = [
            "Status is based on local text overlap and source passage evidence, not scientific proof.",
            "Human review is required before using a citation in a manuscript.",
        ]
        if best_chunk and best_chunk.get("metadata_status") == "placeholder":
            notes.append("Matched source metadata is placeholder; status is capped at needs_human_review.")
        records.append(
            {
                "claim_id": claim.get("claim_id"),
                "claim": claim_text,
                "status": status,
                "matched_chunk_ids": matched_chunk_ids,
                "overlap_terms": best_overlap,
                "source_passage_evidence_ids": [
                    source_evidence_by_chunk[chunk_id]["evidence_id"]
                    for chunk_id in matched_chunk_ids
                    if chunk_id in source_evidence_by_chunk
                ],
                "notes": notes,
            }
        )
    report = {
        "generated_at": _utc_now(),
        "relative_path": "provenance/citation_support_report.json",
        "prompt_version": prompt["prompt_version"],
        "source_chunks_file": "literature/rag/chunks.jsonl",
        "source_passage_evidence_file": "provenance/source_passage_evidence.json",
        "records": records,
        "summary": {
            "claims_checked": len(records),
            "supported": sum(1 for item in records if item["status"] == "supported"),
            "partial": sum(1 for item in records if item["status"] == "partial"),
            "unsupported": sum(1 for item in records if item["status"] == "unsupported"),
            "needs_human_review": sum(1 for item in records if item["status"] == "needs_human_review"),
        },
        "limitations": [
            "This report checks local passage support only.",
            "It does not verify scientific truth, causal inference, statistical significance, or peer review.",
        ],
    }
    write_json(citation_support_path(project_dir), report)
    append_audit_event(
        project_dir,
        project_id,
        "generate_citation_support_report",
        "Citation support report was generated from local RAG/source passage evidence.",
        {
            "report_file": "provenance/citation_support_report.json",
            "claims_checked": len(records),
        },
        source="api",
        event_category="trust",
        risk_level="low",
        entity_type="evidence_claim",
        entity_id="citation_support",
    )
    return report


def read_citation_support_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    path = citation_support_path(project_dir)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return generate_citation_support_report(project_dir, project_id)
