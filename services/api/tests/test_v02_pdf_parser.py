from __future__ import annotations

import json
from pathlib import Path

from app.tools.pdf_parser import parse_pdf


def test_pdf_parser_missing_file_returns_failed_metadata(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    pdf_path = project_dir / "literature" / "missing.pdf"

    metadata = parse_pdf(pdf_path, project_dir)

    assert metadata["parse_status"] == "failed"
    assert metadata["page_count"] == 0
    assert metadata["char_count"] == 0
    assert metadata["warnings"]
    parsed_text = project_dir / metadata["parsed_text_file"]
    metadata_file = project_dir / metadata["metadata_file"]
    assert parsed_text.exists()
    assert metadata_file.exists()
    assert json.loads(metadata_file.read_text(encoding="utf-8"))["parse_status"] == "failed"


def test_literature_index_contains_demo_literature(demo_project_dir: Path) -> None:
    index = json.loads(
        (demo_project_dir / "literature" / "literature_index.json").read_text(encoding="utf-8")
    )

    assert len(index) >= 2
    assert {entry["source_type"] for entry in index} >= {"markdown", "pdf"}
    assert all(entry["literature_id"].startswith("lit_") for entry in index)
    pdf_entry = next(entry for entry in index if entry["source_type"] == "pdf")
    assert pdf_entry["parsed_text_file"].endswith(".txt")
    assert pdf_entry["parse_status"] in {"success", "failed", "unsupported"}
