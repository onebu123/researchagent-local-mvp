from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.literature_rag import read_rag_answers, read_rag_chunks


def source_passage_evidence_path(project_dir: Path) -> Path:
    return project_dir / "provenance" / "source_passage_evidence.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _review_status(metadata_status: str | None, human_verified: bool) -> str:
    if metadata_status == "verified" and human_verified:
        return "supported"
    if metadata_status == "placeholder":
        return "needs_human_review"
    return "partial"


def generate_source_passage_evidence(project_dir: Path, project_id: str) -> dict[str, Any]:
    chunks_by_id = {
        str(chunk.get("chunk_id")): chunk
        for chunk in read_rag_chunks(project_dir)
        if isinstance(chunk.get("chunk_id"), str)
    }
    records: list[dict[str, Any]] = []
    for answer in read_rag_answers(project_dir):
        answer_id = str(answer.get("answer_id", "rag_answer_unknown"))
        for index, passage in enumerate(answer.get("source_passages", []), start=1):
            if not isinstance(passage, dict):
                continue
            chunk_id = str(passage.get("chunk_id") or "")
            chunk = chunks_by_id.get(chunk_id)
            if not chunk:
                continue
            metadata_status = str(chunk.get("metadata_status") or "placeholder")
            human_verified = bool(chunk.get("human_verified"))
            records.append(
                {
                    "evidence_id": f"source_passage_{len(records) + 1:04d}",
                    "answer_id": answer_id,
                    "question": answer.get("question"),
                    "chunk_id": chunk_id,
                    "literature_id": chunk.get("literature_id"),
                    "source_file": chunk.get("source_file"),
                    "title": chunk.get("title"),
                    "metadata_status": metadata_status,
                    "human_verified": human_verified,
                    "support_status": _review_status(metadata_status, human_verified),
                    "excerpt": chunk.get("text", ""),
                    "notes": [
                        "Evidence is linked to a local RAG chunk.",
                        "Placeholder or unverified metadata requires human review before formal citation.",
                    ],
                }
            )
    report = {
        "generated_at": _utc_now(),
        "relative_path": "provenance/source_passage_evidence.json",
        "source_chunks_file": "literature/rag/chunks.jsonl",
        "source_answers_file": "literature/rag/rag_answers.jsonl",
        "records": records,
        "summary": {
            "records": len(records),
            "supported": sum(1 for item in records if item["support_status"] == "supported"),
            "partial": sum(1 for item in records if item["support_status"] == "partial"),
            "needs_human_review": sum(
                1 for item in records if item["support_status"] == "needs_human_review"
            ),
        },
    }
    write_json(source_passage_evidence_path(project_dir), report)
    append_audit_event(
        project_dir,
        project_id,
        "generate_source_passage_evidence",
        "Source passage evidence was generated from local RAG chunks.",
        {
            "report_file": "provenance/source_passage_evidence.json",
            "record_count": len(records),
        },
        source="api",
        event_category="literature",
        risk_level="low",
        entity_type="evidence_claim",
        entity_id="source_passage_evidence",
    )
    return report


def read_source_passage_evidence(project_dir: Path, project_id: str) -> dict[str, Any]:
    path = source_passage_evidence_path(project_dir)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return generate_source_passage_evidence(project_dir, project_id)
