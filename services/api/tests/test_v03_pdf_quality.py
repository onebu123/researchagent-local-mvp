from __future__ import annotations

import json
from pathlib import Path

from app.services.workflow_service import workflow_service
from app.tools.pdf_parser import parse_pdf


def test_pdf_parser_missing_file_has_quality_failure(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    pdf_path = project_dir / "literature" / "missing.pdf"

    metadata = parse_pdf(pdf_path, project_dir)

    assert metadata["parse_status"] == "failed"
    assert metadata["quality_score"] == 0.0
    assert metadata["quality_label"] == "failed"
    assert metadata["needs_manual_review"] is True
    assert metadata["text_length"] == 0


def test_demo_pdf_metadata_contains_quality_fields(demo_project_dir: Path) -> None:
    metadata_files = list((demo_project_dir / "literature" / "parsed").glob("*.metadata.json"))
    assert metadata_files
    for metadata_file in metadata_files:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        for field in [
            "text_length",
            "empty_page_count",
            "extraction_method",
            "warning_count",
            "quality_score",
            "quality_label",
            "needs_manual_review",
        ]:
            assert field in metadata


def test_low_quality_pdf_enters_review_metadata_issue(demo_project_dir: Path) -> None:
    index_path = demo_project_dir / "literature" / "literature_index.json"
    original = index_path.read_text(encoding="utf-8")
    try:
        index = json.loads(original)
        for entry in index:
            if entry.get("source_type") == "pdf":
                entry["quality_label"] = "low"
                entry["quality_score"] = 0.2
                entry["needs_manual_review"] = True
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

        response = workflow_service.run_step("demo_project", "reviewer")
        assert response.workflow_status == "completed"
        report = json.loads(
            (demo_project_dir / "reviews" / "review_report.json").read_text(encoding="utf-8")
        )
        assert report["metadata_issues"]
        assert "PDF parse quality" in report["metadata_issues"][0]
    finally:
        index_path.write_text(original, encoding="utf-8")
        workflow_service.run_step("demo_project", "reviewer")
