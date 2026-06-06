from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile

from app.schemas import UploadResponse
from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import InvalidUploadError, storage_service
from app.tools.audit_log import append_audit_event
from app.tools.literature_index import build_literature_index

router = APIRouter()


@router.post("/projects/{project_id}/upload/literature", response_model=UploadResponse)
def upload_literature(project_id: str, file: UploadFile) -> UploadResponse:
    try:
        project_service.require_project(project_id)
        saved = storage_service.save_upload(
            project_id,
            "literature",
            file,
            allowed_suffixes={".pdf", ".md", ".markdown", ".txt"},
        )
        build_literature_index(storage_service.project_dir(project_id))
        append_audit_event(
            storage_service.project_dir(project_id),
            project_id,
            "upload_literature",
            "Literature file uploaded.",
            {
                "filename": saved.filename,
                "relative_path": saved.relative_path,
                "size_bytes": saved.size_bytes,
            },
            source="api",
        )
        return UploadResponse(
            project_id=project_id,
            filename=saved.filename,
            relative_path=saved.relative_path,
            size_bytes=saved.size_bytes,
            message="文献文件已保存，PDF 将尝试解析并写入 literature_index.json。",
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/upload/data", response_model=UploadResponse)
def upload_data(project_id: str, file: UploadFile) -> UploadResponse:
    try:
        project_service.require_project(project_id)
        saved = storage_service.save_upload(
            project_id,
            "data",
            file,
            allowed_suffixes={".csv"},
        )
        append_audit_event(
            storage_service.project_dir(project_id),
            project_id,
            "upload_data",
            "Data file uploaded.",
            {
                "filename": saved.filename,
                "relative_path": saved.relative_path,
                "size_bytes": saved.size_bytes,
            },
            source="api",
        )
        return UploadResponse(
            project_id=project_id,
            filename=saved.filename,
            relative_path=saved.relative_path,
            size_bytes=saved.size_bytes,
            message="CSV 数据文件已保存。",
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
