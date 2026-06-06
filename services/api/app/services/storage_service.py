from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.config import settings


PROJECT_SUBDIRS = [
    "literature",
    "data",
    "analysis",
    "figures",
    "manuscript",
    "reviews",
    "provenance",
    "audit",
    "runs",
    "trust",
    "exports",
]

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
LITERATURE_UPLOAD_SUFFIXES = {".pdf", ".md", ".markdown", ".txt"}


class InvalidUploadError(ValueError):
    pass


@dataclass(frozen=True)
class SavedUpload:
    filename: str
    relative_path: str
    size_bytes: int


class StorageService:
    def __init__(self, projects_root: Path) -> None:
        self.projects_root = projects_root

    def ensure_project_structure(self, project_id: str) -> Path:
        project_dir = self.project_dir(project_id)
        for subdir in PROJECT_SUBDIRS:
            (project_dir / subdir).mkdir(parents=True, exist_ok=True)
        return project_dir

    def project_dir(self, project_id: str) -> Path:
        safe_id = self.safe_segment(project_id)
        return (self.projects_root / safe_id).resolve()

    def safe_segment(self, value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
        cleaned = cleaned.strip("._")
        if not cleaned:
            raise InvalidUploadError("项目 ID 无效。")
        return cleaned

    def safe_filename(self, filename: str) -> str:
        raw_name = Path(filename or "upload").name
        safe_name = re.sub(r"[^0-9A-Za-z._() -]+", "_", raw_name).strip()
        if not safe_name:
            safe_name = "upload"
        return safe_name

    def ensure_inside_project(self, project_id: str, path: Path) -> Path:
        root = self.project_dir(project_id)
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise InvalidUploadError("文件路径越界。")
        return resolved

    def save_upload(
        self,
        project_id: str,
        subdir: str,
        file: UploadFile,
        allowed_suffixes: set[str],
    ) -> SavedUpload:
        if subdir not in PROJECT_SUBDIRS:
            raise InvalidUploadError("目标目录无效。")
        filename = self.safe_filename(file.filename or "upload")
        suffix = Path(filename).suffix.lower()
        if suffix not in allowed_suffixes:
            allowed = ", ".join(sorted(allowed_suffixes))
            raise InvalidUploadError(f"文件类型不支持，仅允许：{allowed}")

        project_dir = self.ensure_project_structure(project_id)
        dest = self.ensure_inside_project(project_id, project_dir / subdir / filename)
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        size_bytes = dest.stat().st_size
        if size_bytes > MAX_UPLOAD_BYTES:
            dest.unlink(missing_ok=True)
            raise InvalidUploadError("文件过大，当前上限为 10MB。")
        relative_path = dest.relative_to(project_dir).as_posix()
        return SavedUpload(filename=filename, relative_path=relative_path, size_bytes=size_bytes)

    def resource_counts(self, project_id: str) -> dict[str, int]:
        project_dir = self.ensure_project_structure(project_id)
        literature_files = [
            path
            for path in (project_dir / "literature").iterdir()
            if path.is_file() and path.suffix.lower() in LITERATURE_UPLOAD_SUFFIXES
        ]
        return {
            "literature_count": len(literature_files),
            "dataset_count": len(list((project_dir / "data").glob("*.csv"))),
            "figure_count": len(list((project_dir / "figures").glob("figure_*.*"))),
            "manuscript_count": len(list((project_dir / "manuscript").glob("*.md"))),
            "review_count": len(list((project_dir / "reviews").glob("review_report.*"))),
        }


storage_service = StorageService(settings.projects_root)
