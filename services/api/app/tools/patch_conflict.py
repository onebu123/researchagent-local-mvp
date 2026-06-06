from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.manuscript_patch import load_patch, patches_dir


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_conflict_report_id(project_dir: Path) -> tuple[str, Path]:
    numbers: list[int] = []
    for path in patches_dir(project_dir).glob("conflict_report_*.json"):
        match = re.fullmatch(r"conflict_report_(\d+)\.json", path.name)
        if match:
            numbers.append(int(match.group(1)))
    number = (max(numbers) + 1) if numbers else 1
    return f"conflict_{number:03d}", patches_dir(project_dir) / f"conflict_report_{number:03d}.json"


def _item_ref(patch_id: str, item: dict[str, Any]) -> dict[str, Any]:
    safety = item.get("latest_safety_result") if isinstance(item.get("latest_safety_result"), dict) else {}
    return {
        "patch_id": patch_id,
        "patch_item_id": item.get("patch_item_id"),
        "issue_id": item.get("issue_id"),
        "section": item.get("section"),
        "paragraph_index": item.get("paragraph_index"),
        "sentence_index": item.get("sentence_index"),
        "related_claim_id": item.get("related_claim_id"),
        "before": item.get("before"),
        "safety_blocked_reasons": list(safety.get("blocked_reasons") or []),
    }


def _latest_safe(item: dict[str, Any]) -> bool:
    safety = item.get("latest_safety_result")
    if isinstance(safety, dict):
        return safety.get("safe") is True
    return item.get("item_status") in {"safe", "applied"}


def _add_conflict(
    conflicts: list[dict[str, Any]],
    conflict_type: str,
    severity: str,
    refs: list[dict[str, Any]],
    message: str,
) -> None:
    conflicts.append(
        {
            "conflict_id": f"conflict_item_{len(conflicts) + 1:03d}",
            "conflict_type": conflict_type,
            "severity": severity,
            "patch_item_refs": refs,
            "message": message,
            "resolution_required": severity == "major",
            "suggested_resolution": "Choose one patch item or manually edit before merging."
            if severity == "major"
            else "Review whether both patch items should remain in the same merge.",
        }
    )


def check_patch_conflicts(
    project_dir: Path,
    project_id: str,
    patch_ids: list[str],
    *,
    write_audit: bool = True,
) -> dict[str, Any]:
    if not patch_ids:
        raise ValueError("patch_ids must not be empty")
    ordered_patch_ids = list(dict.fromkeys(patch_ids))
    if len(ordered_patch_ids) != len(patch_ids):
        raise ValueError("patch_ids must be unique")

    patch_items: list[tuple[str, dict[str, Any]]] = []
    for patch_id in ordered_patch_ids:
        patch = load_patch(project_dir, patch_id)
        for item in patch.get("items", []):
            if isinstance(item, dict):
                patch_items.append((patch_id, item))

    conflicts: list[dict[str, Any]] = []
    warnings: list[str] = []

    for patch_id, item in patch_items:
        if not _latest_safe(item) or item.get("item_status") in {"blocked", "needs_revision", "skipped"}:
            _add_conflict(
                conflicts,
                "unsafe_item",
                "major",
                [_item_ref(patch_id, item)],
                "Patch item is not safe and cannot be merged automatically.",
            )

    for index, (left_patch_id, left) in enumerate(patch_items):
        for right_patch_id, right in patch_items[index + 1 :]:
            if (
                left_patch_id == right_patch_id
                and left.get("patch_item_id") == right.get("patch_item_id")
            ):
                continue
            refs = [_item_ref(left_patch_id, left), _item_ref(right_patch_id, right)]
            same_sentence = (
                left.get("section") == right.get("section")
                and left.get("paragraph_index") == right.get("paragraph_index")
                and left.get("sentence_index") == right.get("sentence_index")
                and left.get("section") is not None
                and left.get("paragraph_index") is not None
                and left.get("sentence_index") is not None
            )
            if same_sentence:
                _add_conflict(
                    conflicts,
                    "same_sentence",
                    "major",
                    refs,
                    "Two patch items modify the same sentence.",
                )
            if str(left.get("before") or "") and left.get("before") == right.get("before"):
                _add_conflict(
                    conflicts,
                    "same_before_text",
                    "major",
                    refs,
                    "Two patch items share the same before text.",
                )
            overlapping_location = (
                left.get("section") == right.get("section")
                and left.get("paragraph_index") == right.get("paragraph_index")
                and left.get("section") is not None
                and left.get("paragraph_index") is not None
                and left.get("sentence_index") != right.get("sentence_index")
            )
            if overlapping_location:
                _add_conflict(
                    conflicts,
                    "overlapping_location",
                    "minor",
                    refs,
                    "Two patch items modify different sentences in the same paragraph.",
                )
            left_claim = left.get("related_claim_id")
            if isinstance(left_claim, str) and left_claim and left_claim == right.get("related_claim_id"):
                _add_conflict(
                    conflicts,
                    "same_claim",
                    "minor",
                    refs,
                    "Two patch items are linked to the same claim.",
                )

    conflict_report_id, path = _next_conflict_report_id(project_dir)
    report = {
        "conflict_report_id": conflict_report_id,
        "patch_ids": ordered_patch_ids,
        "created_at": _utc_now(),
        "relative_path": f"manuscript/patches/{path.name}",
        "summary": {
            "total_patches": len(ordered_patch_ids),
            "total_items": len(patch_items),
            "conflicts": len(conflicts),
            "warnings": len(warnings),
            "major_conflicts": sum(1 for item in conflicts if item.get("severity") == "major"),
            "minor_conflicts": sum(1 for item in conflicts if item.get("severity") == "minor"),
        },
        "conflicts": conflicts,
        "warnings": warnings,
    }
    write_json(path, report)
    if write_audit:
        append_audit_event(
            project_dir,
            project_id,
            "check_patch_conflicts",
            "Patch conflict report was generated.",
            {
                "conflict_report_id": conflict_report_id,
                "patch_ids": ordered_patch_ids,
                "conflicts": len(conflicts),
                "major_conflicts": report["summary"]["major_conflicts"],
            },
            source="api",
        )
    return report
