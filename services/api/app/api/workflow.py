from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import StepRunRequest, WorkflowRunResponse, WorkflowStatusResponse
from app.services.project_service import ProjectNotFoundError, project_service
from app.services.workflow_service import UnknownWorkflowStepError, workflow_service

router = APIRouter()


@router.post("/projects/{project_id}/workflow/run", response_model=WorkflowRunResponse)
def run_workflow(project_id: str) -> WorkflowRunResponse:
    try:
        return workflow_service.run_workflow(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/projects/{project_id}/workflow/run-step", response_model=WorkflowRunResponse)
def run_workflow_step(project_id: str, payload: StepRunRequest) -> WorkflowRunResponse:
    try:
        return workflow_service.run_step(project_id, payload.step)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnknownWorkflowStepError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/workflow/status", response_model=WorkflowStatusResponse)
def workflow_status(project_id: str) -> WorkflowStatusResponse:
    try:
        project = project_service.require_project(project_id)
        return WorkflowStatusResponse(
            project_id=project.id,
            workflow_status=project.workflow_status,
            current_step=project.current_step,
            errors=[],
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
