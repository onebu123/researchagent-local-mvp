from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.tools.paper_writer.latex_export import export_draft_latex, read_latex_export_status
from app.tools.paper_writer.section_writer import generate_full_draft


def test_auto_paper_writer_exports_latex_source(demo_project_dir: Path) -> None:
    generate_full_draft(
        demo_project_dir,
        "demo_project",
        project_name="Demo Materials Project",
        domain="materials",
    )
    export = export_draft_latex(demo_project_dir, "demo_project")

    tex_path = demo_project_dir / "manuscript" / "draft_full.tex"
    assert tex_path.exists()
    content = tex_path.read_text(encoding="utf-8")
    assert "\\documentclass" in content
    assert "ResearchAgent Auto Paper Writer" in content
    assert "Verified references are not automatically generated" in content
    assert export["compiled_pdf"] is False
    assert read_latex_export_status(demo_project_dir)["available"] is True


def test_auto_paper_writer_latex_api(demo_project_dir: Path) -> None:
    generate_full_draft(
        demo_project_dir,
        "demo_project",
        project_name="Demo Materials Project",
        domain="materials",
    )
    client = TestClient(app)
    response = client.post("/api/projects/demo_project/paper-writer/export-latex", json={})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["latex_file"] == "manuscript/draft_full.tex"
    assert payload["compiled_pdf"] is False
