from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event, read_audit_log, verify_audit_hash_chain
from app.tools.evidence_claim_review import generate_evidence_claim_review_summary
from app.tools.file_tools import write_json
from app.tools.literature_index import load_literature_index
from app.tools.metadata_review_workflow import generate_metadata_review_summary
from app.tools.pdf_page_review import generate_pdf_page_review_summary
from app.tools.reviewer_closure import generate_reviewer_closure_summary
from app.tools.revision_diff_review import generate_revision_diff_review_summary
from app.tools.run_history import read_run_history


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summary_path(project_dir: Path) -> Path:
    return project_dir / "trust" / "trust_summary.json"


def _safe_ratio(done: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(max(0.0, min(1.0, done / total)), 3)


def _placeholder_records(project_dir: Path) -> list[dict[str, Any]]:
    return [
        entry
        for entry in load_literature_index(project_dir)
        if isinstance(entry, dict)
        and (
            entry.get("metadata_status") == "placeholder"
            or entry.get("human_verified") is not True
        )
    ]


def _open_items(
    evidence_summary: dict[str, Any],
    closure_summary: dict[str, Any],
    placeholder_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    open_items: list[dict[str, Any]] = []
    blocking: list[dict[str, Any]] = []
    for claim in evidence_summary.get("claims", []):
        if not isinstance(claim, dict):
            continue
        status = claim.get("latest_human_status")
        if status in {"unsupported", "needs_more_evidence", None}:
            item = {
                "item_type": "evidence_claim",
                "item_id": claim.get("claim_id"),
                "status": status or "unreviewed",
                "message": "Evidence claim needs human trust review before export.",
            }
            open_items.append(item)
            if status == "unsupported":
                blocking.append(item)

    for issue in closure_summary.get("issues", []):
        if not isinstance(issue, dict):
            continue
        status = issue.get("closure_status")
        if status != "closed":
            open_items.append(
                {
                    "item_type": "reviewer_issue",
                    "item_id": issue.get("issue_id"),
                    "status": status,
                    "message": "Reviewer issue is not closed by accepted revision diff review.",
                }
            )

    for entry in placeholder_records:
        item = {
            "item_type": "literature_metadata",
            "item_id": entry.get("literature_id"),
            "status": entry.get("metadata_status"),
            "message": "Placeholder or unverified literature metadata prevents ready export.",
        }
        open_items.append(item)
        blocking.append(item)
    return open_items, blocking


def generate_trust_summary(project_dir: Path, project_id: str) -> dict[str, Any]:
    evidence_summary = generate_evidence_claim_review_summary(project_dir)
    revision_summary = generate_revision_diff_review_summary(project_dir)
    metadata_summary = generate_metadata_review_summary(project_dir)
    pdf_summary = generate_pdf_page_review_summary(project_dir)
    closure_summary = generate_reviewer_closure_summary(project_dir, project_id)
    audit_verify = verify_audit_hash_chain(project_dir)
    audit_entries = read_audit_log(project_dir, limit=0)
    run_history = read_run_history(project_dir)
    failed_runs = [
        run for run in run_history.get("runs", []) if isinstance(run, dict) and run.get("status") == "failed"
    ]
    placeholders = _placeholder_records(project_dir)
    open_items, blocking_issues = _open_items(evidence_summary, closure_summary, placeholders)

    evidence_counts = evidence_summary.get("summary", {})
    revision_counts = revision_summary.get("summary", {})
    metadata_counts = metadata_summary.get("summary", {})
    pdf_counts = pdf_summary.get("summary", {})
    closure_counts = closure_summary.get("summary", {})

    claim_completion = _safe_ratio(
        int(evidence_counts.get("reviewed") or 0),
        int(evidence_counts.get("total_claims") or 0),
    )
    revision_completion = _safe_ratio(
        int(revision_counts.get("reviewed") or 0),
        int(revision_counts.get("total_changes") or 0),
    )
    issue_closure = _safe_ratio(
        int(closure_counts.get("closed") or 0),
        int(closure_counts.get("total_sentence_issues") or 0),
    )
    audit_health = 1.0 if audit_verify.get("valid") is True else 0.0
    pdf_review_completion = _safe_ratio(
        int(pdf_counts.get("total_reviews") or 0),
        max(int(pdf_counts.get("total_reviews") or 0), 1),
    )

    if blocking_issues:
        overall_status = "needs_review"
    elif min(claim_completion, revision_completion or 1.0, issue_closure or 1.0, audit_health) >= 0.99:
        overall_status = "ready_for_local_export"
    elif evidence_counts.get("reviewed") or metadata_counts.get("total_actions") or pdf_counts.get("total_reviews"):
        overall_status = "partially_reviewed"
    else:
        overall_status = "draft"

    payload = {
        "generated_at": _utc_now(),
        "relative_path": "trust/trust_summary.json",
        "overall_status": overall_status,
        "scores": {
            "claim_review_completion": claim_completion,
            "revision_review_completion": revision_completion,
            "reviewer_issue_closure": issue_closure,
            "pdf_page_review_completion": pdf_review_completion,
            "audit_health": audit_health,
        },
        "counts": {
            "claims_total": int(evidence_counts.get("total_claims") or 0),
            "claims_reviewed": int(evidence_counts.get("reviewed") or 0),
            "claims_unsupported": int(evidence_counts.get("unsupported") or 0),
            "revision_changes_total": int(revision_counts.get("total_changes") or 0),
            "revision_changes_reviewed": int(revision_counts.get("reviewed") or 0),
            "metadata_actions_total": int(metadata_counts.get("total_actions") or 0),
            "pdf_pages_reviewed": len(pdf_summary.get("pages", [])),
            "reviewer_issues_total": int(closure_counts.get("total_sentence_issues") or 0),
            "reviewer_issues_open": int(closure_counts.get("total_sentence_issues") or 0)
            - int(closure_counts.get("closed") or 0),
            "audit_entries": len(audit_entries),
            "failed_runs": len(failed_runs),
            "placeholder_literature_records": len(placeholders),
        },
        "audit_hash_chain": audit_verify,
        "failed_run_diagnostics": [
            {
                "run_id": run.get("run_id"),
                "failed_step": run.get("failure_diagnostics", {}).get("failed_step")
                if isinstance(run.get("failure_diagnostics"), dict)
                else run.get("step"),
                "likely_cause": run.get("failure_diagnostics", {}).get("likely_cause")
                if isinstance(run.get("failure_diagnostics"), dict)
                else None,
                "suggested_recovery": run.get("failure_diagnostics", {}).get("suggested_recovery")
                if isinstance(run.get("failure_diagnostics"), dict)
                else [],
                "is_fixture": run.get("is_fixture") is True,
            }
            for run in failed_runs
        ],
        "open_items": open_items,
        "blocking_issues": blocking_issues,
        "source_files": {
            "evidence_review_summary": evidence_summary.get("relative_path"),
            "revision_diff_review_summary": revision_summary.get("relative_path"),
            "metadata_review_summary": metadata_summary.get("relative_path"),
            "pdf_page_review_summary": pdf_summary.get("relative_path"),
            "reviewer_closure_summary": closure_summary.get("relative_path"),
            "audit_log": "audit/audit_log.jsonl",
            "run_history": "runs/run_history.json",
        },
        "notes": [
            "This dashboard summarizes local workflow trust signals only.",
            "It is not a production compliance, peer review, or scientific truth certificate.",
        ],
    }
    write_json(_summary_path(project_dir), payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_trust_summary",
        "Global trust summary was generated from local review and audit artifacts.",
        {
            "summary_file": "trust/trust_summary.json",
            "overall_status": overall_status,
            "blocking_issues": len(blocking_issues),
        },
        source="api",
        event_category="trust",
        risk_level="low" if not blocking_issues else "medium",
        entity_type="trust",
        entity_id="trust_summary",
    )
    return payload
