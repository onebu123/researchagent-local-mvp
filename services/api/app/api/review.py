from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas import IssueResolutionReviewRequest, RevisionDecisionRequest
from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import storage_service
from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir
from app.tools.issue_resolution import (
    load_or_generate_issue_resolution,
    read_issue_resolution_reviews,
    record_issue_resolution_review,
)

router = APIRouter()


def _project_dir(project_id: str) -> Path:
    try:
        project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return storage_service.project_dir(project_id)


def _review_path(project_id: str) -> Path:
    project_dir = _project_dir(project_id)
    return storage_service.ensure_inside_project(
        project_id, project_dir / "reviews" / "review_report.json"
    )


def _decisions_path(project_id: str) -> Path:
    project_dir = _project_dir(project_id)
    return storage_service.ensure_inside_project(
        project_id, project_dir / "reviews" / "revision_decisions.jsonl"
    )


def _read_review(project_id: str) -> dict[str, Any]:
    path = _review_path(project_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="reviews/review_report.json does not exist")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="review_report.json is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="review_report.json must be an object")
    return payload


def _read_decisions(path: Path) -> list[dict[str, Any]]:
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


def _find_issue(review: dict[str, Any], issue_id: str) -> dict[str, Any]:
    issues = review.get("sentence_issues")
    if not isinstance(issues, list):
        raise HTTPException(status_code=400, detail="review_report.json sentence_issues must be a list")
    for issue in issues:
        if isinstance(issue, dict) and issue.get("issue_id") == issue_id:
            return issue
    raise HTTPException(status_code=404, detail=f"sentence issue not found: {issue_id}")


@router.post("/projects/{project_id}/review/sentence-issues/{issue_id}/decision")
def create_revision_decision(
    project_id: str,
    issue_id: str,
    payload: RevisionDecisionRequest,
) -> dict[str, Any]:
    review = _read_review(project_id)
    issue = _find_issue(review, issue_id)
    revision_diff = issue.get("revision_diff") if isinstance(issue.get("revision_diff"), dict) else {}
    decisions_path = _decisions_path(project_id)
    decisions = _read_decisions(decisions_path)
    record = {
        "decision_id": f"rev_decision_{len(decisions) + 1:04d}",
        "issue_id": issue_id,
        "decision": payload.decision,
        "before": revision_diff.get("before") or issue.get("sentence", ""),
        "after": revision_diff.get("after") or issue.get("suggested_revision", ""),
        "reason": payload.reason or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "api",
        "applied_to_manuscript": False,
    }
    ensure_dir(decisions_path.parent)
    with decisions_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    append_audit_event(
        _project_dir(project_id),
        project_id,
        "create_revision_decision",
        "Revision decision was recorded without modifying manuscript.",
        {
            "issue_id": issue_id,
            "decision": payload.decision,
            "applied_to_manuscript": False,
        },
        source="api",
    )
    return record


@router.get("/projects/{project_id}/review/revision-decisions")
def get_revision_decisions(project_id: str) -> list[dict[str, Any]]:
    _read_review(project_id)
    return _read_decisions(_decisions_path(project_id))


@router.get("/projects/{project_id}/review/issue-resolution")
def get_issue_resolution(project_id: str) -> dict[str, Any]:
    _read_review(project_id)
    return load_or_generate_issue_resolution(_project_dir(project_id), project_id)


@router.get("/projects/{project_id}/review/issue-resolution/reviews")
def get_issue_resolution_reviews(project_id: str) -> list[dict[str, Any]]:
    _read_review(project_id)
    return read_issue_resolution_reviews(_project_dir(project_id))


@router.post("/projects/{project_id}/review/issue-resolution/{issue_id}/review")
def create_issue_resolution_review(
    project_id: str,
    issue_id: str,
    payload: IssueResolutionReviewRequest,
) -> dict[str, Any]:
    _read_review(project_id)
    try:
        return record_issue_resolution_review(
            _project_dir(project_id),
            project_id,
            issue_id,
            payload.version_id,
            payload.human_status,
            payload.reason or "",
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
