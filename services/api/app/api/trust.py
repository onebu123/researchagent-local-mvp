from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import EvidenceClaimReviewRequest, MetadataRevertPreviewRequest
from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import InvalidUploadError, storage_service
from app.tools.analysis_timeline import generate_enhanced_analysis_timeline
from app.tools.evidence_claim_review import (
    generate_evidence_claim_review_summary,
    read_evidence_claim_reviews,
    record_evidence_claim_review,
)
from app.tools.metadata_revert_preview import generate_metadata_revert_execution_preview
from app.tools.pdf_page_text_preview import generate_pdf_page_text_preview
from app.tools.readiness_report import generate_v1_readiness_report
from app.tools.reviewer_closure import generate_reviewer_closure_summary
from app.tools.trust_summary import generate_trust_summary

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
    if isinstance(exc, (ValueError, InvalidUploadError)):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="trust operation failed")


@router.post("/projects/{project_id}/evidence/claims/{claim_id}/review")
def review_evidence_claim(
    project_id: str,
    claim_id: str,
    payload: EvidenceClaimReviewRequest,
) -> dict[str, Any]:
    try:
        return record_evidence_claim_review(
            _project_dir(project_id),
            project_id,
            claim_id,
            payload.human_status,
            payload.reason or "",
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/evidence/claim-reviews")
def get_evidence_claim_reviews(project_id: str) -> dict[str, Any]:
    project_dir = _project_dir(project_id)
    try:
        return {
            "reviews": read_evidence_claim_reviews(project_dir),
            "summary": generate_evidence_claim_review_summary(project_dir),
        }
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/evidence/claim-review-summary")
def get_evidence_claim_review_summary(project_id: str) -> dict[str, Any]:
    try:
        return generate_evidence_claim_review_summary(_project_dir(project_id))
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/trust/summary")
def get_trust_summary(project_id: str) -> dict[str, Any]:
    try:
        return generate_trust_summary(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/review/closure-summary")
def get_reviewer_closure_summary(project_id: str) -> dict[str, Any]:
    try:
        return generate_reviewer_closure_summary(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/literature/{literature_id}/metadata/revert-preview")
def preview_metadata_revert(
    project_id: str,
    literature_id: str,
    payload: MetadataRevertPreviewRequest,
) -> dict[str, Any]:
    try:
        return generate_metadata_revert_execution_preview(
            _project_dir(project_id),
            project_id,
            literature_id,
            payload.field,
            payload.source_history_id,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/literature/pdf-page-text-preview")
def get_pdf_page_text_preview(
    project_id: str,
    source_file: str | None = Query(default=None, max_length=240),
    page_number: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    try:
        return generate_pdf_page_text_preview(
            _project_dir(project_id),
            project_id,
            source_file=source_file,
            page_number=page_number,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/analysis/timeline/enhanced")
def get_enhanced_analysis_timeline(project_id: str) -> dict[str, Any]:
    try:
        return generate_enhanced_analysis_timeline(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/trust/readiness-report")
def get_v1_readiness_report(project_id: str) -> dict[str, Any]:
    try:
        return generate_v1_readiness_report(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc
