from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.database import db_session, initialize_database
from app.models import OutputRecord, ProjectRecord
from app.schemas import (
    OutputContent,
    OutputItem,
    ProjectCreate,
    ProjectDetail,
    ProjectRead,
    ResourceSummary,
)
from app.services.storage_service import storage_service
from app.tools.audit_log import append_audit_event


class ProjectNotFoundError(LookupError):
    pass


class OutputNotFoundError(LookupError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project_from_row(row: Any) -> ProjectRecord:
    return ProjectRecord(
        id=row["id"],
        name=row["name"],
        domain=row["domain"],
        language=row["language"],
        output_format=row["output_format"],
        slug=row["slug"],
        workflow_status=row["workflow_status"],
        current_step=row["current_step"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _output_from_row(row: Any) -> OutputRecord:
    return OutputRecord(
        id=row["id"],
        project_id=row["project_id"],
        agent_name=row["agent_name"],
        kind=row["kind"],
        title=row["title"],
        relative_path=row["relative_path"],
        mime_type=row["mime_type"],
        created_at=row["created_at"],
    )


class ProjectService:
    def create_project(
        self,
        payload: ProjectCreate,
        project_id: str | None = None,
        overwrite: bool = False,
    ) -> ProjectRead:
        initialize_database()
        now = utc_now()
        new_id = project_id or f"project_{uuid.uuid4().hex[:10]}"
        project_dir = storage_service.ensure_project_structure(new_id)
        with db_session() as conn:
            existing = conn.execute("SELECT * FROM projects WHERE id = ?", (new_id,)).fetchone()
            if existing and not overwrite:
                return self._to_read(_project_from_row(existing))
            if existing and overwrite:
                conn.execute(
                    """
                    UPDATE projects
                    SET name = ?, domain = ?, language = ?, output_format = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        payload.name,
                        payload.domain,
                        payload.language,
                        payload.output_format,
                        now,
                        new_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO projects (
                        id, name, domain, language, output_format, slug,
                        workflow_status, current_step, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'idle', 'not_started', ?, ?)
                    """,
                    (
                        new_id,
                        payload.name,
                        payload.domain,
                        payload.language,
                        payload.output_format,
                        new_id,
                        now,
                        now,
                    ),
                )
        append_audit_event(
            project_dir,
            new_id,
            "create_project",
            "Project record was created or updated locally.",
            {
                "project_id": new_id,
                "name": payload.name,
                "domain": payload.domain,
                "language": payload.language,
                "overwrite": overwrite,
            },
            source="api",
        )
        return self._to_read(self.require_project(new_id))

    def list_projects(self) -> list[ProjectRead]:
        initialize_database()
        with db_session() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [self._to_read(_project_from_row(row)) for row in rows]

    def require_project(self, project_id: str) -> ProjectRecord:
        initialize_database()
        with db_session() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            raise ProjectNotFoundError(f"项目不存在：{project_id}")
        return _project_from_row(row)

    def get_project_detail(self, project_id: str) -> ProjectDetail:
        project = self.require_project(project_id)
        return ProjectDetail(
            **self._to_read(project).model_dump(),
            resources=self.get_resource_summary(project_id),
            latest_outputs=self.list_outputs(project_id, limit=8),
        )

    def get_resource_summary(self, project_id: str) -> ResourceSummary:
        self.require_project(project_id)
        return ResourceSummary(**storage_service.resource_counts(project_id))

    def update_workflow_state(self, project_id: str, status: str, current_step: str) -> None:
        self.require_project(project_id)
        with db_session() as conn:
            cursor = conn.execute(
                """
                UPDATE projects
                SET workflow_status = ?, current_step = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, current_step, utc_now(), project_id),
            )
            if cursor.rowcount != 1:
                raise ProjectNotFoundError(f"项目不存在：{project_id}")

    def output_id_for(self, project_id: str, relative_path: str) -> str:
        digest = hashlib.sha1(f"{project_id}:{relative_path}".encode("utf-8")).hexdigest()
        return digest[:16]

    def register_output(
        self,
        project_id: str,
        agent_name: str,
        kind: str,
        title: str,
        relative_path: str,
        mime_type: str,
    ) -> OutputItem:
        self.require_project(project_id)
        output_id = self.output_id_for(project_id, relative_path)
        created_at = utc_now()
        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO outputs (
                    id, project_id, agent_name, kind, title,
                    relative_path, mime_type, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    agent_name = excluded.agent_name,
                    kind = excluded.kind,
                    title = excluded.title,
                    mime_type = excluded.mime_type,
                    created_at = excluded.created_at
                """,
                (
                    output_id,
                    project_id,
                    agent_name,
                    kind,
                    title,
                    relative_path,
                    mime_type,
                    created_at,
                ),
            )
        return OutputItem(
            id=output_id,
            agent_name=agent_name,
            kind=kind,
            title=title,
            relative_path=relative_path,
            mime_type=mime_type,
            created_at=created_at,
        )

    def list_outputs(self, project_id: str, limit: int | None = None) -> list[OutputItem]:
        self.require_project(project_id)
        sql = "SELECT * FROM outputs WHERE project_id = ? ORDER BY created_at DESC"
        params: tuple[Any, ...] = (project_id,)
        if limit is not None:
            sql += " LIMIT ?"
            params = (project_id, limit)
        with db_session() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._to_output_item(_output_from_row(row)) for row in rows]

    def read_output(self, project_id: str, output_id: str) -> OutputContent:
        self.require_project(project_id)
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM outputs WHERE project_id = ? AND id = ?",
                (project_id, output_id),
            ).fetchone()
        if not row:
            raise OutputNotFoundError(f"输出不存在：{output_id}")
        record = _output_from_row(row)
        project_dir = storage_service.project_dir(project_id)
        path = (project_dir / record.relative_path).resolve()
        storage_service.ensure_inside_project(project_id, path)
        if not path.exists():
            raise OutputNotFoundError(f"输出文件不存在：{record.relative_path}")

        content: str | dict[str, Any] | list[Any] | None
        binary = False
        if path.suffix.lower() == ".json":
            content = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() in {".md", ".txt", ".csv", ".svg"}:
            content = path.read_text(encoding="utf-8")
        else:
            content = None
            binary = True
        return OutputContent(
            id=record.id,
            title=record.title,
            relative_path=record.relative_path,
            mime_type=record.mime_type,
            content=content,
            binary=binary,
        )

    def output_file_path(self, project_id: str, output_id: str) -> tuple[Path, OutputRecord]:
        self.require_project(project_id)
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM outputs WHERE project_id = ? AND id = ?",
                (project_id, output_id),
            ).fetchone()
        if not row:
            raise OutputNotFoundError(f"输出不存在：{output_id}")
        record = _output_from_row(row)
        project_dir = storage_service.project_dir(project_id)
        path = (project_dir / record.relative_path).resolve()
        storage_service.ensure_inside_project(project_id, path)
        if not path.exists():
            raise OutputNotFoundError(f"输出文件不存在：{record.relative_path}")
        return path, record

    def _to_read(self, record: ProjectRecord) -> ProjectRead:
        return ProjectRead(
            id=record.id,
            name=record.name,
            domain=record.domain,
            language=record.language,
            output_format=record.output_format,
            workflow_status=record.workflow_status,
            current_step=record.current_step,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _to_output_item(self, record: OutputRecord) -> OutputItem:
        return OutputItem(
            id=record.id,
            agent_name=record.agent_name,
            kind=record.kind,
            title=record.title,
            relative_path=record.relative_path,
            mime_type=record.mime_type,
            created_at=record.created_at,
        )


project_service = ProjectService()
