from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import storage_service
from app.tools.project_export import ProjectExportError, build_project_export, latest_project_export_info
from app.tools.workspace_export import (
    WorkspaceExportError,
    build_workspace_export,
    latest_workspace_export_info,
)
from app.tools.evidence_trust_package import (
    build_evidence_trust_package,
    latest_evidence_trust_package_info,
)

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
    if isinstance(exc, (ValueError, ProjectExportError, WorkspaceExportError)):
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


@router.post("/projects/{project_id}/export/workspace")
def create_workspace_export(project_id: str) -> dict[str, Any]:
    try:
        return build_workspace_export(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_export_error(exc) from exc


@router.get("/projects/{project_id}/export/workspace")
def get_latest_workspace_export(project_id: str) -> dict[str, Any]:
    try:
        return latest_workspace_export_info(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_export_error(exc) from exc


@router.post("/projects/{project_id}/export/evidence-trust-package")
def create_evidence_trust_package(project_id: str) -> dict[str, Any]:
    try:
        return build_evidence_trust_package(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_export_error(exc) from exc


@router.get("/projects/{project_id}/export/evidence-trust-package")
def get_latest_evidence_trust_package(project_id: str) -> dict[str, Any]:
    try:
        return latest_evidence_trust_package_info(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_export_error(exc) from exc
