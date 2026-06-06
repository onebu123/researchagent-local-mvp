from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.manuscript_patch import read_version_history


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def version_lineage_path(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "versions" / "version_lineage.json"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _add_node(
    nodes: dict[str, dict[str, Any]],
    node_id: str,
    node_type: str,
    label: str,
    **extra: Any,
) -> None:
    if not node_id:
        return
    current = nodes.get(node_id, {})
    nodes[node_id] = {
        **current,
        "id": node_id,
        "type": node_type,
        "label": label,
        **{key: value for key, value in extra.items() if value is not None},
    }


def _add_edge(
    edges: list[dict[str, Any]],
    source: str | None,
    target: str | None,
    relation: str,
    **extra: Any,
) -> None:
    if not source or not target:
        return
    edge = {
        "source": source,
        "target": target,
        "relation": relation,
        **{key: value for key, value in extra.items() if value is not None},
    }
    if edge not in edges:
        edges.append(edge)


def _safe_relative(path: Path, project_dir: Path) -> str:
    try:
        return path.resolve().relative_to(project_dir.resolve()).as_posix()
    except ValueError:
        return path.name


def _merge_dir(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "patches" / "merges"


def _patch_dir(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "patches"


def _diff_dir(project_dir: Path) -> Path:
    return project_dir / "manuscript" / "diffs"


def _source_node_for_base_file(base_file: str | None) -> str:
    if not base_file:
        return "draft"
    if base_file == "manuscript/draft.md":
        return "draft"
    if base_file.startswith("manuscript/versions/") and base_file.endswith(".md"):
        return Path(base_file).stem
    return base_file


def generate_version_lineage(project_dir: Path, project_id: str) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    warnings: list[str] = []

    draft_path = project_dir / "manuscript" / "draft.md"
    _add_node(
        nodes,
        "draft",
        "manuscript",
        "draft.md",
        file="manuscript/draft.md",
        exists=draft_path.exists(),
    )

    for patch_path in sorted(_patch_dir(project_dir).glob("patch_*.json")):
        patch = _read_json(patch_path, {})
        if not isinstance(patch, dict):
            continue
        patch_id = str(patch.get("patch_id") or patch_path.stem)
        _add_node(
            nodes,
            patch_id,
            "patch",
            patch_id,
            file=_safe_relative(patch_path, project_dir),
            status=patch.get("status"),
            source=patch.get("source"),
            summary=patch.get("summary") if isinstance(patch.get("summary"), dict) else {},
        )
        _add_edge(
            edges,
            _source_node_for_base_file(str(patch.get("source_manuscript") or "manuscript/draft.md")),
            patch_id,
            "proposed_patch",
        )

    merge_by_version: dict[str, str] = {}
    for merge_path in sorted(_merge_dir(project_dir).glob("merge_*.json")):
        merge = _read_json(merge_path, {})
        if not isinstance(merge, dict):
            continue
        merge_id = str(merge.get("merge_id") or merge_path.stem)
        _add_node(
            nodes,
            merge_id,
            "merge",
            merge_id,
            file=_safe_relative(merge_path, project_dir),
            status=merge.get("status"),
            can_apply=merge.get("can_apply"),
            generated_version_id=merge.get("generated_version_id"),
            generated_diff_id=merge.get("generated_diff_id"),
            summary=merge.get("summary") if isinstance(merge.get("summary"), dict) else {},
        )
        for patch_id in merge.get("patch_ids", []):
            if isinstance(patch_id, str) and patch_id:
                _add_node(nodes, patch_id, "patch", patch_id)
                _add_edge(edges, patch_id, merge_id, "included_in_merge")
        version_id = merge.get("generated_version_id")
        if isinstance(version_id, str) and version_id:
            merge_by_version[version_id] = merge_id
            _add_node(nodes, version_id, "version", version_id)
            _add_edge(edges, merge_id, version_id, "generated_version")
        diff_id = merge.get("generated_diff_id")
        if isinstance(diff_id, str) and diff_id:
            _add_node(nodes, diff_id, "diff", diff_id)
            _add_edge(edges, merge_id, diff_id, "generated_diff")

    history = read_version_history(project_dir)
    for version in history["versions"]:
        version_id = str(version.get("version_id") or "")
        if not version_id:
            continue
        _add_node(
            nodes,
            version_id,
            "version",
            version_id,
            file=version.get("file"),
            created_at=version.get("created_at"),
            status=version.get("status"),
            source_type=version.get("source_type") or "patch",
            summary=version.get("summary") if isinstance(version.get("summary"), dict) else {},
        )
        base_node = _source_node_for_base_file(str(version.get("base_file") or "manuscript/draft.md"))
        _add_edge(edges, base_node, version_id, "base_manuscript")
        source_merge_id = version.get("source_merge_id")
        if isinstance(source_merge_id, str) and source_merge_id:
            _add_node(nodes, source_merge_id, "merge", source_merge_id)
            _add_edge(edges, source_merge_id, version_id, "generated_version")
        elif version_id in merge_by_version:
            _add_edge(edges, merge_by_version[version_id], version_id, "generated_version")
        source_patch_id = version.get("source_patch_id")
        if isinstance(source_patch_id, str) and source_patch_id:
            _add_node(nodes, source_patch_id, "patch", source_patch_id)
            _add_edge(edges, source_patch_id, version_id, "generated_version")
        for patch_id in version.get("source_patch_ids", []):
            if isinstance(patch_id, str) and patch_id:
                _add_node(nodes, patch_id, "patch", patch_id)
                _add_edge(edges, patch_id, version_id, "contributed_to_version")

    for diff_path in sorted(_diff_dir(project_dir).glob("diff_*.json")):
        diff = _read_json(diff_path, {})
        if not isinstance(diff, dict):
            continue
        diff_id = str(diff.get("diff_id") or diff_path.stem)
        version_id = diff.get("version_id")
        _add_node(
            nodes,
            diff_id,
            "diff",
            diff_id,
            file=_safe_relative(diff_path, project_dir),
            preview_file=diff.get("preview_file"),
            version_id=version_id,
            summary=diff.get("summary") if isinstance(diff.get("summary"), dict) else {},
        )
        if isinstance(version_id, str) and version_id:
            _add_node(nodes, version_id, "version", version_id)
            _add_edge(edges, version_id, diff_id, "has_diff")

    issue_resolution_path = project_dir / "reviews" / "issue_resolution.json"
    if issue_resolution_path.exists():
        _add_node(
            nodes,
            "issue_resolution",
            "issue_resolution",
            "issue_resolution.json",
            file="reviews/issue_resolution.json",
        )
        for version in history["versions"]:
            version_id = version.get("version_id")
            if isinstance(version_id, str) and version_id:
                _add_edge(edges, version_id, "issue_resolution", "tracked_by_issue_resolution")

    if not history["versions"]:
        warnings.append("No generated manuscript versions were found.")

    node_list = sorted(nodes.values(), key=lambda item: (str(item.get("type")), str(item.get("id"))))
    payload = {
        "generated_at": _utc_now(),
        "relative_path": "manuscript/versions/version_lineage.json",
        "nodes": node_list,
        "edges": edges,
        "summary": {
            "nodes": len(node_list),
            "edges": len(edges),
            "versions": sum(1 for item in node_list if item.get("type") == "version"),
            "patches": sum(1 for item in node_list if item.get("type") == "patch"),
            "merges": sum(1 for item in node_list if item.get("type") == "merge"),
            "diffs": sum(1 for item in node_list if item.get("type") == "diff"),
        },
        "warnings": warnings,
    }
    write_json(version_lineage_path(project_dir), payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_version_lineage",
        "Manuscript version lineage graph was generated from local provenance files.",
        {
            "nodes": payload["summary"]["nodes"],
            "edges": payload["summary"]["edges"],
            "versions": payload["summary"]["versions"],
        },
        source="api",
    )
    return payload


def load_or_generate_version_lineage(project_dir: Path, project_id: str) -> dict[str, Any]:
    path = version_lineage_path(project_dir)
    if path.exists():
        payload = _read_json(path, {})
        if isinstance(payload, dict):
            return payload
    return generate_version_lineage(project_dir, project_id)
