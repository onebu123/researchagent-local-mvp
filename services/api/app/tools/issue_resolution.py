from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json
from app.tools.manuscript_patch import load_patch, read_version_history


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def issue_resolution_path(project_dir: Path) -> Path:
    return project_dir / "reviews" / "issue_resolution.json"


def issue_resolution_reviews_path(project_dir: Path) -> Path:
    return project_dir / "reviews" / "issue_resolution_reviews.jsonl"


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


def read_issue_resolution_reviews(project_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(issue_resolution_reviews_path(project_dir))


def _sentence_issue_ids(project_dir: Path) -> list[str]:
    report = _read_json(project_dir / "reviews" / "review_report.json", {})
    issues = report.get("sentence_issues") if isinstance(report, dict) else None
    if not isinstance(issues, list):
        return []
    return [
        str(issue["issue_id"])
        for issue in issues
        if isinstance(issue, dict) and isinstance(issue.get("issue_id"), str)
    ]


def _patch_issue_maps(project_dir: Path, patch_id: str) -> tuple[dict[str, str], set[str]]:
    try:
        patch = load_patch(project_dir, patch_id)
    except (FileNotFoundError, ValueError):
        return {}, set()
    item_to_issue: dict[str, str] = {}
    applied_issue_ids: set[str] = set()
    for item in patch.get("items", []):
        if not isinstance(item, dict):
            continue
        item_id = item.get("patch_item_id")
        issue_id = item.get("issue_id")
        if isinstance(item_id, str) and isinstance(issue_id, str):
            item_to_issue[item_id] = issue_id
            if item.get("item_status") == "applied":
                applied_issue_ids.add(issue_id)
    return item_to_issue, applied_issue_ids


def _patch_maps(project_dir: Path, patch_ids: list[str]) -> tuple[dict[str, str], set[str]]:
    merged_item_to_issue: dict[str, str] = {}
    merged_applied: set[str] = set()
    for patch_id in patch_ids:
        item_to_issue, applied_from_patch = _patch_issue_maps(project_dir, patch_id)
        for item_id, issue_id in item_to_issue.items():
            merged_item_to_issue[f"{patch_id}:{item_id}"] = issue_id
            merged_item_to_issue.setdefault(item_id, issue_id)
        merged_applied.update(applied_from_patch)
    return merged_item_to_issue, merged_applied


def _source_patch_ids(version: dict[str, Any]) -> list[str]:
    patch_ids = [
        str(item)
        for item in version.get("source_patch_ids", [])
        if isinstance(item, str) and item
    ]
    patch_id = version.get("source_patch_id")
    if isinstance(patch_id, str) and patch_id:
        patch_ids.append(patch_id)
    return list(dict.fromkeys(patch_ids))


def _issue_id_from_ref(ref: Any, item_to_issue: dict[str, str]) -> str | None:
    if not isinstance(ref, dict):
        return None
    issue_id = ref.get("issue_id")
    if isinstance(issue_id, str) and issue_id:
        return issue_id
    patch_item_id = ref.get("patch_item_id")
    patch_id = ref.get("patch_id")
    if isinstance(patch_item_id, str) and patch_item_id:
        keyed = f"{patch_id}:{patch_item_id}" if isinstance(patch_id, str) and patch_id else patch_item_id
        return item_to_issue.get(keyed) or item_to_issue.get(patch_item_id)
    return None


def _human_review_payload(project_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    reviews = read_issue_resolution_reviews(project_dir)
    latest_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for review in reviews:
        issue_id = review.get("issue_id")
        version_id = review.get("version_id")
        if isinstance(issue_id, str) and isinstance(version_id, str):
            latest_by_key[(version_id, issue_id)] = review

    payload = dict(payload)
    versions: list[dict[str, Any]] = []
    latest_status_counts: dict[str, int] = {}
    for version in payload.get("versions", []):
        if not isinstance(version, dict):
            continue
        version_id = str(version.get("version_id") or "")
        version_reviews = [
            review
            for review in latest_by_key.values()
            if review.get("version_id") == version_id
        ]
        for review in version_reviews:
            status = str(review.get("human_status") or "unknown")
            latest_status_counts[status] = latest_status_counts.get(status, 0) + 1
        versions.append(
            {
                **version,
                "human_review_summary": {
                    "reviewed": len(version_reviews),
                    "resolved": sum(1 for item in version_reviews if item.get("human_status") == "resolved"),
                    "unresolved": sum(1 for item in version_reviews if item.get("human_status") == "unresolved"),
                    "needs_review": sum(1 for item in version_reviews if item.get("human_status") == "needs_review"),
                },
                "latest_human_reviews": sorted(
                    version_reviews,
                    key=lambda item: str(item.get("created_at") or ""),
                    reverse=True,
                ),
            }
        )
    payload["versions"] = versions
    payload["review_history"] = reviews
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    payload["summary"] = {
        **summary,
        "human_reviews": len(reviews),
        "latest_human_status_counts": latest_status_counts,
    }
    return payload


def generate_issue_resolution(project_dir: Path, project_id: str) -> dict[str, Any]:
    all_issue_ids = set(_sentence_issue_ids(project_dir))
    history = read_version_history(project_dir)
    version_records: list[dict[str, Any]] = []
    global_resolved: set[str] = set()
    global_partial: set[str] = set()

    for version in history["versions"]:
        patch_ids = _source_patch_ids(version)
        if not patch_ids:
            continue
        item_to_issue, applied_from_patch = _patch_maps(project_dir, patch_ids)
        summary = version.get("summary") if isinstance(version.get("summary"), dict) else {}
        applied_item_ids = {
            str(item)
            for item in summary.get("applied_item_ids", [])
            if isinstance(item, str) and item
        }
        applied_item_refs = [
            item for item in summary.get("applied_item_refs", []) if isinstance(item, dict)
        ]
        skipped_item_ids = {
            str(item.get("patch_item_id") or "")
            for item in summary.get("skipped_item_details", [])
            if isinstance(item, dict)
        }
        skipped_item_refs = [
            item for item in summary.get("skipped_item_details", []) if isinstance(item, dict)
        ]
        resolved_issue_ids = {
            item_to_issue[item_id]
            for item_id in applied_item_ids
            if item_id in item_to_issue
        } | {
            issue_id
            for issue_id in (_issue_id_from_ref(ref, item_to_issue) for ref in applied_item_refs)
            if issue_id
        } | applied_from_patch
        partially_resolved_issue_ids = {
            item_to_issue[item_id]
            for item_id in skipped_item_ids
            if item_id in item_to_issue and item_to_issue[item_id] not in resolved_issue_ids
        } | {
            issue_id
            for issue_id in (_issue_id_from_ref(ref, item_to_issue) for ref in skipped_item_refs)
            if issue_id and issue_id not in resolved_issue_ids
        }
        source_issue_ids = {
            str(item)
            for item in version.get("source_issue_ids", [])
            if isinstance(item, str) and item
        }
        unresolved_issue_ids = all_issue_ids - resolved_issue_ids - partially_resolved_issue_ids
        notes: list[str] = []
        if skipped_item_ids:
            notes.append("Skipped patch items are not treated as resolved.")
        if source_issue_ids - resolved_issue_ids - partially_resolved_issue_ids:
            notes.append("Some source issues have no applied patch item in this version.")
        if version.get("source_type") == "merge":
            notes.append("This version was generated from a confirmed patch merge.")
        global_resolved.update(resolved_issue_ids)
        global_partial.update(partially_resolved_issue_ids)
        version_records.append(
            {
                "version_id": version.get("version_id"),
                "source_type": version.get("source_type") or "patch",
                "source_merge_id": version.get("source_merge_id"),
                "source_patch_ids": patch_ids,
                "resolved_issue_ids": sorted(resolved_issue_ids),
                "unresolved_issue_ids": sorted(unresolved_issue_ids),
                "partially_resolved_issue_ids": sorted(partially_resolved_issue_ids),
                "notes": notes,
            }
        )

    global_unresolved = all_issue_ids - global_resolved - global_partial
    payload = {
        "generated_at": _utc_now(),
        "versions": version_records,
        "summary": {
            "total_sentence_issues": len(all_issue_ids),
            "resolved": len(global_resolved),
            "unresolved": len(global_unresolved),
            "partially_resolved": len(global_partial),
        },
        "notes": [
            "Issue resolution is based only on patch/version provenance, not semantic verification."
        ],
    }
    payload = _human_review_payload(project_dir, payload)
    write_json(issue_resolution_path(project_dir), payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_issue_resolution",
        "Reviewer issue resolution map was generated from provenance only.",
        {
            "versions": len(version_records),
            "resolved": payload["summary"]["resolved"],
            "unresolved": payload["summary"]["unresolved"],
            "partially_resolved": payload["summary"]["partially_resolved"],
        },
        source="api",
    )
    return payload


def load_or_generate_issue_resolution(project_dir: Path, project_id: str) -> dict[str, Any]:
    path = issue_resolution_path(project_dir)
    if path.exists():
        payload = _read_json(path, {})
        if isinstance(payload, dict):
            history_ids = [
                str(item.get("version_id"))
                for item in read_version_history(project_dir)["versions"]
                if item.get("version_id")
            ]
            payload_ids = [
                str(item.get("version_id"))
                for item in payload.get("versions", [])
                if isinstance(item, dict) and item.get("version_id")
            ]
            if history_ids == payload_ids:
                return _human_review_payload(project_dir, payload)
    return generate_issue_resolution(project_dir, project_id)


def _next_review_id(records: list[dict[str, Any]]) -> str:
    numbers: list[int] = []
    for record in records:
        value = str(record.get("review_id") or "")
        if value.startswith("issue_review_"):
            try:
                numbers.append(int(value.removeprefix("issue_review_")))
            except ValueError:
                continue
    return f"issue_review_{(max(numbers) + 1) if numbers else 1:04d}"


def _auto_status(payload: dict[str, Any], version_id: str, issue_id: str) -> str:
    for version in payload.get("versions", []):
        if not isinstance(version, dict) or version.get("version_id") != version_id:
            continue
        if issue_id in version.get("resolved_issue_ids", []):
            return "resolved"
        if issue_id in version.get("partially_resolved_issue_ids", []):
            return "partially_resolved"
        if issue_id in version.get("unresolved_issue_ids", []):
            return "unresolved"
    return "unknown"


def record_issue_resolution_review(
    project_dir: Path,
    project_id: str,
    issue_id: str,
    version_id: str,
    human_status: str,
    reason: str = "",
) -> dict[str, Any]:
    if human_status not in {"resolved", "unresolved", "needs_review"}:
        raise ValueError("human_status must be resolved, unresolved, or needs_review")
    if issue_id not in set(_sentence_issue_ids(project_dir)):
        raise FileNotFoundError(f"sentence issue does not exist: {issue_id}")
    history = read_version_history(project_dir)
    if not any(item.get("version_id") == version_id for item in history["versions"]):
        raise FileNotFoundError(f"manuscript version does not exist: {version_id}")

    current_resolution = load_or_generate_issue_resolution(project_dir, project_id)
    reviews_path = issue_resolution_reviews_path(project_dir)
    records = read_issue_resolution_reviews(project_dir)
    record = {
        "review_id": _next_review_id(records),
        "issue_id": issue_id,
        "version_id": version_id,
        "auto_status": _auto_status(current_resolution, version_id, issue_id),
        "human_status": human_status,
        "reason": reason,
        "created_at": _utc_now(),
        "source": "api",
    }
    ensure_dir(reviews_path.parent)
    with reviews_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    append_audit_event(
        project_dir,
        project_id,
        "record_issue_resolution_review",
        "Human review for sentence issue resolution was recorded without modifying manuscript.",
        {
            "review_id": record["review_id"],
            "issue_id": issue_id,
            "version_id": version_id,
            "human_status": human_status,
            "auto_status": record["auto_status"],
        },
        source="api",
    )
    return {"review": record, "issue_resolution": generate_issue_resolution(project_dir, project_id)}
