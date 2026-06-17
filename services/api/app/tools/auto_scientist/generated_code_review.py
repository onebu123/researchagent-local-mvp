from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.auto_scientist.contracts import CODE_REVIEW_ROUNDS_JSONL, SCHEMA_PREFIX, append_jsonl, read_jsonl, utc_now


def read_generated_code_review_rounds(project_dir: Path) -> list[dict[str, Any]]:
    return read_jsonl(project_dir, CODE_REVIEW_ROUNDS_JSONL)


def _payload(result_record: dict[str, Any]) -> dict[str, Any]:
    payload = result_record.get("result")
    return payload if isinstance(payload, dict) else result_record


def _static_findings(payload: dict[str, Any]) -> list[str]:
    sandbox = payload.get("sandbox") if isinstance(payload.get("sandbox"), dict) else {}
    scan = sandbox.get("static_scan") if isinstance(sandbox.get("static_scan"), dict) else {}
    findings = scan.get("findings") if isinstance(scan.get("findings"), list) else []
    return [str(item) for item in findings]


def _sandbox_runner(payload: dict[str, Any]) -> str:
    sandbox = payload.get("sandbox") if isinstance(payload.get("sandbox"), dict) else {}
    return str(sandbox.get("runner") or "unknown")


def review_generated_code_result(
    project_dir: Path,
    project_id: str,
    run_id: str,
    result_record: dict[str, Any],
    round_index: int = 1,
) -> dict[str, Any]:
    """Produce a bounded reviewer-style diagnosis for a generated-code result.

    This reviewer is a workflow diagnostic, not a proof of code correctness. It
    reads sandbox metadata, static scan findings, and status only; it does not
    trust or execute code.
    """
    payload = _payload(result_record)
    status = str(result_record.get("status") or payload.get("status") or "unknown")
    runner = _sandbox_runner(payload)
    findings = _static_findings(payload)
    failure_class = "unknown"
    recommended_revision_strategy = "deterministic_safe_diagnostic_fallback"
    retry_allowed = True
    severity = "warning"
    notes: list[str] = []

    if status == "pending_human_approval":
        failure_class = "approval_gate"
        recommended_revision_strategy = "await_human_approval_or_safe_fallback"
        notes.append("Generated source is waiting for a recorded local approval decision.")
    elif status == "rejected_by_human_approval":
        failure_class = "human_rejected_source"
        recommended_revision_strategy = "deterministic_safe_diagnostic_fallback"
        severity = "blocking"
        notes.append("A local reviewer rejected the generated source; only a safe fallback may be rerun.")
    elif status == "rejected_by_static_scan":
        failure_class = "static_scan_policy_violation"
        recommended_revision_strategy = "deterministic_safe_diagnostic_fallback"
        severity = "blocking"
        notes.extend(findings[:8])
    elif status == "docker_unavailable":
        failure_class = "sandbox_unavailable"
        recommended_revision_strategy = "switch_to_subprocess_safe_diagnostic"
        notes.append("Docker sandbox was unavailable or blocked by local image policy.")
    elif status == "timeout":
        failure_class = "timeout"
        recommended_revision_strategy = "shorter_deterministic_safe_diagnostic"
        severity = "blocking"
        notes.append("Sandbox execution timed out; retry with a short deterministic diagnostic.")
    elif status == "failed":
        failure_class = "execution_failed"
        recommended_revision_strategy = "deterministic_safe_diagnostic_fallback"
        severity = "blocking"
        notes.append("Sandbox execution failed or did not produce a result artifact.")
    elif status == "completed":
        failure_class = "no_revision_needed"
        recommended_revision_strategy = "none"
        retry_allowed = False
        severity = "info"
        notes.append("Generated-code experiment completed; no revision requested.")
    else:
        notes.append(f"Unhandled generated-code status: {status}")

    review = {
        "schema_version": f"{SCHEMA_PREFIX}.generated_code_review_round.v1",
        "project_id": project_id,
        "run_id": run_id,
        "round_index": round_index,
        "experiment_id": result_record.get("experiment_id"),
        "parent_status": status,
        "sandbox_runner": runner,
        "failure_class": failure_class,
        "severity": severity,
        "static_scan_findings": findings,
        "recommended_revision_strategy": recommended_revision_strategy,
        "retry_allowed": retry_allowed,
        "human_review_required": severity in {"blocking", "warning"},
        "notes": notes,
        "created_at": utc_now(),
    }
    append_jsonl(project_dir, CODE_REVIEW_ROUNDS_JSONL, review)
    return review
