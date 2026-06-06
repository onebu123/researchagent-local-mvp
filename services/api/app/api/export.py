from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import storage_service
from app.tools.project_export import ProjectExportError, build_project_export, latest_project_export_info

router = APIRouter()


def _project_dir(project_id: str):
    try:
        project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return storage_service.project_dir(project_id)


def _handle_export_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (ValueError, ProjectExportError)):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="project export failed")


@router.post("/projects/{project_id}/export/zip")
def create_project_zip_export(project_id: str) -> dict[str, Any]:
    try:
        return build_project_export(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_export_error(exc) from exc


@router.get("/projects/{project_id}/export/zip")
def get_latest_project_zip_export(project_id: str) -> dict[str, Any]:
    try:
        return latest_project_export_info(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_export_error(exc) from exc
