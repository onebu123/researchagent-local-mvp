from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas import (
    PaperWriterDraftRequest,
    PaperWriterLatexExportRequest,
    PaperWriterOutlineRequest,
    PaperWriterPlanRequest,
)
from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import storage_service
from app.tools.paper_writer.latex_export import export_draft_latex, read_latex_export_status
from app.tools.paper_writer.outline_builder import generate_paper_outline, read_paper_outline
from app.tools.paper_writer.paper_plan import generate_paper_plan, read_paper_plan
from app.tools.paper_writer.section_writer import generate_full_draft, read_full_draft_status
from app.tools.paper_writer.writer_eval import evaluate_auto_paper_draft

router = APIRouter()


def _project(project_id: str):
    try:
        return project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _project_dir(project_id: str):
    _project(project_id)
    return storage_service.project_dir(project_id)


def _handle_tool_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="auto paper writer operation failed")


@router.post("/projects/{project_id}/paper-writer/plan")
def create_paper_writer_plan(
    project_id: str,
    payload: PaperWriterPlanRequest | None = None,
) -> dict[str, Any]:
    project = _project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    request_payload = payload or PaperWriterPlanRequest()
    try:
        return generate_paper_plan(
            project_dir,
            project_id,
            project_name=project.name,
            domain=project.domain,
            paper_type=request_payload.paper_type,
            topic=request_payload.topic,
            research_question=request_payload.research_question,
            retrieval_mode=request_payload.retrieval_mode,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/paper-writer/plan")
def get_paper_writer_plan(project_id: str) -> dict[str, Any]:
    payload = read_paper_plan(_project_dir(project_id))
    if not payload:
        raise HTTPException(status_code=404, detail="manuscript/paper_plan.json does not exist")
    return payload


@router.post("/projects/{project_id}/paper-writer/outline")
def create_paper_writer_outline(
    project_id: str,
    payload: PaperWriterOutlineRequest | None = None,
) -> dict[str, Any]:
    project = _project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    request_payload = payload or PaperWriterOutlineRequest()
    try:
        return generate_paper_outline(
            project_dir,
            project_id,
            project_name=project.name,
            domain=project.domain,
            retrieval_mode=request_payload.retrieval_mode,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/paper-writer/outline")
def get_paper_writer_outline(project_id: str) -> dict[str, Any]:
    payload = read_paper_outline(_project_dir(project_id))
    if not payload:
        raise HTTPException(status_code=404, detail="manuscript/outline.json does not exist")
    return payload


@router.post("/projects/{project_id}/paper-writer/draft")
def create_paper_writer_draft(
    project_id: str,
    payload: PaperWriterDraftRequest | None = None,
) -> dict[str, Any]:
    project = _project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    request_payload = payload or PaperWriterDraftRequest()
    try:
        return generate_full_draft(
            project_dir,
            project_id,
            project_name=project.name,
            domain=project.domain,
            retrieval_mode=request_payload.retrieval_mode,
            run_claim_audit_after=request_payload.run_claim_audit_after,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/paper-writer/draft")
def get_paper_writer_draft(project_id: str) -> dict[str, Any]:
    status = read_full_draft_status(_project_dir(project_id))
    if not status["available"]:
        raise HTTPException(status_code=404, detail="manuscript/draft_full.md does not exist")
    return status


@router.post("/projects/{project_id}/paper-writer/export-latex")
def create_paper_writer_latex(
    project_id: str,
    _payload: PaperWriterLatexExportRequest | None = None,
) -> dict[str, Any]:
    try:
        return export_draft_latex(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/paper-writer/status")
def get_paper_writer_status(project_id: str) -> dict[str, Any]:
    project_dir = _project_dir(project_id)
    return {
        "project_id": project_id,
        "plan": {"available": bool(read_paper_plan(project_dir)), "relative_path": "manuscript/paper_plan.json"},
        "outline": {"available": bool(read_paper_outline(project_dir)), "relative_path": "manuscript/outline.json"},
        "draft": read_full_draft_status(project_dir),
        "latex": read_latex_export_status(project_dir),
        "safety_smoke": evaluate_auto_paper_draft(project_dir),
    }
