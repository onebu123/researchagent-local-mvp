from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectRecord:
    id: str
    name: str
    domain: str
    language: str
    output_format: str
    slug: str
    workflow_status: str
    current_step: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class OutputRecord:
    id: str
    project_id: str
    agent_name: str
    kind: str
    title: str
    relative_path: str
    mime_type: str
    created_at: str


@dataclass(frozen=True)
class LiteratureMetadataRecord:
    literature_id: str
    source_file: str
    title: str
    authors: list[str]
    year: int | None
    doi: str | None
    journal: str | None
    source_type: str
    parsed_text_file: str
    parse_metadata_file: str | None
    parse_status: str
    metadata_status: str
    human_verified: bool
    quality_score: float | None = None
    quality_label: str | None = None
    needs_manual_review: bool | None = None
