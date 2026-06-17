from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas import HumanReviewDecisionRequest
from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import storage_service
from app.tools.human_review_queue import read_human_review_queue, record_human_review_decision

router = APIRouter()


def _project_dir(project_id: str):
    try:
        project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return storage_service.project_dir(project_id)


@router.get("/projects/{project_id}/human-review-queue")
def get_human_review_queue(project_id: str) -> dict[str, Any]:
    return read_human_review_queue(_project_dir(project_id), project_id)


@router.post("/projects/{project_id}/human-review-queue/{review_id}/decision")
def decide_human_review_item(
    project_id: str,
    review_id: str,
    payload: HumanReviewDecisionRequest,
) -> dict[str, Any]:
    try:
        return record_human_review_decision(
            _project_dir(project_id),
            project_id,
            review_id,
            payload.decision,
            payload.reason or "",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
