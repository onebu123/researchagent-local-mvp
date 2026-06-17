from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.auto_scientist.contracts import (
    IDEAS_JSON,
    SAFETY_LIMITATIONS,
    SCHEMA_PREFIX,
    ensure_auto_scientist_dirs,
    read_json,
    utc_now,
    write_project_json,
)
from app.tools.auto_scientist.reference_brief import (
    REFERENCE_BRIEF_JSON,
    REFERENCE_BRIEF_MD,
    build_reference_brief,
)
from app.tools.paper_writer.citation_binder import available_evidence_summary


def read_scientist_ideas(project_dir: Path) -> dict[str, Any]:
    payload = read_json(project_dir / IDEAS_JSON, {})
    return payload if isinstance(payload, dict) else {}


def _idea(
    index: int,
    topic: str,
    title: str,
    hypothesis: str,
    experiment_templates: list[str],
    rationale: str,
    feasibility_notes: list[str],
) -> dict[str, Any]:
    return {
        "idea_id": f"idea_{index:03d}",
        "title": title,
        "topic": topic,
        "hypothesis": hypothesis,
        "rationale": rationale,
        "experiment_templates": experiment_templates,
        "expected_outputs": [
            "experiment_result.json",
            "metrics.json",
            "summary.md",
            "optional_svg_figure",
        ],
        "feasibility_notes": feasibility_notes,
        "risk_level": "low",
        "human_review_required": True,
        "status": "proposed",
    }


def generate_scientist_ideas(
    project_dir: Path,
    project_id: str,
    project_name: str,
    domain: str,
    topic: str | None = None,
    research_question: str | None = None,
    max_ideas: int = 3,
    reference_literature_ids: list[str] | None = None,
) -> dict[str, Any]:
    ensure_auto_scientist_dirs(project_dir)
    chosen_topic = (topic or project_name or domain or "local research project").strip()
    chosen_question = (
        research_question or f"What can the local evidence and project artifacts support about {chosen_topic}?"
    ).strip()
    evidence = available_evidence_summary(project_dir, project_id)
    reference_brief: dict[str, Any] | None = None
    reference_summary: dict[str, Any] = {}
    selected_reference_ids: list[str] = []
    if reference_literature_ids:
        reference_brief = build_reference_brief(project_dir, project_id, reference_literature_ids)
        selected_reference_ids = [
            str(item)
            for item in reference_brief.get("reference_literature_ids", [])
            if isinstance(item, str)
        ]
        reference_summary = (
            reference_brief.get("summary") if isinstance(reference_brief.get("summary"), dict) else {}
        )
    feasibility_notes = [
        f"local literature records: {evidence.get('literature_count', 0)}",
        f"local RAG chunks: {evidence.get('rag_chunk_count', 0)}",
        f"analysis artifact available: {bool(evidence.get('analysis_available'))}",
        f"figure records: {evidence.get('figure_count', 0)}",
    ]
    if reference_brief:
        feasibility_notes.extend(
            [
                f"selected local references: {reference_summary.get('reference_count', 0)}",
                f"reference source passages: {reference_summary.get('source_passage_count', 0)}",
                f"reference review warnings: {reference_summary.get('review_warning_count', 0)}",
            ]
        )
    reference_note = ""
    if reference_brief:
        reference_note = (
            " Reference-bounded scope: this idea is based only on the selected local reference "
            "materials and their local source passages; it does not establish novelty or scientific validity."
        )
    ideas = [
        _idea(
            1,
            chosen_topic,
            f"Evidence coverage map for {chosen_topic}",
            "The local source package may support a bounded synthesis if retrieved passages cover the core question.",
            ["evidence_inventory", "rag_retrieval_eval"],
            "Start by measuring whether local evidence is sufficient before drafting claims." + reference_note,
            feasibility_notes,
        ),
        _idea(
            2,
            chosen_topic,
            f"Claim robustness audit for {chosen_topic}",
            "Automatically drafted claims can be made safer by routing unsupported statements to limitations.",
            ["claim_audit_eval", "writing_safety_eval"],
            "This tests whether a draft can survive an internal reviewer-style evidence check." + reference_note,
            feasibility_notes,
        ),
        _idea(
            3,
            chosen_topic,
            f"Descriptive artifact profile for {chosen_topic}",
            "Local data and figure artifacts can support descriptive reporting only when provenance is present.",
            ["descriptive_data_profile", "evidence_inventory"],
            "This checks whether the project has enough local artifacts for Methods/Results sections." + reference_note,
            feasibility_notes,
        ),
    ][: max(1, min(max_ideas, 6))]
    if reference_brief:
        for idea in ideas:
            idea["reference_literature_ids"] = selected_reference_ids
            idea["reference_brief_file"] = REFERENCE_BRIEF_JSON
            idea["reference_coverage"] = reference_summary
            idea["limitations"] = [
                "Reference-based ideation is bounded to selected local reference materials.",
                "Placeholder or unapproved metadata remains a human-review warning.",
                "The idea does not claim novelty, scientific validity, peer review, or citation verification.",
            ]
    payload = {
        "schema_version": f"{SCHEMA_PREFIX}.ideas.v1",
        "project_id": project_id,
        "created_at": utc_now(),
        "topic": chosen_topic,
        "research_question": chosen_question,
        "mode": "safe_local_auto_scientist_mvp",
        "arbitrary_code_execution": False,
        "evidence_summary": evidence,
        "ideas": ideas,
        "limitations": SAFETY_LIMITATIONS,
    }
    if reference_brief:
        payload["reference_literature_ids"] = selected_reference_ids
        payload["reference_brief_file"] = REFERENCE_BRIEF_JSON
        payload["reference_brief_markdown_file"] = REFERENCE_BRIEF_MD
        payload["reference_brief"] = {
            "summary": reference_summary,
            "warnings": reference_brief.get("warnings", []),
            "limitations": reference_brief.get("limitations", []),
        }
    write_project_json(project_dir, IDEAS_JSON, payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_auto_scientist_ideas",
        "Safe local Auto Scientist ideas were generated.",
        {
            "ideas_file": IDEAS_JSON,
            "idea_count": len(ideas),
            "arbitrary_code_execution": False,
            "reference_brief_file": REFERENCE_BRIEF_JSON if reference_brief else None,
            "reference_count": reference_summary.get("reference_count", 0) if reference_brief else 0,
        },
        source="api",
        event_category="agent",
        risk_level="medium",
        entity_type="auto_scientist",
        entity_id="ideas",
    )
    return payload
