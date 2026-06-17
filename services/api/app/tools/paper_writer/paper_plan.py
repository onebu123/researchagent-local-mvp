from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from app.tools.audit_log import append_audit_event
from app.tools.paper_writer.citation_binder import (
    available_evidence_summary,
    retrieve_section_passages,
    source_locator_summary,
    source_passage_ids,
    support_status_from_passages,
)
from app.tools.paper_writer.manuscript_contract import (
    SAFE_LIMITATIONS,
    SCHEMA_PREFIX,
    ensure_manuscript_dirs,
    read_json,
    utc_now,
    write_project_json,
)

PAPER_PLAN_JSON = "manuscript/paper_plan.json"
PaperType = Literal["research_article", "literature_review", "short_paper", "technical_report"]

DEFAULT_SECTIONS: dict[str, list[str]] = {
    "research_article": [
        "Abstract",
        "Introduction",
        "Related Work",
        "Methods",
        "Results",
        "Discussion",
        "Limitations",
        "Conclusion",
    ],
    "literature_review": [
        "Abstract",
        "Introduction",
        "Background",
        "Thematic Findings",
        "Evidence Gaps",
        "Limitations",
        "Conclusion",
    ],
    "short_paper": ["Abstract", "Introduction", "Method", "Findings", "Limitations", "Conclusion"],
    "technical_report": [
        "Executive Summary",
        "Background",
        "Local Evidence",
        "Analysis Notes",
        "Risks and Limitations",
        "Conclusion",
    ],
}

SECTION_PURPOSES = {
    "Abstract": "Summarize the local evidence-bound draft and its limits.",
    "Introduction": "Frame the local research question and motivation without overclaiming novelty.",
    "Related Work": "Synthesize local source passages and identify verified-evidence gaps.",
    "Background": "Explain the local literature context using source passages.",
    "Thematic Findings": "Organize local literature themes with source-passage support.",
    "Evidence Gaps": "List missing, weak, or unverified support that requires human review.",
    "Methods": "Describe local data, analysis artifacts, and provenance instead of inventing experiments.",
    "Method": "Describe local data, analysis artifacts, and provenance instead of inventing experiments.",
    "Results": "Report only descriptive local analysis, figure provenance, or supported source passages.",
    "Findings": "Report only local, evidence-bound findings and limitations.",
    "Discussion": "Interpret local support cautiously and route weak claims to limitations.",
    "Limitations": "Make unsupported, weak, or unverified evidence visible for human review.",
    "Risks and Limitations": "Make unsupported, weak, or unverified evidence visible for human review.",
    "Conclusion": "Close with a cautious summary and remaining human-review requirements.",
    "Executive Summary": "Summarize the local evidence package and review status.",
    "Local Evidence": "Summarize retrieved local passages and artifact provenance.",
    "Analysis Notes": "Summarize local descriptive analysis artifacts without inferential claims.",
}


def read_paper_plan(project_dir: Path) -> dict[str, Any]:
    payload = read_json(project_dir / PAPER_PLAN_JSON, {})
    return payload if isinstance(payload, dict) else {}


def _section_plan(
    project_dir: Path,
    project_id: str,
    section_title: str,
    topic: str,
    retrieval_mode: str,
) -> dict[str, Any]:
    query = f"{topic} {section_title} local evidence"
    passages = retrieve_section_passages(
        project_dir,
        project_id,
        query,
        top_k=5,
        retrieval_mode=retrieval_mode,
    )
    support_status = support_status_from_passages(passages)
    required_evidence_types = ["source_passages"]
    if section_title in {"Methods", "Method", "Results", "Findings", "Analysis Notes"}:
        required_evidence_types.append("analysis_artifacts")
    return {
        "section_id": section_title.lower().replace(" ", "_"),
        "title": section_title,
        "purpose": SECTION_PURPOSES.get(section_title, "Write a cautious evidence-bound section."),
        "required_evidence_types": required_evidence_types,
        "source_passage_ids": source_passage_ids(passages),
        "source_locators": source_locator_summary(passages),
        "support_status": support_status,
        "status": "ready" if support_status == "supported" else "weak_evidence" if passages else "missing_evidence",
    }


def generate_paper_plan(
    project_dir: Path,
    project_id: str,
    project_name: str,
    domain: str,
    paper_type: PaperType = "research_article",
    topic: str | None = None,
    research_question: str | None = None,
    retrieval_mode: str = "local_hybrid_fts",
) -> dict[str, Any]:
    ensure_manuscript_dirs(project_dir)
    chosen_topic = (topic or project_name or domain or "local research project").strip()
    chosen_question = (
        research_question
        or f"What does the local evidence package support about {chosen_topic}?"
    ).strip()
    sections = DEFAULT_SECTIONS.get(paper_type, DEFAULT_SECTIONS["research_article"])
    section_plans = [
        _section_plan(project_dir, project_id, title, chosen_topic, retrieval_mode) for title in sections
    ]
    evidence_summary = available_evidence_summary(project_dir, project_id)
    missing_evidence_warnings: list[str] = []
    if evidence_summary["literature_count"] == 0:
        missing_evidence_warnings.append("No local literature records are available.")
    if evidence_summary["verified_literature_count"] == 0:
        missing_evidence_warnings.append("No human-verified literature metadata is available.")
    if paper_type == "research_article" and not evidence_summary["analysis_available"]:
        missing_evidence_warnings.append(
            "No local analysis summary is available; Results must stay descriptive or be marked TODO."
        )
    if any(section["status"] == "missing_evidence" for section in section_plans):
        missing_evidence_warnings.append(
            "One or more planned sections lack source-passage support and must be written as limitations/TODOs."
        )
    payload = {
        "schema_version": f"{SCHEMA_PREFIX}.paper_plan.v1",
        "project_id": project_id,
        "created_at": utc_now(),
        "paper_plan_file": PAPER_PLAN_JSON,
        "paper_type": paper_type,
        "topic": chosen_topic,
        "domain": domain,
        "title_candidates": [
            f"Evidence-grounded draft on {chosen_topic}",
            f"A local audit-first manuscript draft for {chosen_topic}",
            f"Traceable evidence synthesis for {chosen_topic}",
        ],
        "research_question": chosen_question,
        "thesis_summary": (
            "The draft may summarize only what project-local source passages, analysis artifacts, "
            "and figure provenance support. Unsupported material must remain visible."
        ),
        "target_sections": section_plans,
        "required_evidence": [
            {
                "section_id": item["section_id"],
                "required_evidence_types": item["required_evidence_types"],
                "status": item["status"],
                "source_passage_ids": item["source_passage_ids"],
            }
            for item in section_plans
        ],
        "available_evidence_summary": evidence_summary,
        "missing_evidence_warnings": missing_evidence_warnings,
        "human_inputs_required": [
            "Review and verify references before external use.",
            "Review every generated claim and source passage.",
            "Provide real experimental/statistical results before asserting formal findings.",
        ],
        "design_inspirations": [
            "AI-Scientist-style writeup/review loop, without autonomous code execution.",
            "STORM-style outline-before-draft structure.",
            "PaperQA2-style source-passage grounding.",
            "GPT Researcher-style planner-to-publisher separation.",
        ],
        "limitations": SAFE_LIMITATIONS,
    }
    write_project_json(project_dir, PAPER_PLAN_JSON, payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_auto_paper_plan",
        "Auto Paper Writer plan was generated from local evidence artifacts.",
        {
            "paper_plan_file": PAPER_PLAN_JSON,
            "paper_type": paper_type,
            "section_count": len(section_plans),
            "missing_evidence_warning_count": len(missing_evidence_warnings),
        },
        source="api",
        event_category="manuscript",
        risk_level="medium" if missing_evidence_warnings else "low",
        entity_type="manuscript",
        entity_id="paper_plan",
    )
    return payload
