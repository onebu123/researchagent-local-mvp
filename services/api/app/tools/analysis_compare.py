from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def comparisons_dir(project_dir: Path) -> Path:
    return project_dir / "analysis" / "comparisons"


def _safe_comparison_id(comparison_id: str) -> str:
    if not re.fullmatch(r"analysis_compare_\d{3,}", comparison_id):
        raise ValueError("invalid comparison_id")
    return comparison_id


def _next_comparison_id(project_dir: Path) -> tuple[str, Path]:
    numbers: list[int] = []
    for path in comparisons_dir(project_dir).glob("analysis_compare_*.json"):
        match = re.fullmatch(r"analysis_compare_(\d+)\.json", path.name)
        if match:
            numbers.append(int(match.group(1)))
    number = (max(numbers) + 1) if numbers else 1
    comparison_id = f"analysis_compare_{number:03d}"
    return comparison_id, comparisons_dir(project_dir) / f"{comparison_id}.json"


def _safe_analysis_file(value: str) -> str:
    cleaned = value.strip().replace("\\", "/")
    if not cleaned or cleaned.startswith("/") or ".." in cleaned.split("/"):
        raise ValueError("analysis provenance path must stay inside project")
    if not cleaned.startswith("analysis/") or not cleaned.endswith(".json"):
        raise ValueError("analysis provenance path must stay under analysis and end with .json")
    return cleaned


def _read_json_object(path: Path, relative_path: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"analysis provenance file does not exist: {relative_path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"analysis provenance file is invalid JSON: {relative_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"analysis provenance file must be an object: {relative_path}")
    return payload


def _dict_diff(base: dict[str, Any], target: dict[str, Any]) -> list[dict[str, Any]]:
    keys = sorted(set(base) | set(target))
    changes: list[dict[str, Any]] = []
    for key in keys:
        base_value = base.get(key)
        target_value = target.get(key)
        if base_value == target_value:
            continue
        if key not in base:
            change_type = "added"
        elif key not in target:
            change_type = "removed"
        else:
            change_type = "modified"
        changes.append(
            {
                "field": key,
                "base": base_value,
                "target": target_value,
                "change_type": change_type,
            }
        )
    return changes


def _list_diff(base: list[Any], target: list[Any]) -> list[dict[str, Any]]:
    removed = [item for item in base if item not in target]
    added = [item for item in target if item not in base]
    changes: list[dict[str, Any]] = []
    for item in removed:
        changes.append({"change_type": "removed", "base": item, "target": None})
    for item in added:
        changes.append({"change_type": "added", "base": None, "target": item})
    return changes


def generate_analysis_comparison(
    project_dir: Path,
    project_id: str,
    base_provenance: str,
    target_provenance: str,
) -> dict[str, Any]:
    safe_base = _safe_analysis_file(base_provenance)
    safe_target = _safe_analysis_file(target_provenance)
    base = _read_json_object(project_dir / safe_base, safe_base)
    target = _read_json_object(project_dir / safe_target, safe_target)

    parameter_diff = _dict_diff(
        base.get("parameters") if isinstance(base.get("parameters"), dict) else {},
        target.get("parameters") if isinstance(target.get("parameters"), dict) else {},
    )
    output_file_hashes = _dict_diff(
        base.get("output_file_hashes") if isinstance(base.get("output_file_hashes"), dict) else {},
        target.get("output_file_hashes") if isinstance(target.get("output_file_hashes"), dict) else {},
    )
    runtime_diff = _dict_diff(
        base.get("runtime") if isinstance(base.get("runtime"), dict) else {},
        target.get("runtime") if isinstance(target.get("runtime"), dict) else {},
    )
    warnings_diff = _list_diff(
        base.get("warnings") if isinstance(base.get("warnings"), list) else [],
        target.get("warnings") if isinstance(target.get("warnings"), list) else [],
    )
    limitations_diff = _list_diff(
        base.get("limitations") if isinstance(base.get("limitations"), list) else [],
        target.get("limitations") if isinstance(target.get("limitations"), list) else [],
    )
    base_input_hash = base.get("input_data_hash")
    target_input_hash = target.get("input_data_hash")
    comparison_id, path = _next_comparison_id(project_dir)
    payload = {
        "comparison_id": comparison_id,
        "base_provenance": safe_base,
        "target_provenance": safe_target,
        "created_at": _utc_now(),
        "relative_path": f"analysis/comparisons/{comparison_id}.json",
        "summary": {
            "parameters_changed": len(parameter_diff),
            "input_hash_changed": base_input_hash != target_input_hash,
            "output_hash_changes": len(output_file_hashes),
            "runtime_changes": len(runtime_diff),
            "warnings_changed": len(warnings_diff),
            "limitations_changed": len(limitations_diff),
        },
        "diffs": {
            "parameters": parameter_diff,
            "input_data_hash": {
                "base": base_input_hash,
                "target": target_input_hash,
                "changed": base_input_hash != target_input_hash,
            },
            "output_file_hashes": output_file_hashes,
            "runtime": runtime_diff,
            "warnings": warnings_diff,
            "limitations": limitations_diff,
        },
    }
    ensure_dir(path.parent)
    write_json(path, payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_analysis_comparison",
        "Analysis provenance comparison was generated from existing provenance files.",
        {
            "comparison_id": comparison_id,
            "base_provenance": safe_base,
            "target_provenance": safe_target,
        },
        source="api",
    )
    return payload


def list_analysis_comparisons(project_dir: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(comparisons_dir(project_dir).glob("analysis_compare_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("comparison_id"):
            result.append(payload)
    return result


def load_analysis_comparison(project_dir: Path, comparison_id: str) -> dict[str, Any]:
    safe_id = _safe_comparison_id(comparison_id)
    path = comparisons_dir(project_dir) / f"{safe_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"analysis comparison does not exist: {comparison_id}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("analysis comparison JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("analysis comparison JSON must be an object")
    return payload

