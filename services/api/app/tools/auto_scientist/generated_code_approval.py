from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.auto_scientist.contracts import (
    GENERATED_CODE_APPROVALS_JSONL,
    SCHEMA_PREFIX,
    append_jsonl,
    read_jsonl,
    safe_id,
    utc_now,
)


def source_sha256(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def approval_id_for(run_id: str, experiment_id: str, source_hash: str) -> str:
    return "code_approval_" + hashlib.sha1(
        f"{run_id}:{experiment_id}:{source_hash}".encode("utf-8")
    ).hexdigest()[:16]


def record_generated_code_approval(
    project_dir: Path,
    project_id: str,
    run_id: str,
    experiment_id: str,
    decision: str,
    reason: str = "",
    source_hash: str | None = None,
    reviewer: str = "local_user",
) -> dict[str, Any]:
    cleaned_decision = decision.strip().lower()
    if cleaned_decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected")
    cleaned_run_id = safe_id(run_id)
    cleaned_experiment_id = safe_id(experiment_id)
    cleaned_source_hash = (source_hash or "unknown_source_hash").strip() or "unknown_source_hash"
    record = {
        "schema_version": f"{SCHEMA_PREFIX}.generated_code_approval.v1",
        "approval_id": approval_id_for(cleaned_run_id, cleaned_experiment_id, cleaned_source_hash),
        "project_id": project_id,
        "run_id": cleaned_run_id,
        "experiment_id": cleaned_experiment_id,
        "source_hash": cleaned_source_hash,
        "decision": cleaned_decision,
        "reason": reason.strip(),
        "reviewer": reviewer,
        "created_at": utc_now(),
        "human_review_required": True,
    }
    append_jsonl(project_dir, GENERATED_CODE_APPROVALS_JSONL, record)
    append_audit_event(
        project_dir,
        project_id,
        "record_generated_code_approval",
        "Generated experiment code approval decision was recorded locally.",
        {
            "run_id": cleaned_run_id,
            "experiment_id": cleaned_experiment_id,
            "source_hash": cleaned_source_hash,
            "decision": cleaned_decision,
            "approval_id": record["approval_id"],
        },
        source="api",
        event_category="agent",
        risk_level="medium",
        entity_type="auto_scientist_generated_code",
        entity_id=record["approval_id"],
    )
    return record


def read_generated_code_approvals(project_dir: Path) -> list[dict[str, Any]]:
    return read_jsonl(project_dir, GENERATED_CODE_APPROVALS_JSONL)


def generated_code_is_approved(
    project_dir: Path,
    run_id: str,
    experiment_id: str,
    source_hash: str,
) -> bool:
    cleaned_run_id = safe_id(run_id)
    cleaned_experiment_id = safe_id(experiment_id)
    for record in reversed(read_generated_code_approvals(project_dir)):
        if record.get("run_id") != cleaned_run_id:
            continue
        if record.get("experiment_id") != cleaned_experiment_id:
            continue
        if record.get("source_hash") != source_hash:
            continue
        decision = record.get("decision")
        if decision == "approved":
            return True
        if decision == "rejected":
            return False
    return False


def latest_generated_code_decision(
    project_dir: Path,
    run_id: str,
    experiment_id: str,
    source_hash: str,
) -> dict[str, Any] | None:
    cleaned_run_id = safe_id(run_id)
    cleaned_experiment_id = safe_id(experiment_id)
    for record in reversed(read_generated_code_approvals(project_dir)):
        if (
            record.get("run_id") == cleaned_run_id
            and record.get("experiment_id") == cleaned_experiment_id
            and record.get("source_hash") == source_hash
        ):
            return record
    return None

def list_generated_code_proposals(project_dir: Path, include_source_excerpt: bool = True) -> list[dict[str, Any]]:
    """Return generated-code proposal artifacts for UI review.

    Proposals are candidate experiment-code artifacts. Returning them through a
    dedicated reader lets the frontend show source hashes, static-scan results,
    approval state, and a bounded source excerpt without inferring paths from
    the generic Human Review Queue.
    """
    root = project_dir / "auto_scientist" / "generated_code"
    if not root.exists():
        return []
    approvals = read_generated_code_approvals(project_dir)

    def latest_decision_for(run_id: str, experiment_id: str, source_hash: str) -> dict[str, Any] | None:
        for record in reversed(approvals):
            if (
                record.get("run_id") == run_id
                and record.get("experiment_id") == experiment_id
                and record.get("source_hash") == source_hash
            ):
                return record
        return None

    proposals: list[dict[str, Any]] = []
    for proposal_path in sorted(root.glob("**/code_proposal.json")):
        try:
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(proposal, dict):
            continue
        relative_path = proposal_path.relative_to(project_dir).as_posix()
        run_id = str(proposal.get("run_id") or "")
        experiment_id = str(proposal.get("experiment_id") or "")
        source_hash = str(proposal.get("source_hash") or "")
        decision = latest_decision_for(run_id, experiment_id, source_hash)
        source_excerpt = ""
        source_file = proposal.get("source_file")
        if include_source_excerpt and isinstance(source_file, str):
            source_path = project_dir / source_file
            try:
                source_excerpt = source_path.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                source_excerpt = ""
        static_scan = proposal.get("static_scan") if isinstance(proposal.get("static_scan"), dict) else {}
        proposals.append(
            {
                "schema_version": f"{SCHEMA_PREFIX}.generated_code_proposal_summary.v1",
                "project_id": proposal.get("project_id"),
                "run_id": run_id,
                "experiment_id": experiment_id,
                "created_at": proposal.get("created_at"),
                "relative_path": relative_path,
                "source_file": proposal.get("source_file"),
                "input_file": proposal.get("input_file"),
                "source_hash": source_hash,
                "source_mode": proposal.get("source_mode"),
                "generated_code_strategy": proposal.get("generated_code_strategy"),
                "human_approval_recommended": bool(proposal.get("human_approval_recommended")),
                "static_scan": static_scan,
                "static_scan_safe": bool(static_scan.get("safe")) if isinstance(static_scan, dict) else False,
                "approval_decision": decision.get("decision") if decision else None,
                "approval_id": decision.get("approval_id") if decision else None,
                "approval_reason": decision.get("reason") if decision else None,
                "source_excerpt": source_excerpt,
                "safety_notes": proposal.get("safety_notes") if isinstance(proposal.get("safety_notes"), list) else [],
            }
        )
    return proposals



def rerun_generated_code_proposal(
    project_dir: Path,
    project_id: str,
    run_id: str,
    experiment_id: str,
    source_hash: str,
    *,
    sandbox_mode: str = "subprocess",
    docker_image: str | None = None,
    timeout_seconds: int = 5,
    max_memory_mb: int = 512,
) -> dict[str, Any]:
    """Rerun an approved generated-code proposal through the sandbox.

    This is the UI "rerun selected experiment" primitive. It never trusts the
    proposal blindly: the source hash must match a proposal artifact and the
    latest local approval for that exact hash must be approved before execution.
    """
    cleaned_run_id = safe_id(run_id)
    cleaned_experiment_id = safe_id(experiment_id)
    cleaned_source_hash = source_hash.strip()
    proposal = None
    for item in list_generated_code_proposals(project_dir, include_source_excerpt=False):
        if (
            item.get("run_id") == cleaned_run_id
            and item.get("experiment_id") == cleaned_experiment_id
            and item.get("source_hash") == cleaned_source_hash
        ):
            proposal = item
            break
    if proposal is None:
        raise FileNotFoundError("generated-code proposal not found for run_id/experiment_id/source_hash")
    decision = latest_generated_code_decision(project_dir, cleaned_run_id, cleaned_experiment_id, cleaned_source_hash)
    if not decision or decision.get("decision") != "approved":
        raise ValueError("generated-code proposal must be approved before rerun")
    source_file = proposal.get("source_file")
    if not isinstance(source_file, str):
        raise FileNotFoundError("proposal source_file missing")
    source_path = project_dir / source_file
    if not source_path.exists():
        raise FileNotFoundError(f"proposal source file missing: {source_file}")
    source = source_path.read_text(encoding="utf-8", errors="replace")
    actual_hash = source_sha256(source)
    if actual_hash != cleaned_source_hash:
        raise ValueError("proposal source hash no longer matches source_file")

    from app.tools.auto_scientist.generated_code_sandbox import run_generated_code_experiment

    result = run_generated_code_experiment(
        project_dir,
        project_id,
        cleaned_run_id,
        cleaned_experiment_id,
        {
            "generated_source": source,
            "generated_code_source_mode": "provided",
            "generated_code_requires_approval": True,
            "generated_code_timeout_seconds": timeout_seconds,
            "generated_code_max_memory_mb": max_memory_mb,
            "generated_code_sandbox_mode": sandbox_mode,
            **({"generated_code_docker_image": docker_image} if docker_image else {}),
        },
    )
    record = {
        "schema_version": f"{SCHEMA_PREFIX}.generated_code_rerun.v1",
        "project_id": project_id,
        "run_id": cleaned_run_id,
        "experiment_id": cleaned_experiment_id,
        "source_hash": cleaned_source_hash,
        "approval_id": decision.get("approval_id"),
        "created_at": utc_now(),
        "sandbox_mode": sandbox_mode,
        "status": result.get("status"),
        "sandbox": result.get("sandbox"),
        "metrics": result.get("metrics") if isinstance(result.get("metrics"), dict) else {},
        "limitations": [
            "Rerun executes an approved generated-code proposal through the local sandbox contract.",
            "A successful rerun is not scientific proof and still requires human review.",
        ],
    }
    append_jsonl(project_dir, "auto_scientist/generated_code_reruns.jsonl", record)
    append_audit_event(
        project_dir,
        project_id,
        "rerun_generated_code_proposal",
        "Approved generated-code proposal was rerun through the local sandbox.",
        {
            "run_id": cleaned_run_id,
            "experiment_id": cleaned_experiment_id,
            "source_hash": cleaned_source_hash,
            "status": result.get("status"),
            "sandbox_mode": sandbox_mode,
        },
        source="api",
        event_category="agent",
        risk_level="medium",
        entity_type="auto_scientist_generated_code",
        entity_id=cleaned_experiment_id,
    )
    return {"rerun": record, "result": result}
