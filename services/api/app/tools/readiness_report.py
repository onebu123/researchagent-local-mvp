from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.trust_summary import generate_trust_summary


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _report_path(project_dir: Path) -> Path:
    return project_dir / "trust" / "v1_readiness_report.json"


def _exists(project_dir: Path, relative_path: str) -> bool:
    return (project_dir / relative_path).exists()


def generate_v1_readiness_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    trust = generate_trust_summary(project_dir, project_id)
    checks = {
        "evidence_claim_review_workflow": _exists(project_dir, "provenance/evidence_claim_review_summary.json"),
        "trust_summary": _exists(project_dir, "trust/trust_summary.json"),
        "reviewer_closure_summary": _exists(project_dir, "reviews/reviewer_closure_summary.json"),
        "metadata_revert_preview": bool(list((project_dir / "literature").glob("metadata_revert_preview_*.json"))),
        "pdf_page_text_preview": _exists(project_dir, "literature/pdf_page_text_previews.json"),
        "analysis_timeline": _exists(project_dir, "analysis/analysis_timeline.json"),
        "run_history_failure_fixture": any(
            run.get("is_fixture") is True
            for run in trust.get("failed_run_diagnostics", [])
            if isinstance(run, dict)
        ),
        "audit_hash_chain_valid": trust.get("audit_hash_chain", {}).get("valid") is True,
    }
    production_gaps = [
        "No authentication, authorization, role model, or multi-tenant isolation.",
        "No production database, backup, restore, migration, or queue infrastructure.",
        "No real DOI/reference verification service.",
        "No OCR execution or page-level OCR text generation.",
        "No real plagiarism, AI-detection, instrument integration, or public deployment hardening.",
        "Trust signals are local workflow records, not peer review or scientific validation.",
    ]
    blocking_gaps = [
        item.get("message")
        for item in trust.get("blocking_issues", [])
        if isinstance(item, dict) and isinstance(item.get("message"), str)
    ]
    readiness_level = (
        "local_mvp_ready"
        if checks["evidence_claim_review_workflow"]
        and checks["trust_summary"]
        and checks["audit_hash_chain_valid"]
        else "needs_local_review"
    )
    if blocking_gaps:
        readiness_level = "needs_local_review"

    payload = {
        "report_id": "v1_readiness_report",
        "generated_at": _utc_now(),
        "relative_path": "trust/v1_readiness_report.json",
        "readiness_level": readiness_level,
        "local_mvp_checks": checks,
        "trust_overall_status": trust.get("overall_status"),
        "blocking_gaps": list(dict.fromkeys(blocking_gaps)),
        "production_gaps": production_gaps,
        "recommended_next_steps": [
            "Resolve unsupported and unreviewed evidence claims.",
            "Close or explicitly defer reviewer issues with human rationale.",
            "Replace placeholder literature metadata with verified references before external use.",
            "Add authentication and production storage before any public deployment.",
        ],
        "notes": [
            "v1.0 readiness here means local MVP readiness only.",
            "This report must not be presented as production, compliance, or peer-review readiness.",
        ],
    }
    write_json(_report_path(project_dir), payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_v1_readiness_report",
        "v1.0 readiness report was generated from local trust summary and known production gaps.",
        {
            "report_file": "trust/v1_readiness_report.json",
            "readiness_level": readiness_level,
            "blocking_gaps": len(payload["blocking_gaps"]),
        },
        source="api",
        event_category="trust",
        risk_level="low" if not blocking_gaps else "medium",
        entity_type="readiness_report",
        entity_id="v1_readiness_report",
    )
    return payload
