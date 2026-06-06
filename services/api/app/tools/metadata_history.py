from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.file_tools import ensure_dir


def metadata_history_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "metadata_history.jsonl"


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


def append_metadata_history(
    project_dir: Path,
    literature_id: str,
    changed_fields: list[str],
    old_values: dict[str, Any],
    new_values: dict[str, Any],
    source: str = "api",
    reason: str = "manual metadata update",
) -> dict[str, Any]:
    path = metadata_history_path(project_dir)
    records = _read_jsonl(path)
    record = {
        "history_id": f"lit_hist_{len(records) + 1:04d}",
        "literature_id": literature_id,
        "changed_fields": changed_fields,
        "old_values": old_values,
        "new_values": new_values,
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "reason": reason,
    }
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_metadata_history(
    project_dir: Path,
    literature_id: str | None = None,
) -> list[dict[str, Any]]:
    records = _read_jsonl(metadata_history_path(project_dir))
    if literature_id is None:
        return records
    return [record for record in records if record.get("literature_id") == literature_id]
