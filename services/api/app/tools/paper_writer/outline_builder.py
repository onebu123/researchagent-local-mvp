from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.paper_writer.citation_binder import (
    retrieve_section_passages,
    source_locator_summary,
    source_passage_ids,
    support_status_from_passages,
)
from app.tools.paper_writer.manuscript_contract import (
    SCHEMA_PREFIX,
    ensure_manuscript_dirs,
    read_json,
    utc_now,
    write_project_json,
)
from app.tools.paper_writer.paper_plan import generate_paper_plan, read_paper_plan

OUTLINE_JSON = "manuscript/outline.json"


def read_paper_outline(project_dir: Path) -> dict[str, Any]:
    payload = read_json(project_dir / OUTLINE_JSON, {})
    return payload if isinstance(payload, dict) else {}


def _claims_for_section(title: str, status: str) -> list[str]:
    if status == "missing_evidence":
        return [f"TODO: add local evidence before making a claim in {title}."]
    if title in {"Abstract", "Conclusion"}:
        return ["Summarize only local evidence-bound claims and visible limitations."]
    if title in {"Methods", "Method"}:
        return ["Describe project-local artifacts and provenance without inventing experiments."]
    if title in {"Results", "Findings", "Analysis Notes"}:
        return ["Report descriptive local analysis or source-passage support only."]
    return ["Synthesize retrieved local source passages with explicit uncertainty."]


def generate_paper_outline(
    project_dir: Path,
    project_id: str,
    project_name: str,
    domain: str,
    retrieval_mode: str = "local_hybrid_fts",
) -> dict[str, Any]:
    ensure_manuscript_dirs(project_dir)
    plan = read_paper_plan(project_dir)
    if not plan:
        plan = generate_paper_plan(
            project_dir,
            project_id,
            project_name=project_name,
            domain=domain,
            retrieval_mode=retrieval_mode,
        )
    topic = str(plan.get("topic") or project_name or domain or "local research project")
    sections: list[dict[str, Any]] = []
    for index, planned in enumerate(plan.get("target_sections", []), start=1):
        if not isinstance(planned, dict):
            continue
        title = str(planned.get("title") or f"Section {index}")
        passages = retrieve_section_passages(
            project_dir,
            project_id,
            f"{topic} {title} evidence support",
            top_k=5,
            retrieval_mode=retrieval_mode,
        )
        support_status = support_status_from_passages(passages)
        status = "ready" if support_status == "supported" else "weak_evidence" if passages else "missing_evidence"
        sections.append(
            {
                "section_id": planned.get("section_id") or title.lower().replace(" ", "_"),
                "order": index,
                "title": title,
                "purpose": planned.get("purpose") or "Write a cautious evidence-bound section.",
                "required_claims": _claims_for_section(title, status),
                "required_evidence_types": planned.get("required_evidence_types", ["source_passages"]),
                "source_passage_ids": source_passage_ids(passages),
                "source_locators": source_locator_summary(passages),
                "support_status": support_status,
                "status": status,
            }
        )
    payload = {
        "schema_version": f"{SCHEMA_PREFIX}.outline.v1",
        "project_id": project_id,
        "created_at": utc_now(),
        "outline_file": OUTLINE_JSON,
        "paper_plan_file": plan.get("paper_plan_file", "manuscript/paper_plan.json"),
        "paper_type": plan.get("paper_type", "research_article"),
        "topic": topic,
        "research_question": plan.get("research_question"),
        "sections": sections,
        "summary": {
            "section_count": len(sections),
            "ready": sum(1 for item in sections if item["status"] == "ready"),
            "weak_evidence": sum(1 for item in sections if item["status"] == "weak_evidence"),
            "missing_evidence": sum(1 for item in sections if item["status"] == "missing_evidence"),
        },
        "limitations": [
            "Outline status reflects local retrieval signals, not scientific truth.",
            "Missing-evidence sections must be drafted as limitations or TODOs.",
        ],
    }
    write_project_json(project_dir, OUTLINE_JSON, payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_auto_paper_outline",
        "Auto Paper Writer outline was generated from the evidence plan.",
        {
            "outline_file": OUTLINE_JSON,
            "section_count": len(sections),
            "missing_evidence": payload["summary"]["missing_evidence"],
        },
        source="api",
        event_category="manuscript",
        risk_level="medium" if payload["summary"]["missing_evidence"] else "low",
        entity_type="manuscript",
        entity_id="paper_outline",
    )
    return payload
