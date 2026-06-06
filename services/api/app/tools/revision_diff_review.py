from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json
from app.tools.revision_line_diff import list_revision_line_diffs, load_revision_line_diff

ALLOWED_REVISION_DIFF_STATUSES = {"accepted", "rejected", "needs_rewrite", "needs_evidence"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reviews_path(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "revision_diffs" / "revision_diff_reviews.jsonl"


def _summary_path(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "revision_diffs" / "revision_diff_review_summary.json"


def _safe_revision_diff_id(value: str) -> str:
    cleaned = value.strip()
    if not re.fullmatch(r"revision_diff_\d{3,}", cleaned):
        raise ValueError("invalid revision_diff_id")
    return cleaned


def _safe_change_id(value: str) -> str:
    cleaned = value.strip()
    if not re.fullmatch(r"change_\d{3,}", cleaned):
        raise ValueError("invalid change_id")
    return cleaned


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


def read_revision_diff_reviews(project_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(_reviews_path(project_dir))


def _all_changes(project_dir: Path) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for diff in list_revision_line_diffs(project_dir):
        revision_diff_id = str(diff.get("revision_diff_id") or "")
        for change in diff.get("changes", []):
            if isinstance(change, dict) and isinstance(change.get("change_id"), str):
                changes.append(
                    {
                        "revision_diff_id": revision_diff_id,
                        "change_id": change["change_id"],
                        "before": change.get("before", ""),
                        "after": change.get("after", ""),
                        "related_issue_ids": change.get("related_issue_ids", []),
                        "related_claim_ids": change.get("related_claim_ids", []),
                    }
                )
    return changes


def generate_revision_diff_review_summary(project_dir: Path) -> dict[str, Any]:
    changes = _all_changes(project_dir)
    reviews = read_revision_diff_reviews(project_dir)
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    counts: dict[tuple[str, str], int] = {}
    for review in reviews:
        key = (str(review.get("revision_diff_id") or ""), str(review.get("change_id") or ""))
        counts[key] = counts.get(key, 0) + 1
        latest[key] = review

    records: list[dict[str, Any]] = []
    status_counts = {status: 0 for status in ALLOWED_REVISION_DIFF_STATUSES}
    for change in changes:
        key = (change["revision_diff_id"], change["change_id"])
        review = latest.get(key)
        status = review.get("human_status") if review else None
        if isinstance(status, str) and status in status_counts:
            status_counts[status] += 1
        records.append(
            {
                **change,
                "latest_human_status": status,
                "latest_reason": review.get("reason") if review else None,
                "review_count": counts.get(key, 0),
            }
        )

    reviewed = sum(1 for record in records if record["latest_human_status"])
    payload = {
        "generated_at": _utc_now(),
        "relative_path": "manuscript/revision_diffs/revision_diff_review_summary.json",
        "summary": {
            "total_changes": len(records),
            "reviewed": reviewed,
            "accepted": status_counts["accepted"],
            "rejected": status_counts["rejected"],
            "needs_rewrite": status_counts["needs_rewrite"],
            "needs_evidence": status_counts["needs_evidence"],
            "unreviewed": len(records) - reviewed,
        },
        "changes": records,
    }
    write_json(_summary_path(project_dir), payload)
    return payload


def record_revision_diff_review(
    project_dir: Path,
    project_id: str,
    revision_diff_id: str,
    change_id: str,
    human_status: str,
    reason: str,
    *,
    source: str = "api",
) -> dict[str, Any]:
    safe_revision_diff_id = _safe_revision_diff_id(revision_diff_id)
    safe_change_id = _safe_change_id(change_id)
    if human_status not in ALLOWED_REVISION_DIFF_STATUSES:
        raise ValueError("invalid human_status")
    diff = load_revision_line_diff(project_dir, safe_revision_diff_id)
    if not any(
        isinstance(change, dict) and change.get("change_id") == safe_change_id
        for change in diff.get("changes", [])
    ):
        raise FileNotFoundError(f"revision diff change does not exist: {safe_change_id}")

    records = read_revision_diff_reviews(project_dir)
    record = {
        "review_id": f"rev_diff_review_{len(records) + 1:03d}",
        "revision_diff_id": safe_revision_diff_id,
        "change_id": safe_change_id,
        "human_status": human_status,
        "reason": reason,
        "created_at": _utc_now(),
        "source": source,
    }
    _append_jsonl(_reviews_path(project_dir), record)
    summary = generate_revision_diff_review_summary(project_dir)
    append_audit_event(
        project_dir,
        project_id,
        "record_revision_diff_review",
        "Revision diff review status was recorded without modifying manuscript files.",
        {
            "review_id": record["review_id"],
            "revision_diff_id": safe_revision_diff_id,
            "change_id": safe_change_id,
            "human_status": human_status,
            "manuscript_modified": False,
        },
        source=source,
    )
    return {**record, "summary": summary}
