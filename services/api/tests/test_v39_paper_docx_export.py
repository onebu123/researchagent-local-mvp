from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from main import app
from app.tools.paper_writer.docx_export import (
    AUTO_SCIENTIST_PAPER_DOCX,
    AUTO_SCIENTIST_PAPER_DOCX_MANIFEST,
    DRAFT_FULL_DOCX,
    DRAFT_FULL_DOCX_MANIFEST,
    export_auto_scientist_paper_docx,
    export_draft_docx,
)


def _write_markdown(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"# {title}",
                "",
                "> AI-generated draft from local project evidence. Requires human review before external use.",
                "",
                "## Abstract",
                "",
                "This draft summarizes local artifacts for reviewer inspection.",
                "",
                "## Limitations",
                "",
                "- This is not peer review, citation verification, scientific proof, or publication readiness.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _docx_text(path: Path) -> str:
    document = Document(path)
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _assert_export_manifest(payload: dict, project_dir: Path, docx_relative_path: str, manifest_relative_path: str) -> None:
    assert payload["is_draft_artifact"] is True
    assert payload["citation_proof"] is False
    assert payload["evidence_trust_package_citation_proof"] is False
    assert payload["docx_file"] == docx_relative_path
    assert payload["manifest_file"] == manifest_relative_path
    assert payload["artifact"]["relative_path"] == docx_relative_path
    assert payload["artifact"]["available"] is True
    assert isinstance(payload["artifact"]["sha256"], str)
    assert len(payload["artifact"]["sha256"]) == 64
    assert payload["safety"]["project_relative_paths_only"] is True
    assert str(project_dir) not in json.dumps(payload, ensure_ascii=False)


def test_paper_writer_docx_export_is_readable_and_manifested(demo_project_dir: Path) -> None:
    _write_markdown(demo_project_dir / "manuscript" / "draft_full.md", "Demo Paper Writer Draft")

    payload = export_draft_docx(demo_project_dir, "demo_project")

    docx_path = demo_project_dir / DRAFT_FULL_DOCX
    manifest_path = demo_project_dir / DRAFT_FULL_DOCX_MANIFEST
    assert docx_path.exists()
    assert manifest_path.exists()
    _assert_export_manifest(payload, demo_project_dir, DRAFT_FULL_DOCX, DRAFT_FULL_DOCX_MANIFEST)
    text = _docx_text(docx_path)
    assert "ResearchAgent Auto Paper Writer Draft" in text
    assert "human review" in text
    assert "not peer review" in text
    assert "citation verification" in text
    assert "scientific proof" in text
    assert "publication readiness" in text
    assert str(demo_project_dir) not in text


def test_auto_scientist_docx_export_api_contract(demo_project_dir: Path) -> None:
    _write_markdown(demo_project_dir / "manuscript" / "auto_scientist_paper.md", "Demo Auto Scientist Paper")

    client = TestClient(app)
    response = client.post("/api/projects/demo_project/auto-scientist/paper-export-docx", json={})

    assert response.status_code == 200, response.text
    payload = response.json()
    _assert_export_manifest(
        payload,
        demo_project_dir,
        AUTO_SCIENTIST_PAPER_DOCX,
        AUTO_SCIENTIST_PAPER_DOCX_MANIFEST,
    )
    text = _docx_text(demo_project_dir / AUTO_SCIENTIST_PAPER_DOCX)
    assert "ResearchAgent Auto Scientist Paper Draft" in text
    assert "human review" in text
    assert "not peer review" in text
    assert "citation proof" in text
    assert str(demo_project_dir) not in text


def test_paper_writer_docx_export_api_contract(demo_project_dir: Path) -> None:
    _write_markdown(demo_project_dir / "manuscript" / "draft_full.md", "Demo API Paper Writer Draft")

    client = TestClient(app)
    response = client.post("/api/projects/demo_project/paper-writer/export-docx", json={})

    assert response.status_code == 200, response.text
    payload = response.json()
    _assert_export_manifest(payload, demo_project_dir, DRAFT_FULL_DOCX, DRAFT_FULL_DOCX_MANIFEST)


def test_auto_scientist_docx_export_rejects_unsafe_source_path(demo_project_dir: Path) -> None:
    _write_markdown(demo_project_dir / "manuscript" / "auto_scientist_paper.md", "Demo Auto Scientist Paper")

    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/auto-scientist/paper-export-docx",
        json={"manuscript_relative_path": "../outside.md"},
    )

    assert response.status_code == 422


def test_auto_scientist_docx_export_function_accepts_project_relative_source(demo_project_dir: Path) -> None:
    _write_markdown(demo_project_dir / "manuscript" / "auto_scientist_paper.md", "Function Export")

    payload = export_auto_scientist_paper_docx(demo_project_dir, "demo_project")

    _assert_export_manifest(
        payload,
        demo_project_dir,
        AUTO_SCIENTIST_PAPER_DOCX,
        AUTO_SCIENTIST_PAPER_DOCX_MANIFEST,
    )
