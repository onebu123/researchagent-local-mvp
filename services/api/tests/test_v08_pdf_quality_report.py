from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_pdf_quality_report_contains_page_issue_categories(demo_project_dir: Path) -> None:
    client = TestClient(app)

    response = client.get("/api/projects/demo_project/literature/pdf-quality-report")

    assert response.status_code == 200
    report = response.json()
    assert (demo_project_dir / "literature" / "pdf_quality_report.json").exists()
    assert "summary" in report
    assert "pdfs" in report
    for record in report["pdfs"]:
        assert "low_quality_pages" in record
        assert "suspected_scanned_pages" in record
        assert "issue_categories" in record
        assert "ocr_not_configured" in record["issue_categories"]
        assert record["ocr_attempted"] is False
        assert (
            record["issue_categories"]["ocr_not_configured"] >= 0
            or any("OCR" in warning for warning in record.get("warnings", []))
        )

