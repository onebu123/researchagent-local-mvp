from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json, write_text
from app.tools.manuscript_diff import generate_manuscript_diff
from app.tools.manuscript_patch import (
    load_patch,
    patches_dir,
    read_version_history,
    version_history_path,
)
from app.tools.patch_conflict import check_patch_conflicts


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def merges_dir(project_dir: Path) -> Path:
    return patches_dir(project_dir) / "merges"


def _merge_path(project_dir: Path, merge_id: str) -> Path:
    return merges_dir(project_dir) / f"{_safe_merge_id(merge_id)}.json"


def _merge_preview_path(project_dir: Path, merge_id: str) -> Path:
    return merges_dir(project_dir) / f"{_safe_merge_id(merge_id)}.preview.md"


def _versions_dir(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "versions"


def _next_version_id(project_dir: Path) -> str:
    history = read_version_history(project_dir)
    numbers: list[int] = []
    for entry in history["versions"]:
        match = re.fullmatch(r"manuscript_v(\d+)", str(entry.get("version_id") or ""))
        if match:
            numbers.append(int(match.group(1)))
    return f"manuscript_v{(max(numbers) + 1) if numbers else 1:03d}"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _next_merge_id(project_dir: Path) -> tuple[str, Path, Path]:
    numbers: list[int] = []
    for path in merges_dir(project_dir).glob("merge_*.json"):
        match = re.fullmatch(r"merge_(\d+)\.json", path.name)
        if match:
            numbers.append(int(match.group(1)))
    number = (max(numbers) + 1) if numbers else 1
    merge_id = f"merge_{number:03d}"
    return merge_id, merges_dir(project_dir) / f"{merge_id}.json", merges_dir(project_dir) / f"{merge_id}.preview.md"


def _latest_safe(item: dict[str, Any]) -> bool:
    safety = item.get("latest_safety_result")
    if isinstance(safety, dict):
        return safety.get("safe") is True
    return item.get("item_status") in {"safe", "applied"}


def _extract_claim_ids(text: str) -> set[str]:
    return set(re.findall(r"\bclaim_\d{3,}\b", text))


def _build_preview(
    merge_id: str,
    patch_ids: list[str],
    can_apply: bool,
    preview_text: str,
    merge: dict[str, Any],
) -> str:
    lines = [
        "# Patch Merge Preview",
        "",
        f"Merge ID: {merge_id}",
        f"Patch IDs: {', '.join(patch_ids)}",
        f"Can apply: {str(can_apply).lower()}",
        "",
        "## Summary",
        "",
        json.dumps(merge["summary"], ensure_ascii=False, indent=2),
        "",
        "## Preview",
        "",
        preview_text,
        "",
    ]
    if merge["blocked_items"]:
        lines.extend(["## Blocked Items", ""])
        for item in merge["blocked_items"]:
            lines.append(
                f"- {item.get('patch_id')} / {item.get('patch_item_id')}: "
                f"{'; '.join(item.get('reasons') or [])}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_patch_merge_preview(
    project_dir: Path,
    project_id: str,
    patch_ids: list[str],
    source_manuscript: str = "manuscript/draft.md",
) -> dict[str, Any]:
    if not patch_ids:
        raise ValueError("patch_ids must not be empty")

    conflict_report = check_patch_conflicts(project_dir, project_id, patch_ids)
    major_conflicts = [
        item for item in conflict_report.get("conflicts", []) if item.get("severity") == "major"
    ]

    source_path = project_dir / source_manuscript
    if not source_path.exists():
        raise FileNotFoundError(f"source manuscript does not exist: {source_manuscript}")
    base_text = source_path.read_text(encoding="utf-8", errors="replace")
    preview_text = base_text
    safe_items: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []

    for patch_id in patch_ids:
        patch = load_patch(project_dir, patch_id)
        for item in patch.get("items", []):
            if not isinstance(item, dict):
                continue
            item_ref = {
                "patch_id": patch_id,
                "patch_item_id": item.get("patch_item_id"),
                "issue_id": item.get("issue_id"),
                "decision_id": item.get("decision_id"),
                "related_claim_id": item.get("related_claim_id"),
                "section": item.get("section"),
                "paragraph_index": item.get("paragraph_index"),
                "sentence_index": item.get("sentence_index"),
                "before": item.get("before"),
                "after": item.get("after"),
                "item_status": item.get("item_status"),
                "latest_safety_result": item.get("latest_safety_result"),
            }
            latest = item.get("latest_safety_result")
            if not _latest_safe(item) or item.get("item_status") in {"blocked", "needs_revision", "skipped"}:
                reasons = (
                    latest.get("blocked_reasons")
                    if isinstance(latest, dict)
                    else ["patch item is not safe"]
                )
                blocked_items.append({**item_ref, "reasons": reasons or ["patch item is not safe"]})
                continue
            before = str(item.get("before") or "")
            after = str(item.get("after") or "")
            if before not in preview_text:
                blocked_items.append({**item_ref, "reasons": ["before text not found in merge preview"]})
                continue
            preview_text = preview_text.replace(before, after, 1)
            safe_items.append(item_ref)

    can_apply = not major_conflicts and not blocked_items
    merge_id, json_path, preview_path = _next_merge_id(project_dir)
    merge = {
        "merge_id": merge_id,
        "patch_ids": list(dict.fromkeys(patch_ids)),
        "created_at": _utc_now(),
        "source_manuscript": source_manuscript,
        "status": "preview",
        "conflict_report_file": conflict_report["relative_path"],
        "preview_file": f"manuscript/patches/merges/{merge_id}.preview.md",
        "can_apply": can_apply,
        "confirmed_at": None,
        "rejected_at": None,
        "generated_version_id": None,
        "generated_diff_id": None,
        "confirmed_reason": None,
        "rejected_reason": None,
        "items": safe_items,
        "blocked_items": blocked_items,
        "summary": {
            "total_items": len(safe_items) + len(blocked_items),
            "safe_items": len(safe_items),
            "blocked_items": len(blocked_items),
            "conflicts": conflict_report["summary"]["conflicts"],
            "major_conflicts": len(major_conflicts),
            "requires_resolution": bool(major_conflicts or blocked_items),
        },
    }
    ensure_dir(json_path.parent)
    write_json(json_path, merge)
    write_text(preview_path, _build_preview(merge_id, patch_ids, can_apply, preview_text, merge))
    append_audit_event(
        project_dir,
        project_id,
        "generate_patch_merge_preview",
        "Patch merge preview was generated without modifying draft.md or creating a version.",
        {
            "merge_id": merge_id,
            "patch_ids": patch_ids,
            "can_apply": can_apply,
            "safe_items": len(safe_items),
            "blocked_items": len(blocked_items),
            "major_conflicts": len(major_conflicts),
        },
        source="api",
    )
    return merge


def load_merge_preview(project_dir: Path, merge_id: str) -> str:
    path = _merge_preview_path(project_dir, merge_id)
    if not path.exists():
        raise FileNotFoundError(f"merge preview does not exist: {merge_id}")
    return path.read_text(encoding="utf-8")


def load_patch_merge(project_dir: Path, merge_id: str) -> dict[str, Any]:
    path = _merge_path(project_dir, merge_id)
    if not path.exists():
        raise FileNotFoundError(f"merge preview does not exist: {merge_id}")
    payload = _read_json(path, {})
    if not isinstance(payload, dict):
        raise ValueError("merge JSON must be an object")
    return payload


def _write_merge(project_dir: Path, merge: dict[str, Any]) -> None:
    merge_id = str(merge.get("merge_id") or "")
    write_json(_merge_path(project_dir, merge_id), merge)


def _version_path(project_dir: Path, version_id: str) -> Path:
    return _versions_dir(project_dir) / f"{version_id}.md"


def _collect_merge_source_ids(merge: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    patch_ids = [str(item) for item in merge.get("patch_ids", []) if isinstance(item, str) and item]
    decision_ids: set[str] = set()
    issue_ids: set[str] = set()
    for item in merge.get("items", []):
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("decision_id"), str) and item.get("decision_id"):
            decision_ids.add(str(item["decision_id"]))
        if isinstance(item.get("issue_id"), str) and item.get("issue_id"):
            issue_ids.add(str(item["issue_id"]))
    return list(dict.fromkeys(patch_ids)), sorted(decision_ids), sorted(issue_ids)


def _apply_merge_items(base_text: str, merge: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    current_text = base_text
    applied_refs: list[dict[str, Any]] = []
    skipped_refs: list[dict[str, Any]] = []
    warnings: list[str] = []

    for item in merge.get("items", []):
        if not isinstance(item, dict):
            continue
        ref = {
            "patch_id": item.get("patch_id"),
            "patch_item_id": item.get("patch_item_id"),
            "issue_id": item.get("issue_id"),
            "decision_id": item.get("decision_id"),
        }
        before = str(item.get("before") or "")
        after = str(item.get("after") or "")
        if not before or before not in current_text:
            skipped_refs.append({**ref, "reasons": ["before text not found during merge confirm"]})
            continue
        current_text = current_text.replace(before, after, 1)
        applied_refs.append(ref)

    if "Evidence Checklist" not in current_text:
        warnings.append("Evidence Checklist is missing in generated merge version.")
    missing_claim_ids = sorted(_extract_claim_ids(base_text) - _extract_claim_ids(current_text))
    if missing_claim_ids:
        warnings.append(f"Generated merge version is missing claim_id values: {missing_claim_ids}")

    return current_text, {
        "applied_items": len(applied_refs),
        "applied_item_refs": applied_refs,
        "applied_item_ids": [
            str(item.get("patch_item_id"))
            for item in applied_refs
            if isinstance(item.get("patch_item_id"), str)
        ],
        "skipped_items": len(skipped_refs),
        "skipped_item_details": skipped_refs,
        "warnings": warnings,
    }


def confirm_patch_merge(
    project_dir: Path,
    project_id: str,
    merge_id: str,
    decision: str,
    reason: str = "",
) -> dict[str, Any]:
    if decision not in {"confirmed", "rejected"}:
        raise ValueError("decision must be confirmed or rejected")

    merge = load_patch_merge(project_dir, merge_id)
    if merge.get("status") != "preview":
        raise ValueError("only preview merge can be confirmed or rejected")

    now = _utc_now()
    version_record: dict[str, Any] | None = None
    diff_record: dict[str, Any] | None = None

    if decision == "rejected":
        merge["status"] = "rejected"
        merge["rejected_at"] = now
        merge["rejected_reason"] = reason
        _write_merge(project_dir, merge)
        append_audit_event(
            project_dir,
            project_id,
            "reject_patch_merge",
            "Patch merge preview rejection decision was recorded.",
            {"merge_id": merge_id, "reason": reason},
            source="api",
        )
        return {"merge": merge, "version": None, "diff": None}

    if merge.get("can_apply") is not True:
        raise ValueError("merge cannot be confirmed because conflicts or blocked items remain")

    source_manuscript = str(merge.get("source_manuscript") or "manuscript/draft.md")
    source_path = project_dir / source_manuscript
    if not source_path.exists():
        raise FileNotFoundError(f"source manuscript does not exist: {source_manuscript}")
    base_text = source_path.read_text(encoding="utf-8", errors="replace")
    version_text, summary = _apply_merge_items(base_text, merge)
    patch_ids, decision_ids, issue_ids = _collect_merge_source_ids(merge)

    version_id = _next_version_id(project_dir)
    version_file = _version_path(project_dir, version_id)
    write_text(version_file, version_text)
    version_record = {
        "version_id": version_id,
        "file": f"manuscript/versions/{version_id}.md",
        "base_file": source_manuscript,
        "created_at": now,
        "source_type": "merge",
        "source_patch_id": None,
        "source_merge_id": merge_id,
        "source_patch_ids": patch_ids,
        "source_decision_ids": decision_ids,
        "source_issue_ids": issue_ids,
        "status": "created",
        "summary": summary,
    }
    history = read_version_history(project_dir)
    history["versions"].append(version_record)
    write_json(version_history_path(project_dir), history)

    diff_record = generate_manuscript_diff(project_dir, project_id, source_manuscript, version_id)
    merge["status"] = "confirmed"
    merge["confirmed_at"] = now
    merge["confirmed_reason"] = reason
    merge["generated_version_id"] = version_id
    merge["generated_diff_id"] = diff_record.get("diff_id")
    merge["summary"] = {
        **merge.get("summary", {}),
        "applied_items": summary["applied_items"],
        "skipped_items": summary["skipped_items"],
        "version_warnings": summary["warnings"],
    }
    _write_merge(project_dir, merge)

    try:
        from app.tools.version_lineage import generate_version_lineage

        generate_version_lineage(project_dir, project_id)
    except Exception:
        pass

    append_audit_event(
        project_dir,
        project_id,
        "confirm_patch_merge",
        "Confirmed patch merge created a new manuscript version without overwriting draft.md.",
        {
            "merge_id": merge_id,
            "version_id": version_id,
            "diff_id": diff_record.get("diff_id"),
            "applied_items": summary["applied_items"],
            "skipped_items": summary["skipped_items"],
        },
        source="api",
    )
    return {"merge": merge, "version": version_record, "diff": diff_record}


def _safe_merge_id(merge_id: str) -> str:
    if not re.fullmatch(r"merge_\d{3,}", merge_id):
        raise ValueError("invalid merge_id")
    return merge_id
