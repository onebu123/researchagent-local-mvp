from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Language = Literal["zh", "en"]
OutputFormat = Literal["markdown"]
EvidenceStatus = Literal["supported", "partial", "missing", "needs_human_review"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    domain: str = Field(default="materials", min_length=1, max_length=80)
    language: Language = "zh"
    output_format: OutputFormat = "markdown"


class ProjectRead(BaseModel):
    id: str
    name: str
    domain: str
    language: str
    output_format: str
    workflow_status: str
    current_step: str
    created_at: str
    updated_at: str


class ResourceSummary(BaseModel):
    literature_count: int
    dataset_count: int
    figure_count: int
    manuscript_count: int
    review_count: int


class OutputItem(BaseModel):
    id: str
    agent_name: str
    kind: str
    title: str
    relative_path: str
    mime_type: str
    created_at: str


class ProjectDetail(ProjectRead):
    resources: ResourceSummary
    latest_outputs: list[OutputItem]


class UploadResponse(BaseModel):
    project_id: str
    filename: str
    relative_path: str
    size_bytes: int
    message: str


class StepRunRequest(BaseModel):
    step: str = Field(min_length=1)


class WorkflowRunResponse(BaseModel):
    project_id: str
    workflow_status: str
    current_step: str
    outputs: list[OutputItem]
    errors: list[str] = Field(default_factory=list)


class WorkflowStatusResponse(BaseModel):
    project_id: str
    workflow_status: str
    current_step: str
    errors: list[str] = Field(default_factory=list)


class OutputContent(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    title: str
    relative_path: str
    mime_type: str
    content: str | dict[str, Any] | list[Any] | None
    binary: bool = False


class LiteratureRecord(BaseModel):
    literature_id: str
    source_file: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    journal: str | None = None
    source_type: Literal["pdf", "markdown", "txt"]
    parsed_text_file: str
    parse_metadata_file: str | None = None
    parse_status: str = "success"
    metadata_status: Literal["placeholder", "extracted", "verified"]
    human_verified: bool = False
    warnings: list[str] = Field(default_factory=list)
    page_count: int | None = None
    empty_page_count: int | None = None
    pages: list[dict[str, Any]] = Field(default_factory=list)
    quality_score: float | None = None
    quality_label: str | None = None
    needs_manual_review: bool | None = None
    reference_verification_status: str | None = None
    reference_verification_id: str | None = None


class LiteraturePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    doi: str | None = None
    journal: str | None = None
    metadata_status: Literal["placeholder", "extracted", "verified"] | None = None
    human_verified: bool | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title must not be empty")
        return cleaned

    @field_validator("authors")
    @classmethod
    def validate_authors(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if any(not isinstance(author, str) or not author.strip() for author in value):
            raise ValueError("authors must be a list of non-empty strings")
        return [author.strip() for author in value]

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int | None) -> int | None:
        if value is None:
            return value
        current_year = datetime.now().year
        if value < 1500 or value > current_year:
            raise ValueError(f"year must be between 1500 and {current_year}")
        return value

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if cleaned == "":
            return None
        if not cleaned.startswith("10.") or "/" not in cleaned:
            raise ValueError("doi must start with '10.' and contain '/'")
        return cleaned

    @field_validator("journal")
    @classmethod
    def validate_journal(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class EvidenceClaim(BaseModel):
    claim_id: str
    section: str
    claim: str
    evidence_type: str
    data_file: str | None = None
    analysis_file: str | None = None
    analysis_provenance_file: str | None = None
    figure_file: str | None = None
    figure_provenance_file: str | None = None
    manuscript_file: str | None = None
    evidence_status: EvidenceStatus
    human_verified: bool = False


class EvidenceClaimReviewRequest(BaseModel):
    human_status: Literal[
        "supported",
        "partially_supported",
        "unsupported",
        "needs_more_evidence",
    ]
    reason: str | None = Field(default="", max_length=1000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str:
        return (value or "").strip()


class RevisionDecisionRequest(BaseModel):
    decision: Literal["accepted", "rejected"]
    reason: str | None = Field(default=None, max_length=1000)


class ManuscriptPatchGenerateRequest(BaseModel):
    source_manuscript: str = Field(default="manuscript/draft.md", max_length=240)

    @field_validator("source_manuscript")
    @classmethod
    def validate_source_manuscript(cls, value: str) -> str:
        cleaned = value.strip().replace("\\", "/")
        if not cleaned:
            raise ValueError("source_manuscript must not be empty")
        if cleaned.startswith("/") or ".." in cleaned.split("/"):
            raise ValueError("source_manuscript must stay inside project")
        if cleaned != "manuscript/draft.md" and not cleaned.startswith("manuscript/versions/"):
            raise ValueError("source_manuscript must be draft.md or manuscript version")
        return cleaned


class ManuscriptPatchConfirmRequest(BaseModel):
    decision: Literal["confirmed", "rejected"]
    reason: str | None = Field(default="", max_length=1000)


class PatchMergeConfirmRequest(BaseModel):
    decision: Literal["confirmed", "rejected"]
    reason: str | None = Field(default="", max_length=1000)


class ManuscriptPatchItemEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    after: str = Field(min_length=1, max_length=5000)
    reason: str | None = Field(default="", max_length=1000)

    @field_validator("after")
    @classmethod
    def validate_after(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("after must not be empty")
        return cleaned


class PatchIdsRequest(BaseModel):
    patch_ids: list[str] = Field(min_length=1)

    @field_validator("patch_ids")
    @classmethod
    def validate_patch_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if not cleaned:
            raise ValueError("patch_ids must not be empty")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("patch_ids must be unique")
        for patch_id in cleaned:
            if not patch_id.startswith("patch_"):
                raise ValueError("patch_ids must start with patch_")
        return cleaned


class ManuscriptDiffGenerateRequest(BaseModel):
    base_file: str = Field(default="manuscript/draft.md", max_length=240)
    version_id: str = Field(min_length=1, max_length=80)

    @field_validator("base_file")
    @classmethod
    def validate_base_file(cls, value: str) -> str:
        cleaned = value.strip().replace("\\", "/")
        if not cleaned:
            raise ValueError("base_file must not be empty")
        if cleaned.startswith("/") or ".." in cleaned.split("/"):
            raise ValueError("base_file must stay inside project")
        if not cleaned.startswith("manuscript/"):
            raise ValueError("base_file must stay under manuscript")
        return cleaned

    @field_validator("version_id")
    @classmethod
    def validate_version_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("manuscript_v"):
            raise ValueError("version_id must start with manuscript_v")
        return cleaned


class RevisionLineDiffGenerateRequest(BaseModel):
    base_file: str = Field(default="manuscript/draft.md", max_length=240)
    target_file: str = Field(min_length=1, max_length=240)

    @field_validator("base_file")
    @classmethod
    def validate_base_file(cls, value: str) -> str:
        cleaned = value.strip().replace("\\", "/")
        if not cleaned:
            raise ValueError("base_file must not be empty")
        if cleaned.startswith("/") or ".." in cleaned.split("/"):
            raise ValueError("base_file must stay inside project")
        if not cleaned.startswith("manuscript/") or not cleaned.endswith(".md"):
            raise ValueError("base_file must stay under manuscript and end with .md")
        return cleaned

    @field_validator("target_file")
    @classmethod
    def validate_target_file(cls, value: str) -> str:
        cleaned = value.strip().replace("\\", "/")
        if not cleaned:
            raise ValueError("target_file must not be empty")
        if cleaned.startswith("/") or ".." in cleaned.split("/"):
            raise ValueError("target_file must stay inside project")
        if not cleaned.startswith("manuscript/versions/") or not cleaned.endswith(".md"):
            raise ValueError("target_file must be a manuscript version markdown file")
        return cleaned


class IssueResolutionReviewRequest(BaseModel):
    version_id: str = Field(min_length=1, max_length=80)
    human_status: Literal["resolved", "unresolved", "needs_review"]
    reason: str | None = Field(default="", max_length=1000)

    @field_validator("version_id")
    @classmethod
    def validate_version_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("manuscript_v"):
            raise ValueError("version_id must start with manuscript_v")
        return cleaned


class LiteratureMetadataRevertSuggestionRequest(BaseModel):
    field: str = Field(min_length=1, max_length=80)
    source_history_id: str = Field(min_length=1, max_length=80)

    @field_validator("field")
    @classmethod
    def validate_field(cls, value: str) -> str:
        cleaned = value.strip()
        allowed = {
            "title",
            "authors",
            "year",
            "doi",
            "journal",
            "metadata_status",
            "human_verified",
        }
        if cleaned not in allowed:
            raise ValueError("field is not editable literature metadata")
        return cleaned

    @field_validator("source_history_id")
    @classmethod
    def validate_source_history_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("lit_hist_"):
            raise ValueError("source_history_id must start with lit_hist_")
        return cleaned


class MetadataRevertPreviewRequest(BaseModel):
    field: str = Field(min_length=1, max_length=80)
    source_history_id: str = Field(min_length=1, max_length=80)

    @field_validator("field")
    @classmethod
    def validate_field(cls, value: str) -> str:
        cleaned = value.strip()
        allowed = {
            "title",
            "authors",
            "year",
            "doi",
            "journal",
            "metadata_status",
            "human_verified",
        }
        if cleaned not in allowed:
            raise ValueError("field is not editable literature metadata")
        return cleaned

    @field_validator("source_history_id")
    @classmethod
    def validate_source_history_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("lit_hist_"):
            raise ValueError("source_history_id must start with lit_hist_")
        return cleaned


class AnalysisCompareRequest(BaseModel):
    base_provenance: str = Field(default="analysis/analysis_provenance.json", max_length=240)
    target_provenance: str = Field(default="analysis/analysis_provenance.json", max_length=240)

    @field_validator("base_provenance", "target_provenance")
    @classmethod
    def validate_provenance_path(cls, value: str) -> str:
        cleaned = value.strip().replace("\\", "/")
        if not cleaned:
            raise ValueError("analysis provenance path must not be empty")
        if cleaned.startswith("/") or ".." in cleaned.split("/"):
            raise ValueError("analysis provenance path must stay inside project")
        if not cleaned.startswith("analysis/") or not cleaned.endswith(".json"):
            raise ValueError("analysis provenance path must stay under analysis and end with .json")
        return cleaned


class RevisionDiffReviewRequest(BaseModel):
    human_status: Literal["accepted", "rejected", "needs_rewrite", "needs_evidence"]
    reason: str | None = Field(default="", max_length=1000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str:
        return (value or "").strip()


class MetadataReviewActionRequest(BaseModel):
    field: str = Field(min_length=1, max_length=80)
    action: Literal["accept_change", "reject_change", "needs_verification", "request_revert"]
    source_history_id: str = Field(min_length=1, max_length=80)
    reason: str | None = Field(default="", max_length=1000)

    @field_validator("field")
    @classmethod
    def validate_field(cls, value: str) -> str:
        cleaned = value.strip()
        allowed = {
            "title",
            "authors",
            "year",
            "doi",
            "journal",
            "metadata_status",
            "human_verified",
        }
        if cleaned not in allowed:
            raise ValueError("field is not editable literature metadata")
        return cleaned

    @field_validator("source_history_id")
    @classmethod
    def validate_source_history_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("lit_hist_"):
            raise ValueError("source_history_id must start with lit_hist_")
        return cleaned

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str:
        return (value or "").strip()


class PDFPageReviewRequest(BaseModel):
    source_file: str = Field(min_length=1, max_length=240)
    page_number: int = Field(ge=1)
    human_status: Literal[
        "accepted_as_readable",
        "needs_ocr",
        "ignore_page",
        "needs_manual_check",
    ]
    reason: str | None = Field(default="", max_length=1000)

    @field_validator("source_file")
    @classmethod
    def validate_source_file(cls, value: str) -> str:
        cleaned = value.strip().replace("\\", "/")
        if not cleaned:
            raise ValueError("source_file must not be empty")
        if cleaned.startswith("/") or ".." in cleaned.split("/"):
            raise ValueError("source_file must stay inside project")
        if not cleaned.startswith("literature/") or not cleaned.lower().endswith(".pdf"):
            raise ValueError("source_file must be a PDF under literature")
        return cleaned

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str:
        return (value or "").strip()


class AuditFilteredExportRequest(BaseModel):
    event_category: Literal[
        "workflow",
        "file",
        "literature",
        "review",
        "patch",
        "merge",
        "version",
        "audit",
        "analysis",
        "trust",
        "system",
    ] | None = None
    risk_level: Literal["low", "medium", "high"] | None = None
    entity_type: Literal[
        "project",
        "file",
        "literature",
        "review_issue",
        "patch",
        "merge",
        "version",
        "audit_export",
        "analysis",
        "evidence_claim",
        "trust",
        "readiness_report",
        "pdf_page",
        "metadata_revert_preview",
        "workflow",
    ] | None = None
    entity_id: str | None = Field(default=None, max_length=120)

    @field_validator("entity_id")
    @classmethod
    def validate_entity_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if "/" in cleaned or "\\" in cleaned or ".." in cleaned:
            raise ValueError("entity_id must be an identifier, not a path")
        return cleaned


class FigureProvenanceRecord(BaseModel):
    figure_id: str
    title: str
    figure_type: str
    source_data: str
    analysis_file: str
    script_or_function: str
    output_files: list[str]
    is_ai_generated: bool
    is_experimental_result: bool
    created_at: str
    data_hash: str
    warnings: list[str] = Field(default_factory=list)


class LLMTestRequest(BaseModel):
    prompt: str = Field(default="Return a short JSON health check.", max_length=1000)
    prompt_version: str = Field(default="literature_answer_v1", max_length=120)

    @field_validator("prompt", "prompt_version")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned


class LiteratureRAGAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("question must not be empty")
        return cleaned


class LiteratureMetadataLookupRequest(BaseModel):
    provider: Literal["mock_fixture", "crossref_optional", "semantic_scholar_optional"] = "mock_fixture"


class ReferenceVerificationRunRequest(BaseModel):
    literature_id: str | None = Field(default=None, max_length=120)
    provider: Literal[
        "mock_fixture",
        "crossref_optional",
        "semantic_scholar_optional",
        "pubmed_optional",
    ] = "mock_fixture"

    @field_validator("literature_id")
    @classmethod
    def validate_literature_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if "/" in cleaned or "\\" in cleaned or ".." in cleaned:
            raise ValueError("literature_id must be an identifier, not a path")
        return cleaned


class ReferenceApprovalRequest(BaseModel):
    decision: Literal["approved", "rejected", "needs_manual_check"]
    reason: str | None = Field(default="", max_length=1000)
    apply_to_literature_index: bool = False

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str:
        return (value or "").strip()
