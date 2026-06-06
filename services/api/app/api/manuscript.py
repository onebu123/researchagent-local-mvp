from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas import (
    ManuscriptDiffGenerateRequest,
    ManuscriptPatchConfirmRequest,
    ManuscriptPatchGenerateRequest,
    ManuscriptPatchItemEditRequest,
    PatchIdsRequest,
    PatchMergeConfirmRequest,
    RevisionDiffReviewRequest,
    RevisionLineDiffGenerateRequest,
)
from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import InvalidUploadError, storage_service
from app.tools.manuscript_patch import (
    confirm_manuscript_patch,
    edit_patch_item,
    generate_manuscript_patch,
    list_patches,
    load_patch,
    load_patch_preview,
    load_version,
    read_version_history,
    rerun_patch_item_safety,
)
from app.tools.manuscript_diff import (
    generate_manuscript_diff,
    list_manuscript_diffs,
    load_manuscript_diff,
    load_manuscript_diff_preview,
)
from app.tools.patch_conflict import check_patch_conflicts
from app.tools.patch_merge import (
    confirm_patch_merge,
    generate_patch_merge_preview,
    load_merge_preview,
    load_patch_merge,
)
from app.tools.version_lineage import generate_version_lineage
from app.tools.revision_line_diff import (
    generate_revision_line_diff,
    list_revision_line_diffs,
    load_revision_line_diff,
)
from app.tools.revision_diff_review import (
    generate_revision_diff_review_summary,
    read_revision_diff_reviews,
    record_revision_diff_review,
)

router = APIRouter()


def _project_dir(project_id: str) -> Path:
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
    return HTTPException(status_code=500, detail="manuscript patch operation failed")


def _assert_source_inside(project_id: str, project_dir: Path, source_manuscript: str) -> None:
    try:
        storage_service.ensure_inside_project(project_id, project_dir / source_manuscript)
    except InvalidUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/manuscript/patches/generate")
def generate_patch(
    project_id: str,
    payload: ManuscriptPatchGenerateRequest | None = None,
) -> dict[str, Any]:
    project_dir = _project_dir(project_id)
    request_payload = payload or ManuscriptPatchGenerateRequest()
    _assert_source_inside(project_id, project_dir, request_payload.source_manuscript)
    try:
        return generate_manuscript_patch(
            project_dir,
            project_id,
            source_manuscript=request_payload.source_manuscript,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/manuscript/patches")
def get_patches(project_id: str) -> list[dict[str, Any]]:
    return list_patches(_project_dir(project_id))


@router.get("/projects/{project_id}/manuscript/patches/{patch_id}")
def get_patch(project_id: str, patch_id: str) -> dict[str, Any]:
    try:
        return load_patch(_project_dir(project_id), patch_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/manuscript/patches/{patch_id}/preview")
def get_patch_preview(project_id: str, patch_id: str) -> dict[str, str]:
    try:
        return {
            "patch_id": patch_id,
            "relative_path": f"manuscript/patches/{patch_id}.preview.md",
            "content": load_patch_preview(_project_dir(project_id), patch_id),
        }
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/manuscript/patches/{patch_id}/confirm")
def confirm_patch(
    project_id: str,
    patch_id: str,
    payload: ManuscriptPatchConfirmRequest,
) -> dict[str, Any]:
    try:
        return confirm_manuscript_patch(
            _project_dir(project_id),
            project_id,
            patch_id,
            payload.decision,
            payload.reason or "",
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.patch("/projects/{project_id}/manuscript/patches/{patch_id}/items/{patch_item_id}")
def patch_item(
    project_id: str,
    patch_id: str,
    patch_item_id: str,
    payload: ManuscriptPatchItemEditRequest,
) -> dict[str, Any]:
    try:
        return edit_patch_item(
            _project_dir(project_id),
            project_id,
            patch_id,
            patch_item_id,
            payload.after,
            payload.reason or "",
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post(
    "/projects/{project_id}/manuscript/patches/{patch_id}/items/{patch_item_id}/safety-check"
)
def patch_item_safety_check(
    project_id: str,
    patch_id: str,
    patch_item_id: str,
) -> dict[str, Any]:
    try:
        return rerun_patch_item_safety(_project_dir(project_id), project_id, patch_id, patch_item_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/manuscript/patches/conflicts/check")
def patch_conflicts(project_id: str, payload: PatchIdsRequest) -> dict[str, Any]:
    try:
        return check_patch_conflicts(_project_dir(project_id), project_id, payload.patch_ids)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/manuscript/patches/merge-preview")
def patch_merge_preview(project_id: str, payload: PatchIdsRequest) -> dict[str, Any]:
    try:
        return generate_patch_merge_preview(_project_dir(project_id), project_id, payload.patch_ids)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/manuscript/patches/merges/{merge_id}")
def get_patch_merge(project_id: str, merge_id: str) -> dict[str, Any]:
    try:
        return load_patch_merge(_project_dir(project_id), merge_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/manuscript/patches/merges/{merge_id}/preview")
def get_patch_merge_preview(project_id: str, merge_id: str) -> dict[str, str]:
    try:
        return {
            "merge_id": merge_id,
            "relative_path": f"manuscript/patches/merges/{merge_id}.preview.md",
            "content": load_merge_preview(_project_dir(project_id), merge_id),
        }
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/manuscript/patches/merges/{merge_id}/confirm")
def confirm_merge(
    project_id: str,
    merge_id: str,
    payload: PatchMergeConfirmRequest,
) -> dict[str, Any]:
    try:
        return confirm_patch_merge(
            _project_dir(project_id),
            project_id,
            merge_id,
            payload.decision,
            payload.reason or "",
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/manuscript/versions")
def get_versions(project_id: str) -> dict[str, list[dict[str, Any]]]:
    return read_version_history(_project_dir(project_id))


@router.get("/projects/{project_id}/manuscript/versions/lineage")
def get_version_lineage(project_id: str) -> dict[str, Any]:
    try:
        return generate_version_lineage(_project_dir(project_id), project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/manuscript/versions/{version_id}")
def get_version(project_id: str, version_id: str) -> dict[str, Any]:
    try:
        return load_version(_project_dir(project_id), version_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/manuscript/diffs/generate")
def generate_diff(project_id: str, payload: ManuscriptDiffGenerateRequest) -> dict[str, Any]:
    project_dir = _project_dir(project_id)
    _assert_source_inside(project_id, project_dir, payload.base_file)
    try:
        return generate_manuscript_diff(
            project_dir,
            project_id,
            payload.base_file,
            payload.version_id,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/manuscript/diffs")
def get_diffs(project_id: str) -> list[dict[str, Any]]:
    return list_manuscript_diffs(_project_dir(project_id))


@router.get("/projects/{project_id}/manuscript/diffs/{diff_id}")
def get_diff(project_id: str, diff_id: str) -> dict[str, Any]:
    try:
        return load_manuscript_diff(_project_dir(project_id), diff_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/manuscript/diffs/{diff_id}/preview")
def get_diff_preview(project_id: str, diff_id: str) -> dict[str, str]:
    try:
        return {
            "diff_id": diff_id,
            "relative_path": f"manuscript/diffs/{diff_id}.md",
            "content": load_manuscript_diff_preview(_project_dir(project_id), diff_id),
        }
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/manuscript/revision-diffs/generate")
def generate_revision_diff(
    project_id: str,
    payload: RevisionLineDiffGenerateRequest,
) -> dict[str, Any]:
    project_dir = _project_dir(project_id)
    _assert_source_inside(project_id, project_dir, payload.base_file)
    _assert_source_inside(project_id, project_dir, payload.target_file)
    try:
        return generate_revision_line_diff(
            project_dir,
            project_id,
            payload.base_file,
            payload.target_file,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/manuscript/revision-diffs")
def get_revision_diffs(project_id: str) -> list[dict[str, Any]]:
    return list_revision_line_diffs(_project_dir(project_id))


@router.get("/projects/{project_id}/manuscript/revision-diffs/reviews")
def get_revision_diff_reviews(project_id: str) -> dict[str, Any]:
    project_dir = _project_dir(project_id)
    return {
        "reviews": read_revision_diff_reviews(project_dir),
        "summary": generate_revision_diff_review_summary(project_dir),
    }


@router.post(
    "/projects/{project_id}/manuscript/revision-diffs/{revision_diff_id}/changes/{change_id}/review"
)
def review_revision_diff_change(
    project_id: str,
    revision_diff_id: str,
    change_id: str,
    payload: RevisionDiffReviewRequest,
) -> dict[str, Any]:
    try:
        return record_revision_diff_review(
            _project_dir(project_id),
            project_id,
            revision_diff_id,
            change_id,
            payload.human_status,
            payload.reason or "",
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/manuscript/revision-diffs/{revision_diff_id}")
def get_revision_diff(project_id: str, revision_diff_id: str) -> dict[str, Any]:
    try:
        return load_revision_line_diff(_project_dir(project_id), revision_diff_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc
