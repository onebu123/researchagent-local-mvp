from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.revision_diff_review import read_revision_diff_reviews
from app.tools.revision_line_diff import list_revision_line_diffs


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summary_path(project_dir: Path) -> Path:
    return project_dir / "reviews" / "reviewer_closure_summary.json"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _sentence_issues(project_dir: Path) -> list[dict[str, Any]]:
    payload = _read_json(project_dir / "reviews" / "review_report.json", {})
    issues = payload.get("sentence_issues") if isinstance(payload, dict) else []
    return [item for item in issues if isinstance(item, dict)] if isinstance(issues, list) else []


def _linked_changes(project_dir: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for diff in list_revision_line_diffs(project_dir):
        revision_diff_id = str(diff.get("revision_diff_id") or "")
        for change in diff.get("changes", []):
            if not isinstance(change, dict):
                continue
            for issue_id in change.get("related_issue_ids", []):
                if not isinstance(issue_id, str):
                    continue
                result.setdefault(issue_id, []).append(
                    {
                        "revision_diff_id": revision_diff_id,
                        "change_id": change.get("change_id"),
                        "before": change.get("before"),
                        "after": change.get("after"),
                    }
                )
    return result


def _latest_reviews(project_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for review in read_revision_diff_reviews(project_dir):
        revision_diff_id = str(review.get("revision_diff_id") or "")
        change_id = str(review.get("change_id") or "")
        latest[(revision_diff_id, change_id)] = review
    return latest


def _closure_status(
    changes: list[dict[str, Any]],
    latest_reviews: dict[tuple[str, str], dict[str, Any]],
) -> tuple[str, dict[str, Any] | None, str]:
    if not changes:
        return "unlinked", None, "No revision diff change is linked to this reviewer issue."
    reviewed: list[dict[str, Any]] = []
    for change in changes:
        review = latest_reviews.get(
            (str(change.get("revision_diff_id") or ""), str(change.get("change_id") or ""))
        )
        if review:
            reviewed.append(review)
    if not reviewed:
        return "open", None, "Linked revision diff change still lacks human review."
    review = reviewed[-1]
    status = review.get("human_status")
    if status == "accepted":
        return (
            "closed",
            review,
            "Linked revision change was accepted by a human reviewer. This is workflow closure only.",
        )
    if status == "needs_evidence":
        return "needs_evidence", review, "Linked revision change needs additional evidence."
    if status == "needs_rewrite":
        return "needs_rewrite", review, "Linked revision change needs rewrite before closure."
    if status == "rejected":
        return "rejected", review, "Linked revision change was rejected."
    return "open", review, "Linked revision change is not closed."


def generate_reviewer_closure_summary(project_dir: Path, project_id: str) -> dict[str, Any]:
    issues = _sentence_issues(project_dir)
    changes_by_issue = _linked_changes(project_dir)
    latest = _latest_reviews(project_dir)
    counts = {
        "closed": 0,
        "open": 0,
        "unlinked": 0,
        "needs_evidence": 0,
        "needs_rewrite": 0,
        "rejected": 0,
    }
    records: list[dict[str, Any]] = []
    for issue in issues:
        issue_id = str(issue.get("issue_id") or "")
        changes = changes_by_issue.get(issue_id, [])
        status, review, reason = _closure_status(changes, latest)
        counts[status] = counts.get(status, 0) + 1
        records.append(
            {
                "issue_id": issue_id,
                "issue_type": issue.get("issue_type"),
                "severity": issue.get("severity"),
                "sentence": issue.get("sentence"),
                "closure_status": status,
                "linked_changes": changes,
                "latest_revision_review": review,
                "reason": reason,
            }
        )

    payload = {
        "generated_at": _utc_now(),
        "relative_path": "reviews/reviewer_closure_summary.json",
        "summary": {
            "total_sentence_issues": len(records),
            **counts,
        },
        "issues": records,
        "notes": [
            "Closed means a linked revision diff change was accepted in this local workflow.",
            "It does not prove the scientific claim or reviewer concern is semantically resolved.",
        ],
    }
    write_json(_summary_path(project_dir), payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_reviewer_closure_summary",
        "Reviewer issue closure summary was generated from existing issues and revision reviews.",
        {
            "summary_file": "reviews/reviewer_closure_summary.json",
            "total_sentence_issues": len(records),
            "closed": counts["closed"],
            "open": counts["open"],
        },
        source="api",
        event_category="trust",
        risk_level="low",
        entity_type="trust",
        entity_id="reviewer_closure_summary",
    )
    return payload
