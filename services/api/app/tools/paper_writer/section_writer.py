from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.claim_audit import run_draft_claim_audit
from app.tools.paper_writer.citation_binder import (
    retrieve_section_passages,
    source_locator_summary,
    source_passage_ids,
    support_status_from_passages,
)
from app.tools.paper_writer.manuscript_contract import (
    AI_DRAFT_NOTICE,
    SAFE_LIMITATIONS,
    SCHEMA_PREFIX,
    contract_warnings_for_text,
    ensure_manuscript_dirs,
    make_safe_sentence,
    markdown_heading,
    normalize_section_id,
    read_json,
    utc_now,
    write_project_json,
    write_project_text,
)
from app.tools.paper_writer.outline_builder import generate_paper_outline, read_paper_outline

DRAFT_FULL_MD = "manuscript/draft_full.md"
WRITING_AUDIT_JSON = "manuscript/writing_audit.json"
WRITING_ROUNDS_JSONL = "manuscript/writing_rounds.jsonl"
SECTIONS_DIR = "manuscript/sections"


def read_full_draft_status(project_dir: Path) -> dict[str, Any]:
    audit = read_json(project_dir / WRITING_AUDIT_JSON, {})
    if not isinstance(audit, dict):
        audit = {}
    return {
        "available": (project_dir / DRAFT_FULL_MD).exists(),
        "draft_file": DRAFT_FULL_MD if (project_dir / DRAFT_FULL_MD).exists() else None,
        "writing_audit_file": WRITING_AUDIT_JSON if audit else None,
        "writing_audit": audit,
    }


def _append_round(project_dir: Path, record: dict[str, Any]) -> None:
    path = project_dir / WRITING_ROUNDS_JSONL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _short_passage_note(passages: list[dict[str, Any]]) -> str:
    locators = source_locator_summary(passages, limit=3)
    if not locators:
        return "No local source passage is available for this paragraph."
    return "Local source passages: " + ", ".join(f"[{locator}]" for locator in locators)


def _paragraphs_for_section(
    title: str,
    topic: str,
    passages: list[dict[str, Any]],
    support_status: str,
) -> list[dict[str, Any]]:
    passage_ids = source_passage_ids(passages)
    source_note = _short_passage_note(passages)
    status_phrase = {
        "supported": "The local evidence package supports a cautious descriptive statement",
        "weakly_supported": "The local evidence package provides partial support and requires human review",
        "unsupported": "The local evidence package is insufficient for a substantive claim",
    }.get(support_status, "The local evidence package requires human review")
    paragraphs: list[dict[str, Any]] = []

    if title in {"Abstract", "Executive Summary"}:
        text = (
            f"{AI_DRAFT_NOTICE} This draft addresses {topic} using project-local literature, "
            "analysis artifacts, source passages, and audit records. It does not present unverified "
            "statistics, reference metadata, experimental results, or publication-ready conclusions."
        )
        paragraphs.append(_paragraph("p001", text, passage_ids, support_status))
        text = (
            f"{status_phrase} for the current section. {source_note} Missing or weak evidence is "
            "kept visible for reviewer and human approval workflows."
        )
        paragraphs.append(_paragraph("p002", text, passage_ids, support_status))
    elif title in {"Introduction", "Background"}:
        text = (
            f"This section frames {topic} as a local, auditable research draft. The purpose is to "
            "organize the available sources and expose evidence gaps before any external use."
        )
        paragraphs.append(_paragraph("p001", text, passage_ids, "needs_human_review"))
        text = f"{status_phrase} for context about {topic}. {source_note}"
        paragraphs.append(_paragraph("p002", text, passage_ids, support_status))
    elif title in {"Related Work", "Thematic Findings", "Local Evidence"}:
        if passages:
            text = (
                f"The local retrieved passages describe {topic} as a project-specific evidence theme. "
                f"{source_note} Because metadata and parser quality may be incomplete, this synthesis remains a draft note."
            )
            paragraphs.append(_paragraph("p001", text, passage_ids, support_status))
        else:
            text = (
                f"TODO: add local, reviewable source passages before writing a related-work claim about {topic}."
            )
            paragraphs.append(_paragraph("p001", text, [], "unsupported"))
    elif title in {"Methods", "Method"}:
        text = (
            "The current workflow uses local project artifacts: uploaded literature, parsed text, "
            "RAG chunks, analysis summaries, figure provenance, claim audit records, and review logs. "
            "It does not invent experiments or formal statistical procedures."
        )
        paragraphs.append(_paragraph("p001", text, passage_ids, "needs_human_review"))
    elif title in {"Results", "Findings", "Analysis Notes"}:
        text = (
            "Results in this draft are limited to local descriptive artifacts and source-passage support. "
            "Any missing analysis, figure, or source record is treated as a limitation rather than a finding."
        )
        paragraphs.append(_paragraph("p001", text, passage_ids, "needs_human_review"))
        if passages:
            text = f"{status_phrase} for a cautious local finding about {topic}. {source_note}"
            paragraphs.append(_paragraph("p002", text, passage_ids, support_status))
    elif title in {"Discussion"}:
        text = (
            f"The evidence package can support cautious discussion of {topic} only where source passages "
            "or analysis artifacts are available. Unsupported interpretations should be revised, removed, "
            "or moved into limitations after human review."
        )
        paragraphs.append(_paragraph("p001", text, passage_ids, "needs_human_review"))
    elif title in {"Limitations", "Risks and Limitations", "Evidence Gaps"}:
        text = (
            "Limitations include unverified metadata, parser-quality uncertainty, incomplete source-passage "
            "coverage, and the need for human review of every claim, reference, figure, and revision."
        )
        paragraphs.append(_paragraph("p001", text, passage_ids, "needs_human_review"))
        if support_status == "unsupported":
            text = f"The local evidence is insufficient for one or more claims about {topic}; add sources or keep the claim as TODO."
            paragraphs.append(_paragraph("p002", text, [], "unsupported"))
    else:
        text = f"{status_phrase} for a cautious draft section on {topic}. {source_note}"
        paragraphs.append(_paragraph("p001", text, passage_ids, support_status))

    return paragraphs


def _paragraph(
    paragraph_id: str,
    text: str,
    passage_ids: list[str],
    support_status: str,
) -> dict[str, Any]:
    safe_text = make_safe_sentence(text)
    warnings = contract_warnings_for_text(safe_text, support_status=support_status)
    return {
        "paragraph_id": paragraph_id,
        "text": safe_text,
        "source_passage_ids": passage_ids,
        "claim_ids": [],
        "support_status": support_status,
        "warnings": warnings,
    }


def _section_markdown(title: str, paragraphs: list[dict[str, Any]]) -> str:
    lines = [markdown_heading(title, level=1), ""]
    for paragraph in paragraphs:
        lines.extend([str(paragraph.get("text") or ""), ""])
    return "\n".join(lines).strip() + "\n"


def _section_payload(
    project_dir: Path,
    project_id: str,
    section: dict[str, Any],
    topic: str,
    retrieval_mode: str,
) -> dict[str, Any]:
    title = str(section.get("title") or "Section")
    section_id = str(section.get("section_id") or normalize_section_id(title))
    passages = retrieve_section_passages(
        project_dir,
        project_id,
        f"{topic} {title} draft evidence",
        top_k=5,
        retrieval_mode=retrieval_mode,
    )
    support_status = support_status_from_passages(passages)
    if section.get("status") == "missing_evidence":
        support_status = "unsupported"
    paragraphs = _paragraphs_for_section(title, topic, passages, support_status)
    unsupported_claims = [
        paragraph["text"] for paragraph in paragraphs if paragraph.get("support_status") == "unsupported"
    ]
    missing_notes = []
    if support_status == "unsupported":
        missing_notes.append("Section lacks sufficient local source-passage support.")
    relative_path = f"{SECTIONS_DIR}/{section_id}.md"
    write_project_text(project_dir, relative_path, _section_markdown(title, paragraphs))
    return {
        "schema_version": f"{SCHEMA_PREFIX}.section_draft.v1",
        "section_id": section_id,
        "title": title,
        "relative_path": relative_path,
        "draft_markdown": _section_markdown(title, paragraphs),
        "paragraphs": paragraphs,
        "source_passage_ids": sorted({pid for paragraph in paragraphs for pid in paragraph["source_passage_ids"]}),
        "source_locators": source_locator_summary(passages),
        "support_status": support_status,
        "unsupported_claims": unsupported_claims,
        "missing_evidence_notes": missing_notes,
        "human_review_required": support_status != "supported" or any(
            paragraph.get("warnings") for paragraph in paragraphs
        ),
    }


def _draft_markdown(outline: dict[str, Any], sections: list[dict[str, Any]]) -> str:
    title = outline.get("topic") or "Evidence-grounded auto paper draft"
    lines = [
        markdown_heading(str(title), level=1),
        "",
        f"> {AI_DRAFT_NOTICE}",
        "> This draft is not peer review, citation verification, or publication-ready scientific proof.",
        "",
    ]
    for section in sections:
        lines.append(section["draft_markdown"].strip())
        lines.append("")
    lines.extend(
        [
            markdown_heading("References", level=1),
            "",
            "Verified references are not automatically generated. Use the local literature metadata, BibTeX, and human review workflows before external use.",
            "",
            markdown_heading("Writing Audit Notice", level=1),
            "",
            "Every generated section must be reviewed against source passages, claim audit results, and human-review decisions.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def generate_full_draft(
    project_dir: Path,
    project_id: str,
    project_name: str,
    domain: str,
    retrieval_mode: str = "local_hybrid_fts",
    run_claim_audit_after: bool = True,
) -> dict[str, Any]:
    ensure_manuscript_dirs(project_dir)
    outline = read_paper_outline(project_dir)
    if not outline:
        outline = generate_paper_outline(
            project_dir,
            project_id,
            project_name=project_name,
            domain=domain,
            retrieval_mode=retrieval_mode,
        )
    topic = str(outline.get("topic") or project_name or domain or "local research project")
    sections: list[dict[str, Any]] = []
    for section in outline.get("sections", []):
        if isinstance(section, dict):
            payload = _section_payload(project_dir, project_id, section, topic, retrieval_mode)
            sections.append(payload)
            _append_round(
                project_dir,
                {
                    "created_at": utc_now(),
                    "step": "section_draft",
                    "section_id": payload["section_id"],
                    "support_status": payload["support_status"],
                    "relative_path": payload["relative_path"],
                    "human_review_required": payload["human_review_required"],
                },
            )
    draft_markdown = _draft_markdown(outline, sections)
    write_project_text(project_dir, DRAFT_FULL_MD, draft_markdown)
    status_counts = {"supported": 0, "weakly_supported": 0, "unsupported": 0, "needs_human_review": 0}
    for section in sections:
        status = str(section.get("support_status") or "needs_human_review")
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts["needs_human_review"] += 1
    writing_audit = {
        "schema_version": f"{SCHEMA_PREFIX}.writing_audit.v1",
        "project_id": project_id,
        "created_at": utc_now(),
        "draft_file": DRAFT_FULL_MD,
        "outline_file": "manuscript/outline.json",
        "writing_rounds_file": WRITING_ROUNDS_JSONL,
        "section_count": len(sections),
        "section_status_counts": status_counts,
        "human_review_required": True,
        "sections": [
            {
                "section_id": section["section_id"],
                "title": section["title"],
                "relative_path": section["relative_path"],
                "support_status": section["support_status"],
                "source_passage_ids": section["source_passage_ids"],
                "missing_evidence_notes": section["missing_evidence_notes"],
                "human_review_required": section["human_review_required"],
            }
            for section in sections
        ],
        "limitations": SAFE_LIMITATIONS,
    }
    write_project_json(project_dir, WRITING_AUDIT_JSON, writing_audit)

    claim_audit: dict[str, Any] | None = None
    if run_claim_audit_after:
        try:
            claim_audit = run_draft_claim_audit(
                project_dir,
                project_id,
                manuscript_relative_path=DRAFT_FULL_MD,
                retrieval_mode=retrieval_mode,
                top_k=5,
            )
            writing_audit["claim_audit_file"] = claim_audit.get("claim_audit_file")
            writing_audit["claim_audit_summary"] = claim_audit.get("summary")
            write_project_json(project_dir, WRITING_AUDIT_JSON, writing_audit)
        except Exception as exc:  # claim audit is useful, but draft creation should remain inspectable
            writing_audit["claim_audit_error"] = exc.__class__.__name__
            write_project_json(project_dir, WRITING_AUDIT_JSON, writing_audit)

    append_audit_event(
        project_dir,
        project_id,
        "generate_auto_paper_draft",
        "Auto Paper Writer generated an evidence-bound manuscript draft.",
        {
            "draft_file": DRAFT_FULL_MD,
            "writing_audit_file": WRITING_AUDIT_JSON,
            "section_count": len(sections),
            "human_review_required": True,
            "claim_audit_generated": bool(claim_audit),
        },
        source="api",
        event_category="manuscript",
        risk_level="medium",
        entity_type="manuscript",
        entity_id="draft_full",
    )
    return {
        "project_id": project_id,
        "created_at": writing_audit["created_at"],
        "draft_file": DRAFT_FULL_MD,
        "writing_audit_file": WRITING_AUDIT_JSON,
        "writing_rounds_file": WRITING_ROUNDS_JSONL,
        "sections": sections,
        "writing_audit": writing_audit,
        "claim_audit": claim_audit,
        "limitations": SAFE_LIMITATIONS,
    }
