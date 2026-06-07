from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json
from app.tools.literature_index import literature_index_path, load_literature_index
from app.tools.metadata_history import append_metadata_history
from app.tools.reference_verification import (
    mark_verification_applied,
    read_reference_verification_results,
    summarize_reference_verification,
)

ReferenceApprovalDecision = Literal["approved", "rejected", "needs_manual_check"]
DECISIONS = {"approved", "rejected", "needs_manual_check"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def reference_approvals_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "reference_approvals.jsonl"


def reference_approval_summary_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "reference_approval_summary.json"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_reference_approvals(project_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(reference_approvals_path(project_dir))


def _find_verification(project_dir: Path, verification_id: str) -> dict[str, Any]:
    for result in read_reference_verification_results(project_dir):
        if result.get("verification_id") == verification_id:
            return result
    raise ValueError(f"verification_id not found: {verification_id}")


def _candidate_metadata(verification: dict[str, Any]) -> dict[str, Any]:
    candidate = verification.get("candidate")
    if not isinstance(candidate, dict):
        return {}
    metadata: dict[str, Any] = {}
    for field in ["title", "authors", "year", "doi", "journal"]:
        value = candidate.get(field)
        if value in (None, "", []):
            continue
        metadata[field] = value
    return metadata


def _apply_to_literature_index(
    project_dir: Path,
    project_id: str,
    verification: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    literature_id = str(verification.get("literature_id") or "")
    candidate_metadata = _candidate_metadata(verification)
    if not literature_id:
        raise ValueError("verification result has no literature_id")
    if not candidate_metadata:
        raise ValueError("approved verification has no candidate metadata to apply")

    entries = load_literature_index(project_dir)
    for index, entry in enumerate(entries):
        if entry.get("literature_id") != literature_id:
            continue
        updated = dict(entry)
        updated.update(candidate_metadata)
        updated["metadata_status"] = "verified"
        updated["human_verified"] = True
        updated["reference_verification_status"] = "approved"
        updated["reference_verification_id"] = verification.get("verification_id")
        changed_fields = [
            field for field, value in updated.items() if entry.get(field) != value
        ]
        entries[index] = updated
        write_json(literature_index_path(project_dir), entries)
        if changed_fields:
            append_metadata_history(
                project_dir,
                literature_id,
                changed_fields,
                {field: entry.get(field) for field in changed_fields},
                {field: updated.get(field) for field in changed_fields},
                source="api",
                reason=reason or "reference verification approved and applied",
            )
        mark_verification_applied(project_dir, str(verification.get("verification_id")))
        append_audit_event(
            project_dir,
            project_id,
            "apply_reference_approval",
            "Approved reference candidate was applied to literature_index.json.",
            {
                "verification_id": verification.get("verification_id"),
                "literature_id": literature_id,
                "changed_fields": changed_fields,
                "literature_index_modified": True,
            },
            source="api",
            event_category="literature",
            risk_level="medium",
            entity_type="literature",
            entity_id=literature_id,
        )
        return updated
    raise ValueError(f"literature_id not found: {literature_id}")


def generate_reference_approval_summary(project_dir: Path) -> dict[str, Any]:
    approvals = read_reference_approvals(project_dir)
    summary = {
        "total_records": len(approvals),
        "approved": 0,
        "rejected": 0,
        "needs_manual_check": 0,
        "applied_to_literature_index": 0,
    }
    latest_by_literature: dict[str, dict[str, Any]] = {}
    for approval in approvals:
        decision = str(approval.get("decision") or "")
        if decision in summary:
            summary[decision] += 1
        if approval.get("applied_to_literature_index"):
            summary["applied_to_literature_index"] += 1
        literature_id = str(approval.get("literature_id") or "")
        if literature_id:
            latest_by_literature[literature_id] = approval
    payload = {
        "generated_at": _utc_now(),
        "relative_path": "literature/reference_approval_summary.json",
        "summary": summary,
        "latest_by_literature": latest_by_literature,
    }
    write_json(reference_approval_summary_path(project_dir), payload)
    summarize_reference_verification(project_dir)
    return payload


def read_reference_approval_summary(project_dir: Path) -> dict[str, Any]:
    path = reference_approval_summary_path(project_dir)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return generate_reference_approval_summary(project_dir)


def record_reference_approval(
    project_dir: Path,
    project_id: str,
    verification_id: str,
    decision: ReferenceApprovalDecision,
    reason: str = "",
    apply_to_literature_index: bool = False,
    source: str = "api",
) -> dict[str, Any]:
    if decision not in DECISIONS:
        raise ValueError(f"invalid reference approval decision: {decision}")
    if apply_to_literature_index and decision != "approved":
        raise ValueError("Only approved decisions can set apply_to_literature_index=true")
    verification = _find_verification(project_dir, verification_id)
    approved_metadata = _candidate_metadata(verification) if decision == "approved" else {}
    approvals = read_reference_approvals(project_dir)
    record = {
        "approval_id": f"ref_approval_{len(approvals) + 1:04d}",
        "verification_id": verification_id,
        "literature_id": verification.get("literature_id"),
        "decision": decision,
        "reason": reason.strip(),
        "approved_metadata": approved_metadata,
        "created_at": _utc_now(),
        "source": source,
        "apply_to_literature_index": apply_to_literature_index,
        "applied_to_literature_index": False,
    }
    applied_record: dict[str, Any] | None = None
    if apply_to_literature_index:
        applied_record = _apply_to_literature_index(project_dir, project_id, verification, reason)
        record["applied_to_literature_index"] = True

    _append_jsonl(reference_approvals_path(project_dir), record)
    summary = generate_reference_approval_summary(project_dir)
    append_audit_event(
        project_dir,
        project_id,
        "record_reference_approval",
        "Reference verification decision was recorded.",
        {
            "approval_id": record["approval_id"],
            "verification_id": verification_id,
            "literature_id": record["literature_id"],
            "decision": decision,
            "applied_to_literature_index": record["applied_to_literature_index"],
        },
        source=source,
        event_category="literature",
        risk_level="medium" if apply_to_literature_index else "low",
        entity_type="literature",
        entity_id=str(record["literature_id"]),
    )
    return {
        **record,
        "literature_index_modified": record["applied_to_literature_index"],
        "summary": summary,
        "applied_record": applied_record,
    }
