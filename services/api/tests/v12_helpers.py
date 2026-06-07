from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_v12_project(project_dir: Path, entries: list[dict[str, Any]], source_text: str | None = None) -> Path:
    literature_dir = project_dir / "literature"
    literature_dir.mkdir(parents=True, exist_ok=True)
    if source_text is not None:
        (literature_dir / "source.md").write_text(source_text, encoding="utf-8")
    (literature_dir / "literature_index.json").write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return project_dir / "literature" / "literature_index.json"


def base_literature_entry(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "literature_id": "lit_001",
        "source_file": "literature/source.md",
        "title": "Adaptive Retrieval Improves Local Citation Grounding",
        "authors": ["Ada Lovelace", "Grace Hopper"],
        "year": 2026,
        "doi": None,
        "journal": "Journal of Local Methods",
        "source_type": "markdown",
        "parsed_text_file": "literature/source.md",
        "metadata_status": "placeholder",
        "human_verified": False,
    }
    entry.update(overrides)
    return entry
