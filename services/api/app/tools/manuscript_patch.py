from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json, write_text
from app.tools.patch_safety import check_patch_item


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def patches_dir(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "patches"


def versions_dir(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "versions"


def version_history_path(project_dir: Path) -> Path:
    return versions_dir(project_dir) / "version_history.json"


def _safe_id(value: str, prefix: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError(f"invalid {prefix} id")
    if not value.startswith(prefix):
        raise ValueError(f"{prefix} id must start with {prefix}")
    return value


def _patch_path(project_dir: Path, patch_id: str) -> Path:
    safe_id = _safe_id(patch_id, "patch_")
    return patches_dir(project_dir) / f"{safe_id}.json"


def _preview_path(project_dir: Path, patch_id: str) -> Path:
    safe_id = _safe_id(patch_id, "patch_")
    return patches_dir(project_dir) / f"{safe_id}.preview.md"


def _version_path(project_dir: Path, version_id: str) -> Path:
    safe_id = _safe_id(version_id, "manuscript_v")
    return versions_dir(project_dir) / f"{safe_id}.md"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


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


def _normalize_safety_result(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "safe": bool(value.get("safe")),
            "warnings": list(value.get("warnings") or []),
            "blocked_reasons": list(value.get("blocked_reasons") or []),
        }
    return {"safe": True, "warnings": [], "blocked_reasons": []}


def _normalize_patch_item(
    item: dict[str, Any],
    *,
    item_status: str | None = None,
    blocked_reasons: list[str] | None = None,
) -> dict[str, Any]:
    normalized = dict(item)
    normalized["manual_edits"] = [
        edit for edit in normalized.get("manual_edits", []) if isinstance(edit, dict)
    ]
    if "latest_safety_result" not in normalized:
        reasons = list(blocked_reasons or normalized.get("blocked_reasons") or [])
        normalized["latest_safety_result"] = {
            "safe": not reasons,
            "warnings": list(normalized.get("warnings") or []),
            "blocked_reasons": reasons,
        }
    else:
        normalized["latest_safety_result"] = _normalize_safety_result(
            normalized["latest_safety_result"]
        )
    if "item_status" not in normalized:
        if item_status:
            normalized["item_status"] = item_status
        elif normalized["latest_safety_result"]["safe"]:
            normalized["item_status"] = "safe"
        else:
            normalized["item_status"] = "blocked"
    return normalized


def _normalize_patch(patch: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(patch)
    normalized["items"] = [
        _normalize_patch_item(item)
        for item in normalized.get("items", [])
        if isinstance(item, dict)
    ]
    normalized["blocked_items"] = [
        _normalize_patch_item(
            item,
            item_status=str(item.get("item_status") or "blocked"),
            blocked_reasons=list(item.get("blocked_reasons") or []),
        )
        for item in normalized.get("blocked_items", [])
        if isinstance(item, dict)
    ]
    normalized["summary"] = _patch_summary(normalized)
    return normalized


def _patch_summary(patch: dict[str, Any]) -> dict[str, Any]:
    current = patch.get("summary") if isinstance(patch.get("summary"), dict) else {}
    items = [item for item in patch.get("items", []) if isinstance(item, dict)]
    blocked_items = [item for item in patch.get("blocked_items", []) if isinstance(item, dict)]
    unsafe_items = [
        item
        for item in items
        if item.get("item_status") not in {"safe", "applied"}
        or _normalize_safety_result(item.get("latest_safety_result")).get("safe") is not True
    ]
    safe_items = [
        item
        for item in items
        if item.get("item_status") in {"safe", "applied"}
        and _normalize_safety_result(item.get("latest_safety_result")).get("safe") is True
    ]
    return {
        **current,
        "total_items": len(items),
        "safe_to_apply": bool(safe_items) and not unsafe_items and not blocked_items,
        "requires_human_confirmation": True,
        "blocked_items": len(blocked_items) + len(unsafe_items),
        "safe_items": len(safe_items),
    }


def _next_patch_id(project_dir: Path) -> str:
    numbers: list[int] = []
    for path in patches_dir(project_dir).glob("patch_*.json"):
        match = re.fullmatch(r"patch_(\d+)\.json", path.name)
        if match:
            numbers.append(int(match.group(1)))
    return f"patch_{(max(numbers) + 1) if numbers else 1:03d}"


def _next_version_id(project_dir: Path) -> str:
    history = read_version_history(project_dir)
    numbers: list[int] = []
    for entry in history["versions"]:
        version_id = str(entry.get("version_id") or "")
        match = re.fullmatch(r"manuscript_v(\d+)", version_id)
        if match:
            numbers.append(int(match.group(1)))
    return f"manuscript_v{(max(numbers) + 1) if numbers else 1:03d}"


def _issue_by_id(review: dict[str, Any]) -> dict[str, dict[str, Any]]:
    issues = review.get("sentence_issues")
    if not isinstance(issues, list):
        return {}
    return {
        str(issue["issue_id"]): issue
        for issue in issues
        if isinstance(issue, dict) and isinstance(issue.get("issue_id"), str)
    }


def _evidence_claim_ids(project_dir: Path) -> set[str]:
    payload = _read_json(project_dir / "provenance" / "evidence.json", [])
    if not isinstance(payload, list):
        return set()
    return {
        str(item["claim_id"])
        for item in payload
        if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
    }


def _extract_claim_ids(text: str) -> set[str]:
    return set(re.findall(r"\bclaim_\d{3,}\b", text))


def _build_preview(patch: dict[str, Any]) -> str:
    lines = [
        "# Manuscript Patch Preview",
        "",
        f"Patch ID: {patch['patch_id']}",
        f"Source manuscript: {patch['source_manuscript']}",
        f"Status: {patch['status']}",
        "",
    ]

    items = patch.get("items", [])
    if not items:
        lines.extend(["No safe patch items are currently available.", ""])
    for item in items:
        lines.extend(
            [
                f"## Patch Item {item['patch_item_id']}",
                "",
                f"Section: {item.get('section', '-')}",
                f"Issue: {item.get('issue_id', '-')}",
                f"Decision: {item.get('decision_id', '-')}",
                f"Related claim: {item.get('related_claim_id') or '-'}",
                f"Change type: {item.get('change_type', '-')}",
                f"Item status: {item.get('item_status', '-')}",
                "",
                "### Before",
                "",
                str(item.get("before", "")),
                "",
                "### After",
                "",
                str(item.get("after", "")),
                "",
            ]
        )
        warnings = item.get("warnings") or []
        if warnings:
            lines.extend(["### Warnings", ""])
            lines.extend(f"- {warning}" for warning in warnings)
            lines.append("")
        latest_safety = item.get("latest_safety_result")
        if isinstance(latest_safety, dict):
            lines.extend(
                [
                    "### Latest Safety Result",
                    "",
                    json.dumps(latest_safety, ensure_ascii=False, indent=2),
                    "",
                ]
            )

    blocked_items = patch.get("blocked_items") or []
    if blocked_items:
        lines.extend(["## Blocked Items", ""])
        for item in blocked_items:
            lines.append(
                f"- {item.get('patch_item_id', 'unknown')} / "
                f"{item.get('issue_id', 'unknown')}: {item.get('blocked_reasons', [])}"
            )
        lines.append("")

    lines.extend(["## Summary", "", json.dumps(patch.get("summary", {}), ensure_ascii=False, indent=2)])
    return "\n".join(lines).rstrip() + "\n"


def _write_patch_files(project_dir: Path, patch: dict[str, Any]) -> None:
    patch["summary"] = _patch_summary(patch)
    write_json(_patch_path(project_dir, patch["patch_id"]), patch)
    write_text(_preview_path(project_dir, patch["patch_id"]), _build_preview(patch))


def generate_manuscript_patch(
    project_dir: Path,
    project_id: str,
    source_manuscript: str = "manuscript/draft.md",
) -> dict[str, Any]:
    review = _read_json(project_dir / "reviews" / "review_report.json", {})
    if not isinstance(review, dict):
        raise ValueError("review_report.json must be an object")
    decisions = _read_jsonl(project_dir / "reviews" / "revision_decisions.jsonl")
    issues = _issue_by_id(review)
    claim_ids = _evidence_claim_ids(project_dir)
    patch_id = _next_patch_id(project_dir)

    items: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []
    latest_decisions: dict[str, dict[str, Any]] = {}
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        issue_id = decision.get("issue_id")
        if isinstance(issue_id, str) and issue_id:
            latest_decisions[issue_id] = decision
    accepted_decisions = [
        decision for decision in latest_decisions.values() if decision.get("decision") == "accepted"
    ]

    for decision in accepted_decisions:
        issue_id = str(decision.get("issue_id") or "")
        issue = issues.get(issue_id)
        diff = issue.get("revision_diff") if isinstance(issue, dict) else None
        if not isinstance(diff, dict):
            blocked_items.append(
                {
                    "patch_item_id": f"patch_item_{len(items) + len(blocked_items) + 1:03d}",
                    "issue_id": issue_id,
                    "decision_id": decision.get("decision_id"),
                    "blocked_reasons": ["revision_diff is missing"],
                }
            )
            continue

        warnings = list(diff.get("warnings") or [])
        if diff.get("requires_human_approval") is not True:
            warnings.append("revision_diff did not require approval; human confirmation is forced.")

        related_claim_id = (
            issue.get("related_claim_id")
            if isinstance(issue, dict) and isinstance(issue.get("related_claim_id"), str)
            else diff.get("preserved_claim_id")
        )
        item = {
            "patch_item_id": f"patch_item_{len(items) + len(blocked_items) + 1:03d}",
            "issue_id": issue_id,
            "decision_id": decision.get("decision_id"),
            "section": issue.get("section") if isinstance(issue, dict) else None,
            "paragraph_index": issue.get("paragraph_index") if isinstance(issue, dict) else None,
            "sentence_index": issue.get("sentence_index") if isinstance(issue, dict) else None,
            "before": diff.get("before") or decision.get("before") or "",
            "after": diff.get("after") or decision.get("after") or "",
            "change_type": diff.get("change_type") or "needs_human_rewrite",
            "related_claim_id": related_claim_id,
            "evidence_status": issue.get("evidence_status") if isinstance(issue, dict) else None,
            "requires_human_confirmation": True,
            "warnings": warnings,
        }
        safety = check_patch_item(project_dir, item, source_manuscript, claim_ids)
        item["warnings"] = [*item["warnings"], *safety["warnings"]]
        item["latest_safety_result"] = safety
        item["manual_edits"] = []
        if safety["safe"]:
            item["item_status"] = "safe"
            items.append(item)
        else:
            item["item_status"] = "blocked"
            blocked_items.append({**item, "blocked_reasons": safety["blocked_reasons"]})

    patch = {
        "patch_id": patch_id,
        "source_manuscript": source_manuscript,
        "base_version_id": "v0",
        "created_at": _utc_now(),
        "status": "proposed",
        "source": "accepted_revision_decision",
        "items": items,
        "blocked_items": blocked_items,
        "summary": {
            "total_items": len(items),
            "safe_to_apply": bool(items) and not blocked_items,
            "requires_human_confirmation": True,
            "blocked_items": len(blocked_items),
            "accepted_decisions": len(accepted_decisions),
        },
    }
    _write_patch_files(project_dir, patch)
    append_audit_event(
        project_dir,
        project_id,
        "generate_manuscript_patch",
        "Manuscript patch was generated without modifying draft.md.",
        {
            "patch_id": patch_id,
            "source_manuscript": source_manuscript,
            "total_items": len(items),
            "blocked_items": len(blocked_items),
        },
        source="api",
    )
    return patch


def list_patches(project_dir: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(patches_dir(project_dir).glob("patch_*.json")):
        payload = _read_json(path, {})
        if isinstance(payload, dict) and payload.get("patch_id"):
            result.append(_normalize_patch(payload))
    return result


def load_patch(project_dir: Path, patch_id: str) -> dict[str, Any]:
    path = _patch_path(project_dir, patch_id)
    if not path.exists():
        raise FileNotFoundError(f"patch does not exist: {patch_id}")
    payload = _read_json(path, {})
    if not isinstance(payload, dict):
        raise ValueError("patch JSON must be an object")
    return _normalize_patch(payload)


def _find_patch_item(patch: dict[str, Any], patch_item_id: str) -> dict[str, Any]:
    safe_item_id = _safe_id(patch_item_id, "patch_item_")
    for item in patch.get("items", []):
        if isinstance(item, dict) and item.get("patch_item_id") == safe_item_id:
            return item
    raise FileNotFoundError(f"patch item does not exist: {patch_item_id}")


def _next_patch_edit_id(item: dict[str, Any]) -> str:
    numbers: list[int] = []
    for edit in item.get("manual_edits", []):
        if not isinstance(edit, dict):
            continue
        match = re.fullmatch(r"patch_edit_(\d+)", str(edit.get("edit_id") or ""))
        if match:
            numbers.append(int(match.group(1)))
    return f"patch_edit_{(max(numbers) + 1) if numbers else 1:03d}"


def _status_from_safety(safety: dict[str, Any]) -> str:
    if safety.get("safe") is True:
        return "safe"
    if safety.get("blocked_reasons"):
        return "blocked"
    return "needs_revision"


def edit_patch_item(
    project_dir: Path,
    project_id: str,
    patch_id: str,
    patch_item_id: str,
    after: str,
    reason: str = "",
) -> dict[str, Any]:
    patch = load_patch(project_dir, patch_id)
    if patch.get("status") != "proposed":
        raise ValueError("only proposed patch items can be edited")
    item = _find_patch_item(patch, patch_item_id)
    old_after = str(item.get("after") or "")
    item["after"] = after
    source_manuscript = str(patch.get("source_manuscript") or "manuscript/draft.md")
    safety = check_patch_item(project_dir, item, source_manuscript, _evidence_claim_ids(project_dir))
    item["latest_safety_result"] = safety
    item["item_status"] = _status_from_safety(safety)
    item.setdefault("manual_edits", [])
    item["manual_edits"].append(
        {
            "edit_id": _next_patch_edit_id(item),
            "old_after": old_after,
            "new_after": after,
            "reason": reason,
            "created_at": _utc_now(),
            "safety_result": safety,
        }
    )
    item["warnings"] = list(dict.fromkeys([*list(item.get("warnings") or []), *safety["warnings"]]))
    _write_patch_files(project_dir, patch)
    append_audit_event(
        project_dir,
        project_id,
        "edit_patch_item",
        "Patch item after text was edited and safety was rerun.",
        {
            "patch_id": patch_id,
            "patch_item_id": patch_item_id,
            "item_status": item["item_status"],
            "safety_safe": safety["safe"],
        },
        source="api",
    )
    return patch


def rerun_patch_item_safety(
    project_dir: Path,
    project_id: str,
    patch_id: str,
    patch_item_id: str,
) -> dict[str, Any]:
    patch = load_patch(project_dir, patch_id)
    if patch.get("status") != "proposed":
        raise ValueError("only proposed patch items can be safety checked")
    item = _find_patch_item(patch, patch_item_id)
    source_manuscript = str(patch.get("source_manuscript") or "manuscript/draft.md")
    safety = check_patch_item(project_dir, item, source_manuscript, _evidence_claim_ids(project_dir))
    item["latest_safety_result"] = safety
    item["item_status"] = _status_from_safety(safety)
    item["warnings"] = list(dict.fromkeys([*list(item.get("warnings") or []), *safety["warnings"]]))
    _write_patch_files(project_dir, patch)
    append_audit_event(
        project_dir,
        project_id,
        "rerun_patch_item_safety",
        "Patch item safety checker was rerun.",
        {
            "patch_id": patch_id,
            "patch_item_id": patch_item_id,
            "item_status": item["item_status"],
            "safety_safe": safety["safe"],
        },
        source="api",
    )
    return {"patch": patch, "patch_item": item, "safety_result": safety}


def load_patch_preview(project_dir: Path, patch_id: str) -> str:
    path = _preview_path(project_dir, patch_id)
    if not path.exists():
        raise FileNotFoundError(f"patch preview does not exist: {patch_id}")
    return path.read_text(encoding="utf-8")


def read_version_history(project_dir: Path) -> dict[str, list[dict[str, Any]]]:
    payload = _read_json(version_history_path(project_dir), {"versions": []})
    if not isinstance(payload, dict) or not isinstance(payload.get("versions"), list):
        return {"versions": []}
    return {"versions": [item for item in payload["versions"] if isinstance(item, dict)]}


def _apply_items_to_text(
    base_text: str,
    patch: dict[str, Any],
    project_dir: Path,
) -> tuple[str, dict[str, Any]]:
    current_text = base_text
    applied_items: list[str] = []
    skipped_items: list[dict[str, Any]] = []
    warnings: list[str] = []
    source_manuscript = str(patch.get("source_manuscript") or "manuscript/draft.md")
    claim_ids = _evidence_claim_ids(project_dir)

    for item in patch.get("items", []):
        if not isinstance(item, dict):
            continue
        patch_item_id = str(item.get("patch_item_id") or "unknown")
        latest_safety = _normalize_safety_result(item.get("latest_safety_result"))
        if item.get("item_status") not in {"safe", "applied"} or latest_safety.get("safe") is False:
            skipped_items.append(
                {"patch_item_id": patch_item_id, "reasons": latest_safety["blocked_reasons"] or ["patch item is not safe"]}
            )
            continue
        safety = check_patch_item(project_dir, item, source_manuscript, claim_ids)
        if not safety["safe"]:
            skipped_items.append(
                {"patch_item_id": patch_item_id, "reasons": safety["blocked_reasons"]}
            )
            continue
        before = str(item.get("before") or "")
        after = str(item.get("after") or "")
        if before not in current_text:
            skipped_items.append(
                {"patch_item_id": patch_item_id, "reasons": ["before text not found during apply"]}
            )
            continue
        current_text = current_text.replace(before, after, 1)
        applied_items.append(patch_item_id)

    if "Evidence Checklist" not in current_text:
        warnings.append("Evidence Checklist is missing in generated version.")
    original_claim_ids = _extract_claim_ids(base_text)
    version_claim_ids = _extract_claim_ids(current_text)
    missing_claim_ids = sorted(original_claim_ids - version_claim_ids)
    if missing_claim_ids:
        warnings.append(f"Generated version is missing claim_id values: {missing_claim_ids}")

    return current_text, {
        "applied_items": len(applied_items),
        "applied_item_ids": applied_items,
        "skipped_items": len(skipped_items),
        "skipped_item_details": skipped_items,
        "warnings": warnings,
    }


def confirm_manuscript_patch(
    project_dir: Path,
    project_id: str,
    patch_id: str,
    decision: str,
    reason: str = "",
) -> dict[str, Any]:
    patch = load_patch(project_dir, patch_id)
    if patch.get("status") != "proposed":
        raise ValueError("only proposed patch can be confirmed or rejected")
    if decision not in {"confirmed", "rejected"}:
        raise ValueError("decision must be confirmed or rejected")

    now = _utc_now()
    patch["status"] = decision
    patch["confirmation"] = {
        "decision": decision,
        "reason": reason,
        "confirmed_at": now,
        "requires_human_confirmation": True,
    }

    version_record: dict[str, Any] | None = None
    if decision == "confirmed":
        source_manuscript = str(patch.get("source_manuscript") or "manuscript/draft.md")
        base_path = project_dir / source_manuscript
        if not base_path.exists():
            raise FileNotFoundError(f"source manuscript does not exist: {source_manuscript}")
        base_text = base_path.read_text(encoding="utf-8", errors="replace")
        version_text, summary = _apply_items_to_text(base_text, patch, project_dir)
        version_id = _next_version_id(project_dir)
        version_file = _version_path(project_dir, version_id)
        write_text(version_file, version_text)
        version_record = {
            "version_id": version_id,
            "file": f"manuscript/versions/{version_id}.md",
            "base_file": source_manuscript,
            "created_at": now,
            "source_patch_id": patch_id,
            "source_decision_ids": [
                item.get("decision_id") for item in patch.get("items", []) if isinstance(item, dict)
            ],
            "source_issue_ids": [
                item.get("issue_id") for item in patch.get("items", []) if isinstance(item, dict)
            ],
            "status": "created",
            "summary": summary,
        }
        history = read_version_history(project_dir)
        history["versions"].append(version_record)
        write_json(version_history_path(project_dir), history)
        patch["version_id"] = version_id
        applied_item_ids = set(summary["applied_item_ids"])
        skipped_item_ids = {
            str(item.get("patch_item_id") or "")
            for item in summary["skipped_item_details"]
            if isinstance(item, dict)
        }
        for item in patch.get("items", []):
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("patch_item_id") or "")
            if item_id in applied_item_ids:
                item["item_status"] = "applied"
            elif item_id in skipped_item_ids:
                item["item_status"] = "skipped"
        patch["summary"] = {
            **patch.get("summary", {}),
            "applied_items": summary["applied_items"],
            "skipped_items": summary["skipped_items"],
            "version_warnings": summary["warnings"],
        }
        append_audit_event(
            project_dir,
            project_id,
            "create_manuscript_version",
            "Confirmed manuscript patch created a new manuscript version without overwriting draft.md.",
            {
                "patch_id": patch_id,
                "version_id": version_id,
                "applied_items": summary["applied_items"],
                "skipped_items": summary["skipped_items"],
            },
            source="api",
        )
        try:
            from app.tools.version_lineage import generate_version_lineage

            generate_version_lineage(project_dir, project_id)
        except Exception:
            pass

    _write_patch_files(project_dir, patch)
    append_audit_event(
        project_dir,
        project_id,
        "confirm_manuscript_patch" if decision == "confirmed" else "reject_manuscript_patch",
        "Manuscript patch confirmation decision was recorded.",
        {
            "patch_id": patch_id,
            "decision": decision,
            "reason": reason,
            "version_id": patch.get("version_id"),
        },
        source="api",
    )
    return {"patch": patch, "version": version_record}


def load_version(project_dir: Path, version_id: str) -> dict[str, Any]:
    history = read_version_history(project_dir)
    record = next(
        (item for item in history["versions"] if item.get("version_id") == version_id),
        None,
    )
    if not record:
        raise FileNotFoundError(f"version does not exist: {version_id}")
    path = _version_path(project_dir, version_id)
    if not path.exists():
        raise FileNotFoundError(f"version file does not exist: {version_id}")
    return {"version": record, "content": path.read_text(encoding="utf-8")}
