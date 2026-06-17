from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.paper_writer.manuscript_contract import restricted_term_hits, read_json, read_text
from app.tools.paper_writer.section_writer import DRAFT_FULL_MD, WRITING_AUDIT_JSON


def evaluate_auto_paper_draft(project_dir: Path) -> dict[str, Any]:
    draft = read_text(project_dir / DRAFT_FULL_MD)
    audit = read_json(project_dir / WRITING_AUDIT_JSON, {})
    hits = restricted_term_hits(draft)
    has_notice = "AI-generated draft" in draft and "Requires human review" in draft
    return {
        "draft_file": DRAFT_FULL_MD,
        "available": bool(draft),
        "has_ai_generated_notice": has_notice,
        "restricted_term_hits": hits,
        "section_count": audit.get("section_count", 0) if isinstance(audit, dict) else 0,
        "passes_safety_smoke": bool(draft) and has_notice and not hits,
        "limitations": [
            "This is a local smoke check, not a writing-quality benchmark.",
            "Absence of restricted wording does not prove scientific correctness.",
        ],
    }
