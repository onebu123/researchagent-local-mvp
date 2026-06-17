from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.schemas import AutoScientistRunRequest
from app.services.project_service import ProjectNotFoundError
from app.tools.auto_scientist.scientist_loop import run_auto_scientist
from app.tools.job_manager import (
    list_project_jobs,
    read_project_job,
    read_project_job_events,
    read_project_job_log,
    request_project_job_cancel,
    run_project_job,
    start_project_job_background,
    stream_project_job_events,
)

router = APIRouter()


def _handle_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="job operation failed")


@router.get("/projects/{project_id}/jobs")
def get_project_jobs(project_id: str, limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
    try:
        return list_project_jobs(project_id, limit=limit)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get("/projects/{project_id}/jobs/{job_id}")
def get_project_job(project_id: str, job_id: str) -> dict[str, Any]:
    try:
        return read_project_job(project_id, job_id)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get("/projects/{project_id}/jobs/{job_id}/log")
def get_project_job_log(project_id: str, job_id: str) -> dict[str, Any]:
    try:
        return read_project_job_log(project_id, job_id)
    except Exception as exc:
        raise _handle_error(exc) from exc




@router.get("/projects/{project_id}/jobs/{job_id}/events")
def get_project_job_events(
    project_id: str,
    job_id: str,
    since_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, Any]:
    try:
        return read_project_job_events(project_id, job_id, since_sequence=since_sequence, limit=limit)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get("/projects/{project_id}/jobs/{job_id}/events/stream")
def stream_project_job_event_feed(
    project_id: str,
    job_id: str,
    since_sequence: int = Query(default=0, ge=0),
    max_events: int = Query(default=200, ge=1, le=2000),
) -> StreamingResponse:
    try:
        # Validate now so missing jobs return a JSON error instead of a broken SSE stream.
        read_project_job(project_id, job_id)
    except Exception as exc:
        raise _handle_error(exc) from exc
    return StreamingResponse(
        stream_project_job_events(project_id, job_id, since_sequence=since_sequence, max_events=max_events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/projects/{project_id}/jobs/{job_id}/cancel")
def cancel_project_job(project_id: str, job_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        reason = ""
        if isinstance(payload, dict):
            reason = str(payload.get("reason") or "")
        return request_project_job_cancel(project_id, job_id, reason=reason)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.post("/projects/{project_id}/jobs/auto-scientist/run")
def run_auto_scientist_job(
    project_id: str,
    payload: AutoScientistRunRequest | None = None,
) -> dict[str, Any]:
    request_payload = payload or AutoScientistRunRequest()

    def runner(update):
        update("generating ideas and experiment plan", 0.15)
        result = run_auto_scientist(
            project_id,
            topic=request_payload.topic,
            research_question=request_payload.research_question,
            max_ideas=request_payload.max_ideas,
            max_experiments_per_idea=request_payload.max_experiments_per_idea,
            paper_type=request_payload.paper_type,
            retrieval_mode=request_payload.retrieval_mode,
            write_paper=request_payload.write_paper,
            export_latex=request_payload.export_latex,
            allow_generated_code_experiments=request_payload.allow_generated_code_experiments,
            generated_code_timeout_seconds=request_payload.generated_code_timeout_seconds,
            generated_code_max_memory_mb=request_payload.generated_code_max_memory_mb,
            generated_code_sandbox_mode=request_payload.generated_code_sandbox_mode,
            generated_code_docker_image=request_payload.generated_code_docker_image,
            generated_code_source_mode=request_payload.generated_code_source_mode,
            generated_code_strategy=request_payload.generated_code_strategy,
            generated_code_requires_approval=request_payload.generated_code_requires_approval,
            generated_code_approved=request_payload.generated_code_approved,
            enable_generated_code_revision_loop=request_payload.enable_generated_code_revision_loop,
            generated_code_revision_rounds=request_payload.generated_code_revision_rounds,
            enable_experiment_tree_search=request_payload.enable_experiment_tree_search,
            experiment_tree_max_depth=request_payload.experiment_tree_max_depth,
            experiment_tree_branching_factor=request_payload.experiment_tree_branching_factor,
            progress_callback=update,
        )
        update("auto scientist loop completed", 0.95)
        return result

    try:
        return run_project_job(
            project_id,
            "auto_scientist_run",
            request_payload.model_dump(),
            runner,
        )
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.post("/projects/{project_id}/jobs/auto-scientist/start")
def start_auto_scientist_job(
    project_id: str,
    payload: AutoScientistRunRequest | None = None,
) -> dict[str, Any]:
    request_payload = payload or AutoScientistRunRequest()

    def runner(update):
        update("generating ideas and experiment plan", 0.15)
        result = run_auto_scientist(
            project_id,
            topic=request_payload.topic,
            research_question=request_payload.research_question,
            max_ideas=request_payload.max_ideas,
            max_experiments_per_idea=request_payload.max_experiments_per_idea,
            paper_type=request_payload.paper_type,
            retrieval_mode=request_payload.retrieval_mode,
            write_paper=request_payload.write_paper,
            export_latex=request_payload.export_latex,
            allow_generated_code_experiments=request_payload.allow_generated_code_experiments,
            generated_code_timeout_seconds=request_payload.generated_code_timeout_seconds,
            generated_code_max_memory_mb=request_payload.generated_code_max_memory_mb,
            generated_code_sandbox_mode=request_payload.generated_code_sandbox_mode,
            generated_code_docker_image=request_payload.generated_code_docker_image,
            generated_code_source_mode=request_payload.generated_code_source_mode,
            generated_code_strategy=request_payload.generated_code_strategy,
            generated_code_requires_approval=request_payload.generated_code_requires_approval,
            generated_code_approved=request_payload.generated_code_approved,
            enable_generated_code_revision_loop=request_payload.enable_generated_code_revision_loop,
            generated_code_revision_rounds=request_payload.generated_code_revision_rounds,
            enable_experiment_tree_search=request_payload.enable_experiment_tree_search,
            experiment_tree_max_depth=request_payload.experiment_tree_max_depth,
            experiment_tree_branching_factor=request_payload.experiment_tree_branching_factor,
            progress_callback=update,
        )
        update("auto scientist loop completed", 0.95)
        return result

    try:
        return start_project_job_background(
            project_id,
            "auto_scientist_run",
            request_payload.model_dump(),
            runner,
        )
    except Exception as exc:
        raise _handle_error(exc) from exc
