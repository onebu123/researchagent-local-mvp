from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.file_tools import ensure_dir, write_json, write_text

AI_DRAFT_NOTICE = (
    "AI-generated draft from local project evidence. Requires human review before external use."
)
SCHEMA_PREFIX = "researchagent.auto_paper_writer"

RESTRICTED_ASSERTION_TERMS = [
    "statistically significant",
    "significant",
    "p-value",
    "p values",
    "p-values",
    "causal",
    "causality",
    "proves",
    "proved",
    "demonstrated",
    "confirmed",
    "breakthrough",
    "novel discovery",
    "显著",
    "证明",
    "证实",
    "因果",
]

SAFE_LIMITATIONS = [
    "This auto paper writer creates an auditable draft, not a submission-ready manuscript.",
    "Every substantive claim must be tied to local source passages, analysis artifacts, or figure provenance.",
    "Unsupported material is written as a limitation or TODO, not as a research conclusion.",
    "Human review is required for references, claims, statistics, figures, and final wording.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def relative_path(path: Path, project_dir: Path) -> str:
    return path.resolve().relative_to(project_dir.resolve()).as_posix()


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def restricted_term_hits(text: str) -> list[str]:
    lowered = text.lower()
    hits: list[str] = []
    for term in RESTRICTED_ASSERTION_TERMS:
        if term.isascii():
            if re.search(r"\b" + re.escape(term.lower()) + r"\b", lowered):
                hits.append(term)
        elif term in text:
            hits.append(term)
    return sorted(set(hits))


def make_safe_sentence(text: str) -> str:
    cleaned = re.sub(r"\b(?:proves?|proved|demonstrated|confirmed)\b", "describes", text, flags=re.I)
    cleaned = re.sub(r"\b(?:statistically significant|significant)\b", "descriptive", cleaned, flags=re.I)
    cleaned = re.sub(r"\b(?:causal|causality)\b", "associational or contextual", cleaned, flags=re.I)
    cleaned = re.sub(r"\bp-?values?\b", "formal statistical-test outputs", cleaned, flags=re.I)
    cleaned = cleaned.replace("显著", "描述性地")
    cleaned = cleaned.replace("证明", "描述")
    cleaned = cleaned.replace("证实", "描述")
    cleaned = cleaned.replace("因果", "关联或背景")
    return cleaned


def normalize_section_id(title: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", title.strip().lower()).strip("_")
    return cleaned or "section"


def markdown_heading(title: str, level: int = 1) -> str:
    return f"{'#' * level} {title.strip()}"


def write_project_json(project_dir: Path, relative: str, payload: Any) -> None:
    write_json(project_dir / relative, payload)


def write_project_text(project_dir: Path, relative: str, content: str) -> None:
    write_text(project_dir / relative, content)


def ensure_manuscript_dirs(project_dir: Path) -> None:
    ensure_dir(project_dir / "manuscript")
    ensure_dir(project_dir / "manuscript" / "sections")


def contract_warnings_for_text(text: str, support_status: str = "needs_human_review") -> list[str]:
    warnings: list[str] = []
    hits = restricted_term_hits(text)
    if hits:
        warnings.append("restricted_assertion_terms:" + ",".join(hits))
    if support_status != "supported":
        warnings.append("human_review_required")
    return sorted(set(warnings))
