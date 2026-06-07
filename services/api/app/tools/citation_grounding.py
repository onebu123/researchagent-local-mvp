from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.literature_index import load_literature_index
from app.tools.literature_rag import build_literature_rag, read_rag_chunks


def citation_grounding_path(project_dir: Path) -> Path:
    return project_dir / "provenance" / "citation_grounding_report.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", text)
        if len(token) > 2
    }


def _entities(text: str) -> set[str]:
    return set(re.findall(r"\b[A-Z][A-Za-z0-9_-]{2,}\b", text))


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\b\d+(?:\.\d+)?\b", text))


def _read_evidence_claims(project_dir: Path) -> list[dict[str, Any]]:
    path = project_dir / "provenance" / "evidence.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _number_consistency(claim: str, excerpt: str) -> str:
    claim_numbers = _numbers(claim)
    excerpt_numbers = _numbers(excerpt)
    if not claim_numbers:
        return "not_applicable"
    if claim_numbers <= excerpt_numbers:
        return "match"
    return "mismatch"


def _ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return round(len(left & right) / max(len(left), 1), 4)


def _literature_by_id(project_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("literature_id")): entry
        for entry in load_literature_index(project_dir)
        if isinstance(entry, dict)
    }


def _pdf_quality_ok(entry: dict[str, Any] | None) -> bool:
    if not entry:
        return False
    if entry.get("source_type") != "pdf":
        return True
    if entry.get("quality_label") in {"low", "failed"}:
        return False
    quality_score = entry.get("quality_score")
    if isinstance(quality_score, (int, float)) and quality_score < 0.4:
        return False
    return True


def _select_chunk(claim: str, chunks: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float]:
    claim_tokens = _tokens(claim)
    best_chunk: dict[str, Any] | None = None
    best_score = -1.0
    for chunk in chunks:
        score = _ratio(claim_tokens, _tokens(str(chunk.get("text") or "")))
        if score > best_score:
            best_score = score
            best_chunk = chunk
    return best_chunk, max(best_score, 0.0)


def _grounding_strength(
    keyword_overlap: float,
    entity_overlap: float,
    number_consistency: str,
    metadata_verified: bool,
    pdf_quality_ok: bool,
    has_passage: bool,
) -> str:
    if not has_passage:
        return "unsupported"
    if number_consistency == "mismatch":
        return "unsupported"
    if not pdf_quality_ok:
        return "needs_human_review"
    if not metadata_verified:
        if keyword_overlap >= 0.3:
            return "weak"
        return "needs_human_review"
    if keyword_overlap >= 0.55 and entity_overlap >= 0.2:
        return "strong"
    if keyword_overlap >= 0.3:
        return "moderate"
    if keyword_overlap > 0:
        return "weak"
    return "unsupported"


def generate_citation_grounding_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    chunks = read_rag_chunks(project_dir)
    if not chunks:
        build_literature_rag(project_dir, project_id)
        chunks = read_rag_chunks(project_dir)
    literature_map = _literature_by_id(project_dir)
    items: list[dict[str, Any]] = []
    for index, claim in enumerate(_read_evidence_claims(project_dir), start=1):
        claim_text = str(claim.get("claim") or "")
        chunk, keyword_overlap = _select_chunk(claim_text, chunks)
        excerpt = str(chunk.get("text") or "") if chunk else ""
        literature_id = str(chunk.get("literature_id") or "") if chunk else None
        literature_entry = literature_map.get(str(literature_id))
        metadata_verified = bool(
            literature_entry
            and literature_entry.get("metadata_status") == "verified"
            and literature_entry.get("human_verified") is True
        )
        pdf_ok = _pdf_quality_ok(literature_entry)
        number_status = _number_consistency(claim_text, excerpt)
        entity_overlap = _ratio(_entities(claim_text), _entities(excerpt))
        strength = _grounding_strength(
            keyword_overlap,
            entity_overlap,
            number_status,
            metadata_verified,
            pdf_ok,
            bool(chunk and excerpt),
        )
        items.append(
            {
                "grounding_id": f"grounding_{index:04d}",
                "claim_id": claim.get("claim_id") or f"claim_{index:03d}",
                "claim": claim_text,
                "candidate_chunk_id": chunk.get("chunk_id") if chunk else None,
                "literature_id": literature_id,
                "source_file": chunk.get("source_file") if chunk else None,
                "text_excerpt": excerpt[:700],
                "grounding_strength": strength,
                "signals": {
                    "keyword_overlap": keyword_overlap,
                    "entity_overlap": entity_overlap,
                    "number_consistency": number_status,
                    "metadata_verified": metadata_verified,
                    "pdf_quality_ok": pdf_ok,
                    "llm_assisted": False,
                },
                "limitations": [
                    "Grounding strength is a heuristic and requires human review.",
                    "This report does not prove scientific truth or peer-review readiness.",
                ],
                "requires_human_review": strength != "strong",
            }
        )
    summary = {
        "total": len(items),
        "strong": sum(1 for item in items if item["grounding_strength"] == "strong"),
        "moderate": sum(1 for item in items if item["grounding_strength"] == "moderate"),
        "weak": sum(1 for item in items if item["grounding_strength"] == "weak"),
        "unsupported": sum(1 for item in items if item["grounding_strength"] == "unsupported"),
        "needs_human_review": sum(
            1 for item in items if item["grounding_strength"] == "needs_human_review"
        ),
    }
    report = {
        "generated_at": _utc_now(),
        "relative_path": "provenance/citation_grounding_report.json",
        "items": items,
        "summary": summary,
    }
    write_json(citation_grounding_path(project_dir), report)
    append_audit_event(
        project_dir,
        project_id,
        "generate_citation_grounding_report",
        "Citation grounding report was generated from local passages and metadata verification state.",
        {
            "report_file": "provenance/citation_grounding_report.json",
            "items": len(items),
            "strong": summary["strong"],
        },
        source="api",
        event_category="trust",
        risk_level="low",
        entity_type="evidence_claim",
        entity_id="citation_grounding",
    )
    return report


def read_citation_grounding_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    path = citation_grounding_path(project_dir)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return generate_citation_grounding_report(project_dir, project_id)
