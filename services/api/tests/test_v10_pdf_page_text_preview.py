from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_pdf_page_text_preview_uses_existing_parsed_text_without_ocr(
    demo_project_dir: Path,
) -> None:
    client = TestClient(app)

    response = client.get("/api/projects/demo_project/literature/pdf-page-text-preview")

    assert response.status_code == 200
    payload = response.json()
    assert (demo_project_dir / "literature" / "pdf_page_text_previews.json").exists()
    assert payload["summary"]["ocr_attempted"] is False
    assert payload["pages"]
    first_page = payload["pages"][0]
    assert first_page["source_file"].startswith("literature/")
    assert first_page["page_number"] >= 1
    assert first_page["ocr_attempted"] is False
    assert "text_preview" in first_page

    filtered = client.get(
        "/api/projects/demo_project/literature/pdf-page-text-preview",
        params={"source_file": first_page["source_file"], "page_number": first_page["page_number"]},
    )
    assert filtered.status_code == 200
    assert len(filtered.json()["pages"]) == 1

    traversal = client.get(
        "/api/projects/demo_project/literature/pdf-page-text-preview",
        params={"source_file": "../secret.pdf"},
    )
    assert traversal.status_code == 400
