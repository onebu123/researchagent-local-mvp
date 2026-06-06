from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json

ALLOWED_EVIDENCE_CLAIM_STATUSES = {
    "supported",
    "partially_supported",
    "unsupported",
    "needs_more_evidence",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _evidence_path(project_dir: Path) -> Path:
    return project_dir / "provenance" / "evidence.json"


def _reviews_path(project_dir: Path) -> Path:
    return project_dir / "provenance" / "evidence_claim_reviews.jsonl"


def _summary_path(project_dir: Path) -> Path:
    return project_dir / "provenance" / "evidence_claim_review_summary.json"


def _safe_claim_id(value: str) -> str:
    cleaned = value.strip()
    if not re.fullmatch(r"claim_\d{3,}", cleaned):
        raise ValueError("invalid claim_id")
    return cleaned


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_evidence_claims(project_dir: Path) -> list[dict[str, Any]]:
    path = _evidence_path(project_dir)
    if not path.exists():
        raise FileNotFoundError("provenance/evidence.json does not exist")
    payload = _read_json(path, [])
    if not isinstance(payload, list):
        raise ValueError("provenance/evidence.json must be a list")
    return [item for item in payload if isinstance(item, dict)]


def read_evidence_claim_reviews(project_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(_reviews_path(project_dir))


def _related_files(claim: dict[str, Any]) -> list[str]:
    fields = [
        "data_file",
        "analysis_file",
        "analysis_provenance_file",
        "figure_file",
        "figure_provenance_file",
        "manuscript_file",
    ]
    result: list[str] = []
    for field in fields:
        value = claim.get(field)
        if isinstance(value, str) and value:
            result.append(value)
    return result


def generate_evidence_claim_review_summary(project_dir: Path) -> dict[str, Any]:
    claims = read_evidence_claims(project_dir)
    reviews = read_evidence_claim_reviews(project_dir)
    latest: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}
    status_counts = {status: 0 for status in ALLOWED_EVIDENCE_CLAIM_STATUSES}

    for review in reviews:
        claim_id = str(review.get("claim_id") or "")
        counts[claim_id] = counts.get(claim_id, 0) + 1
        latest[claim_id] = review

    records: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = str(claim.get("claim_id") or "")
        review = latest.get(claim_id)
        status = review.get("human_status") if review else None
        if isinstance(status, str) and status in status_counts:
            status_counts[status] += 1
        records.append(
            {
                "claim_id": claim_id,
                "section": claim.get("section"),
                "claim": claim.get("claim"),
                "evidence_type": claim.get("evidence_type"),
                "evidence_status": claim.get("evidence_status"),
                "latest_human_status": status,
                "latest_reason": review.get("reason") if review else None,
                "review_count": counts.get(claim_id, 0),
                "related_files": _related_files(claim),
            }
        )

    reviewed = sum(1 for record in records if record["latest_human_status"])
    payload = {
        "generated_at": _utc_now(),
        "relative_path": "provenance/evidence_claim_review_summary.json",
        "summary": {
            "total_claims": len(records),
            "reviewed": reviewed,
            "supported": status_counts["supported"],
            "partially_supported": status_counts["partially_supported"],
            "unsupported": status_counts["unsupported"],
            "needs_more_evidence": status_counts["needs_more_evidence"],
            "unreviewed": len(records) - reviewed,
        },
        "claims": records,
    }
    write_json(_summary_path(project_dir), payload)
    return payload


def record_evidence_claim_review(
    project_dir: Path,
    project_id: str,
    claim_id: str,
    human_status: str,
    reason: str,
    *,
    source: str = "api",
) -> dict[str, Any]:
    safe_claim_id = _safe_claim_id(claim_id)
    if human_status not in ALLOWED_EVIDENCE_CLAIM_STATUSES:
        raise ValueError("invalid evidence claim human_status")
    claims = read_evidence_claims(project_dir)
    claim = next((item for item in claims if item.get("claim_id") == safe_claim_id), None)
    if claim is None:
        raise FileNotFoundError(f"evidence claim does not exist: {safe_claim_id}")

    reviews = read_evidence_claim_reviews(project_dir)
    record = {
        "review_id": f"evidence_claim_review_{len(reviews) + 1:03d}",
        "claim_id": safe_claim_id,
        "human_status": human_status,
        "reason": reason,
        "related_files": _related_files(claim),
        "created_at": _utc_now(),
        "source": source,
        "evidence_modified": False,
    }
    _append_jsonl(_reviews_path(project_dir), record)
    summary = generate_evidence_claim_review_summary(project_dir)
    append_audit_event(
        project_dir,
        project_id,
        "record_evidence_claim_review",
        "Evidence claim human review status was recorded without modifying evidence.json.",
        {
            "review_id": record["review_id"],
            "claim_id": safe_claim_id,
            "human_status": human_status,
            "evidence_modified": False,
        },
        source=source,
        event_category="trust",
        risk_level="medium",
        entity_type="evidence_claim",
        entity_id=safe_claim_id,
    )
    return {**record, "summary": summary}
