from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas import ProjectCreate, ProjectDetail, ProjectRead, ResourceSummary
from app.services.project_service import ProjectNotFoundError, project_service

router = APIRouter()


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate) -> ProjectRead:
    return project_service.create_project(payload)


@router.get("/projects", response_model=list[ProjectRead])
def list_projects() -> list[ProjectRead]:
    return project_service.list_projects()


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str) -> ProjectDetail:
    try:
        return project_service.get_project_detail(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/resources", response_model=ResourceSummary)
def get_resources(project_id: str) -> ResourceSummary:
    try:
        return project_service.get_resource_summary(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
