from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PendingOutput(BaseModel):
    agent_name: str
    kind: str
    title: str
    relative_path: str
    mime_type: str


class ResearchState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    project_id: str
    project_name: str
    domain: str
    language: str
    output_format: str
    literature_files: list[str] = Field(default_factory=list)
    literature_index: list[dict[str, Any]] = Field(default_factory=list)
    data_files: list[str] = Field(default_factory=list)
    literature_review: str | None = None
    candidate_topics: list[dict[str, Any]] = Field(default_factory=list)
    novelty_report: dict[str, Any] | None = None
    analysis_results: dict[str, Any] | None = None
    figures: list[dict[str, Any]] = Field(default_factory=list)
    manuscript: str | None = None
    refined_manuscript: str | None = None
    review_report: dict[str, Any] | None = None
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    workflow_status: str = "idle"
    current_step: str = "not_started"
    errors: list[str] = Field(default_factory=list)
    project_dir: Path
    literature_is_placeholder: bool = False
    outputs: list[PendingOutput] = Field(default_factory=list)
