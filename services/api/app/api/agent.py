from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.project_service import ProjectNotFoundError
from app.tools.iterative_research_loop import (
    read_agent_runs,
    read_iterative_research_loop_latest,
    run_iterative_research_loop,
)

router = APIRouter()


class IterativeLoopRequest(BaseModel):
    max_rounds: int = Field(default=2, ge=1, le=5)
    topic: str | None = None
    research_question: str | None = None


def _not_found(exc: ProjectNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.post("/projects/{project_id}/agent/iterative-loop")
def create_iterative_research_loop(
    project_id: str,
    payload: IterativeLoopRequest | None = None,
) -> dict[str, Any]:
    request_payload = payload or IterativeLoopRequest()
    try:
        return run_iterative_research_loop(
            project_id,
            max_rounds=request_payload.max_rounds,
            topic=request_payload.topic,
            research_question=request_payload.research_question,
        )
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/agent/iterative-loop/latest")
def get_iterative_research_loop_latest(project_id: str) -> dict[str, Any]:
    try:
        return read_iterative_research_loop_latest(project_id)
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/projects/{project_id}/agent/runs")
def get_agent_runs(project_id: str) -> list[dict[str, Any]]:
    try:
        return read_agent_runs(project_id)
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc
