from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas import (
    LiteratureMetadataRevertSuggestionRequest,
    LiteraturePatch,
    LiteratureRecord,
    MetadataReviewActionRequest,
    PDFPageReviewRequest,
)
from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import storage_service
from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.metadata_history import append_metadata_history, read_metadata_history
from app.tools.literature_metadata_diff import (
    build_revert_suggestion,
    generate_metadata_diff_report,
    generate_metadata_review_batch,
)
from app.tools.pdf_quality_report import generate_pdf_quality_report
from app.tools.metadata_review_workflow import (
    generate_metadata_review_summary,
    read_metadata_review_actions,
    record_metadata_review_action,
)
from app.tools.pdf_page_review import (
    generate_pdf_page_review_summary,
    read_pdf_page_reviews,
    record_pdf_page_review,
)

router = APIRouter()


def _literature_index_file(project_id: str):
    try:
        project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    project_dir = storage_service.project_dir(project_id)
    return storage_service.ensure_inside_project(
        project_id, project_dir / "literature" / "literature_index.json"
    )


def _read_literature_index(project_id: str) -> list[dict[str, Any]]:
    path = _literature_index_file(project_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="literature/literature_index.json does not exist")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="literature_index.json is invalid JSON") from exc
    if not isinstance(payload, list):
        raise HTTPException(status_code=400, detail="literature_index.json must be a list")
    return payload


def _project_dir(project_id: str):
    try:
        project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return storage_service.project_dir(project_id)


def _reject_invalid_nulls(payload: LiteraturePatch) -> None:
    fields = payload.model_fields_set
    if "title" in fields and payload.title is None:
        raise HTTPException(status_code=422, detail="title must not be null")
    if "authors" in fields and payload.authors is None:
        raise HTTPException(status_code=422, detail="authors must be a string array")
    if "metadata_status" in fields and payload.metadata_status is None:
        raise HTTPException(status_code=422, detail="metadata_status must not be null")
    if "human_verified" in fields and payload.human_verified is None:
        raise HTTPException(status_code=422, detail="human_verified must be a boolean")


def _handle_tool_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="literature operation failed")


@router.get("/projects/{project_id}/literature", response_model=list[LiteratureRecord])
def get_project_literature(project_id: str) -> list[dict[str, Any]]:
    return _read_literature_index(project_id)


@router.patch("/projects/{project_id}/literature/{literature_id}", response_model=LiteratureRecord)
def patch_project_literature(
    project_id: str,
    literature_id: str,
    payload: LiteraturePatch,
) -> dict[str, Any]:
    _reject_invalid_nulls(payload)
    entries = _read_literature_index(project_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No literature metadata fields supplied")

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        if entry.get("literature_id") != literature_id:
            continue
        updated = {**entry, **updates}
        entries[index] = updated
        write_json(_literature_index_file(project_id), entries)
        changed_fields = [field for field, value in updates.items() if entry.get(field) != value]
        if changed_fields:
            project_dir = _project_dir(project_id)
            append_metadata_history(
                project_dir,
                literature_id,
                changed_fields,
                {field: entry.get(field) for field in changed_fields},
                {field: updated.get(field) for field in changed_fields},
                source="api",
                reason="manual metadata update",
            )
            append_audit_event(
                project_dir,
                project_id,
                "patch_literature_metadata",
                "Literature metadata was patched by local user.",
                {
                    "literature_id": literature_id,
                    "changed_fields": changed_fields,
                    "source_file": entry.get("source_file"),
                },
                source="api",
            )
        return updated

    raise HTTPException(status_code=404, detail=f"literature_id not found: {literature_id}")


@router.get("/projects/{project_id}/literature/history")
def get_literature_history(project_id: str) -> list[dict[str, Any]]:
    return read_metadata_history(_project_dir(project_id))


@router.get("/projects/{project_id}/literature/{literature_id}/history")
def get_literature_record_history(project_id: str, literature_id: str) -> list[dict[str, Any]]:
    entries = _read_literature_index(project_id)
    if not any(isinstance(entry, dict) and entry.get("literature_id") == literature_id for entry in entries):
        raise HTTPException(status_code=404, detail=f"literature_id not found: {literature_id}")
    return read_metadata_history(_project_dir(project_id), literature_id)


@router.get("/projects/{project_id}/literature/metadata-diff")
def get_literature_metadata_diff(project_id: str) -> dict[str, Any]:
    try:
        return generate_metadata_diff_report(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/literature/{literature_id}/metadata/revert-suggestion")
def suggest_literature_metadata_revert(
    project_id: str,
    literature_id: str,
    payload: LiteratureMetadataRevertSuggestionRequest,
) -> dict[str, Any]:
    try:
        return build_revert_suggestion(
            _project_dir(project_id),
            project_id,
            literature_id,
            payload.field,
            payload.source_history_id,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/literature/metadata-review-batch")
def create_literature_metadata_review_batch(project_id: str) -> dict[str, Any]:
    try:
        return generate_metadata_review_batch(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/literature/metadata-review-actions")
def get_literature_metadata_review_actions(project_id: str) -> dict[str, Any]:
    project_dir = _project_dir(project_id)
    return {
        "actions": read_metadata_review_actions(project_dir),
        "summary": generate_metadata_review_summary(project_dir),
    }


@router.post("/projects/{project_id}/literature/{literature_id}/metadata-review")
def review_literature_metadata_change(
    project_id: str,
    literature_id: str,
    payload: MetadataReviewActionRequest,
) -> dict[str, Any]:
    try:
        return record_metadata_review_action(
            _project_dir(project_id),
            project_id,
            literature_id,
            payload.field,
            payload.action,
            payload.source_history_id,
            payload.reason or "",
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/literature/pdf-quality-report")
def get_pdf_quality_report(project_id: str) -> dict[str, Any]:
    try:
        return generate_pdf_quality_report(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/literature/pdf-page-reviews")
def get_pdf_page_reviews(project_id: str) -> dict[str, Any]:
    project_dir = _project_dir(project_id)
    return {
        "reviews": read_pdf_page_reviews(project_dir),
        "summary": generate_pdf_page_review_summary(project_dir),
    }


@router.post("/projects/{project_id}/literature/pdf-page-review")
def review_pdf_page(project_id: str, payload: PDFPageReviewRequest) -> dict[str, Any]:
    try:
        return record_pdf_page_review(
            _project_dir(project_id),
            project_id,
            payload.source_file,
            payload.page_number,
            payload.human_status,
            payload.reason or "",
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc
