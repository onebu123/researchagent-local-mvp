from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas import AuditFilteredExportRequest
from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import storage_service
from app.tools.audit_export import (
    export_audit_log,
    list_audit_exports,
    load_audit_export,
    load_audit_export_report,
    load_audit_file_manifest,
)
from app.tools.audit_filter_export import (
    export_filtered_audit_log,
    list_filtered_audit_exports,
    load_filtered_audit_export,
    load_filtered_audit_report,
)
from app.tools.audit_log import read_audit_log, verify_audit_hash_chain
from app.tools.run_history import read_run_history

router = APIRouter()


def _project_dir(project_id: str):
    try:
        project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return storage_service.project_dir(project_id)


@router.get("/projects/{project_id}/audit")
def get_audit_log(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    return read_audit_log(_project_dir(project_id), limit=limit)


@router.get("/projects/{project_id}/runs")
def get_run_history(project_id: str) -> dict[str, list[dict]]:
    return read_run_history(_project_dir(project_id))


@router.get("/projects/{project_id}/audit/verify")
def verify_audit_log(project_id: str) -> dict:
    return verify_audit_hash_chain(_project_dir(project_id))


def _handle_tool_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="audit operation failed")


@router.post("/projects/{project_id}/audit/export")
def create_audit_export(project_id: str) -> dict:
    try:
        return export_audit_log(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/audit/exports")
def get_audit_exports(project_id: str) -> list[dict]:
    return list_audit_exports(_project_dir(project_id))


@router.get("/projects/{project_id}/audit/exports/{export_id}")
def get_audit_export(project_id: str, export_id: str) -> dict:
    try:
        return load_audit_export(_project_dir(project_id), export_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/audit/exports/{export_id}/report")
def get_audit_export_report(project_id: str, export_id: str) -> dict[str, str]:
    try:
        return {
            "export_id": export_id,
            "relative_path": f"audit/exports/audit_integrity_report_{export_id.removeprefix('audit_export_')}.md",
            "content": load_audit_export_report(_project_dir(project_id), export_id),
        }
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/audit/exports/{export_id}/manifest")
def get_audit_file_manifest(project_id: str, export_id: str) -> dict:
    try:
        return load_audit_file_manifest(_project_dir(project_id), export_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/audit/filtered-export")
def create_filtered_audit_export(project_id: str, payload: AuditFilteredExportRequest) -> dict:
    try:
        return export_filtered_audit_log(
            _project_dir(project_id),
            project_id,
            payload.model_dump(exclude_none=True),
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/audit/filtered-exports")
def get_filtered_audit_exports(project_id: str) -> list[dict]:
    return list_filtered_audit_exports(_project_dir(project_id))


@router.get("/projects/{project_id}/audit/filtered-exports/{export_id}")
def get_filtered_audit_export(project_id: str, export_id: str) -> dict:
    try:
        return load_filtered_audit_export(_project_dir(project_id), export_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/audit/filtered-exports/{export_id}/report")
def get_filtered_audit_export_report(project_id: str, export_id: str) -> dict[str, str]:
    try:
        return {
            "export_id": export_id,
            "relative_path": (
                "audit/filtered_exports/"
                f"audit_filtered_report_{export_id.removeprefix('audit_filtered_export_')}.md"
            ),
            "content": load_filtered_audit_report(_project_dir(project_id), export_id),
        }
    except Exception as exc:
        raise _handle_tool_error(exc) from exc
