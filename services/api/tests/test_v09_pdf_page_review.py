from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def _first_pdf_page(client: TestClient) -> tuple[str, int]:
    report_response = client.get("/api/projects/demo_project/literature/pdf-quality-report")
    assert report_response.status_code == 200
    pdfs = report_response.json()["pdfs"]
    assert pdfs
    return pdfs[0]["source_file"], 1


def test_pdf_page_review_records_human_status_without_ocr(demo_project_dir: Path) -> None:
    client = TestClient(app)
    source_file, page_number = _first_pdf_page(client)

    response = client.post(
        "/api/projects/demo_project/literature/pdf-page-review",
        json={
            "source_file": source_file,
            "page_number": page_number,
            "human_status": "needs_manual_check",
            "reason": "page should be manually checked before citation use",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_file"] == source_file
    assert payload["page_number"] == page_number
    assert payload["ocr_attempted"] is False
    assert (demo_project_dir / "literature" / "pdf_page_reviews.jsonl").exists()
    assert (demo_project_dir / "literature" / "pdf_page_review_summary.json").exists()

    list_response = client.get("/api/projects/demo_project/literature/pdf-page-reviews")
    assert list_response.status_code == 200
    assert any(review["page_review_id"] == payload["page_review_id"] for review in list_response.json()["reviews"])


def test_pdf_page_review_failure_boundaries() -> None:
    client = TestClient(app)

    path_traversal = client.post(
        "/api/projects/demo_project/literature/pdf-page-review",
        json={
            "source_file": "../secret.pdf",
            "page_number": 1,
            "human_status": "needs_ocr",
            "reason": "invalid path",
        },
    )
    assert path_traversal.status_code == 422

    invalid_status = client.post(
        "/api/projects/demo_project/literature/pdf-page-review",
        json={
            "source_file": "literature/missing.pdf",
            "page_number": 1,
            "human_status": "ocr_done",
            "reason": "invalid status",
        },
    )
    assert invalid_status.status_code == 422

    missing_file = client.post(
        "/api/projects/demo_project/literature/pdf-page-review",
        json={
            "source_file": "literature/missing.pdf",
            "page_number": 1,
            "human_status": "needs_ocr",
            "reason": "missing file",
        },
    )
    assert missing_file.status_code == 404
