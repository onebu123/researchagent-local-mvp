from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    LiteratureMetadataLookupRequest,
    LiteratureRAGAskRequest,
    ReferenceApprovalRequest,
    ReferenceVerificationRunRequest,
)
from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import storage_service
from app.tools.bibtex_generator import generate_bibtex, read_bibtex
from app.tools.citation_support_checker import read_citation_support_report
from app.tools.citation_grounding import read_citation_grounding_report
from app.tools.literature_metadata_lookup import read_metadata_lookup_results, run_metadata_lookup
from app.tools.literature_rag import (
    ask_literature_rag,
    build_literature_rag,
    read_rag_answers,
    read_rag_chunks,
)
from app.tools.llm_call_log import read_llm_calls
from app.tools.manuscript_references import read_references_preview, read_references_status
from app.tools.reference_approval import (
    generate_reference_approval_summary,
    read_reference_approval_summary,
    read_reference_approvals,
    record_reference_approval,
)
from app.tools.reference_verification import (
    read_reference_verification_results,
    read_reference_verification_summary,
    run_reference_verification,
)
from app.tools.source_passage_evidence import read_source_passage_evidence

router = APIRouter()


def _project_dir(project_id: str):
    try:
        project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return storage_service.project_dir(project_id)


def _handle_tool_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="literature intelligence operation failed")


@router.get("/projects/{project_id}/llm/calls")
def get_project_llm_calls(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    return read_llm_calls(_project_dir(project_id), limit=limit)


@router.post("/projects/{project_id}/literature/rag/build")
def build_project_literature_rag(project_id: str) -> dict[str, Any]:
    try:
        return build_literature_rag(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/literature/rag/ask")
def ask_project_literature_rag(
    project_id: str,
    payload: LiteratureRAGAskRequest,
) -> dict[str, Any]:
    try:
        return ask_literature_rag(
            _project_dir(project_id),
            project_id,
            payload.question,
            top_k=payload.top_k,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/literature/rag/chunks")
def get_project_literature_rag_chunks(project_id: str) -> list[dict[str, Any]]:
    return read_rag_chunks(_project_dir(project_id))


@router.get("/projects/{project_id}/literature/rag/answers")
def get_project_literature_rag_answers(project_id: str) -> list[dict[str, Any]]:
    return read_rag_answers(_project_dir(project_id))


@router.get("/projects/{project_id}/provenance/source-passage-evidence")
def get_project_source_passage_evidence(project_id: str) -> dict[str, Any]:
    try:
        return read_source_passage_evidence(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/literature/metadata-lookup")
def run_project_metadata_lookup(
    project_id: str,
    payload: LiteratureMetadataLookupRequest,
) -> dict[str, Any]:
    try:
        return run_metadata_lookup(_project_dir(project_id), project_id, provider=payload.provider)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/literature/metadata-lookup/results")
def get_project_metadata_lookup_results(project_id: str) -> dict[str, Any]:
    return read_metadata_lookup_results(_project_dir(project_id))


@router.post("/projects/{project_id}/literature/bibtex/generate")
def generate_project_bibtex(project_id: str) -> dict[str, Any]:
    try:
        return generate_bibtex(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/literature/bibtex")
def get_project_bibtex(project_id: str) -> dict[str, Any]:
    try:
        return read_bibtex(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/provenance/citation-support")
def get_project_citation_support(project_id: str) -> dict[str, Any]:
    try:
        return read_citation_support_report(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/literature/reference-verification/run")
def run_project_reference_verification(
    project_id: str,
    payload: ReferenceVerificationRunRequest,
) -> dict[str, Any]:
    try:
        return run_reference_verification(
            _project_dir(project_id),
            project_id,
            provider=payload.provider,
            literature_id=payload.literature_id,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/literature/reference-verification/results")
def get_project_reference_verification_results(project_id: str) -> list[dict[str, Any]]:
    return read_reference_verification_results(_project_dir(project_id))


@router.get("/projects/{project_id}/literature/reference-verification/summary")
def get_project_reference_verification_summary(project_id: str) -> dict[str, Any]:
    return read_reference_verification_summary(_project_dir(project_id))


@router.post("/projects/{project_id}/literature/reference-verification/{verification_id}/approval")
def approve_project_reference_verification(
    project_id: str,
    verification_id: str,
    payload: ReferenceApprovalRequest,
) -> dict[str, Any]:
    try:
        return record_reference_approval(
            _project_dir(project_id),
            project_id,
            verification_id,
            payload.decision,
            payload.reason or "",
            apply_to_literature_index=payload.apply_to_literature_index,
            source="api",
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/literature/reference-approvals")
def get_project_reference_approvals(project_id: str) -> list[dict[str, Any]]:
    return read_reference_approvals(_project_dir(project_id))


@router.get("/projects/{project_id}/literature/reference-approval-summary")
def get_project_reference_approval_summary(project_id: str) -> dict[str, Any]:
    project_dir = _project_dir(project_id)
    if not read_reference_approvals(project_dir):
        return read_reference_approval_summary(project_dir)
    return generate_reference_approval_summary(project_dir)


@router.get("/projects/{project_id}/provenance/citation-grounding")
def get_project_citation_grounding(project_id: str) -> dict[str, Any]:
    try:
        return read_citation_grounding_report(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/manuscript/references/status")
def get_project_manuscript_references_status(project_id: str) -> dict[str, Any]:
    try:
        return read_references_status(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/manuscript/references/preview")
def get_project_manuscript_references_preview(project_id: str) -> dict[str, Any]:
    try:
        return read_references_preview(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc
