from __future__ import annotations

import json
from pathlib import Path


def test_pdf_metadata_contains_page_quality_and_ocr_placeholders(demo_project_dir: Path) -> None:
    metadata_path = demo_project_dir / "literature" / "parsed" / "demo_pdf_literature.metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert isinstance(metadata["pages"], list)
    assert metadata["pages"]
    assert metadata["empty_page_count"] == sum(1 for page in metadata["pages"] if page["empty"])

    for page in metadata["pages"]:
        assert page["page_number"] >= 1
        assert isinstance(page["char_count"], int)
        assert page["quality_signal"] in {"good", "medium", "low", "empty"}
        assert page["ocr"]["ocr_attempted"] is False
        assert page["ocr"]["ocr_engine"] is None
        assert page["ocr"]["ocr_status"] == "not_configured"
        assert page["ocr"]["ocr_text_file"] is None


def test_literature_index_exposes_pdf_page_quality(demo_project_dir: Path) -> None:
    literature_index = json.loads(
        (demo_project_dir / "literature" / "literature_index.json").read_text(encoding="utf-8")
    )
    pdf_entries = [entry for entry in literature_index if entry["source_type"] == "pdf"]

    assert pdf_entries
    for entry in pdf_entries:
        assert "page_count" in entry
        assert "empty_page_count" in entry
        assert isinstance(entry["pages"], list)
        assert entry["pages"]
