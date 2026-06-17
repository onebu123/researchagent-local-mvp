from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.auto_scientist.contracts import REVIEW_JSON, REVIEW_MD, SCHEMA_PREFIX, utc_now, write_project_json, write_project_text
from app.tools.claim_audit import read_claim_audit
from app.tools.paper_writer.writer_eval import evaluate_auto_paper_draft


def run_scientist_reviewer(
    project_dir: Path,
    project_id: str,
    run_id: str,
    analysis: dict[str, Any],
) -> dict[str, Any]:
    safety = evaluate_auto_paper_draft(project_dir)
    claim_audit = read_claim_audit(project_dir)
    summary = claim_audit.get("summary") if isinstance(claim_audit, dict) else {}
    unsupported = int((summary or {}).get("unsupported", 0) or 0)
    weak = int((summary or {}).get("weakly_supported", 0) or 0)
    restricted_hits = safety.get("restricted_term_hits") or []
    blocking_issues: list[str] = []
    warnings: list[str] = []
    if unsupported:
        blocking_issues.append(f"{unsupported} claim audit item(s) remain unsupported.")
    if restricted_hits:
        blocking_issues.append("Generated draft contains restricted assertion terms: " + ", ".join(restricted_hits))
    if weak:
        warnings.append(f"{weak} claim audit item(s) are weakly supported and require human review.")
    if not analysis.get("experiment_count"):
        blocking_issues.append("No experiment templates were executed.")
    if analysis.get("arbitrary_code_execution") is not False:
        blocking_issues.append("Auto Scientist run must explicitly record arbitrary_code_execution=false.")
    decision = "major_revision" if blocking_issues else "minor_revision" if warnings else "ready_for_human_review"
    payload = {
        "schema_version": f"{SCHEMA_PREFIX}.review.v1",
        "project_id": project_id,
        "run_id": run_id,
        "created_at": utc_now(),
        "review_file": REVIEW_JSON,
        "overall_decision": decision,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "recommended_revisions": [
            "Resolve unsupported claim audit items before external use.",
            "Keep all weakly supported findings in limitations unless additional evidence is provided.",
            "Do not present safe local template diagnostics as independent scientific proof.",
            "Have a human researcher verify references, experiments, figures, and final wording.",
        ],
        "reviewer_type": "simulated_auto_scientist_reviewer",
        "not_peer_review": True,
        "human_review_required": True,
    }
    write_project_json(project_dir, REVIEW_JSON, payload)
    lines = [
        "# Auto Scientist Reviewer Report",
        "",
        f"Overall decision: **{decision}**",
        "",
        "This is a simulated internal reviewer, not formal peer review.",
        "",
        "## Blocking Issues",
        "",
        *(f"- {item}" for item in blocking_issues or ["None."]),
        "",
        "## Warnings",
        "",
        *(f"- {item}" for item in warnings or ["None."]),
        "",
        "## Recommended Revisions",
        "",
        *(f"- {item}" for item in payload["recommended_revisions"]),
    ]
    write_project_text(project_dir, REVIEW_MD, "\n".join(lines) + "\n")
    return payload
