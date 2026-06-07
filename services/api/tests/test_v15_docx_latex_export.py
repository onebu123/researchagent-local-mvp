from __future__ import annotations

import json
from pathlib import Path

from docx import Document

from app.tools.workspace_export import build_workspace_export


def test_workspace_docx_is_readable_and_contains_caveats(demo_project_dir: Path) -> None:
    build_workspace_export(demo_project_dir, "demo_project")
    docx_path = demo_project_dir / "exports" / "workspace" / "research_workspace_export.docx"

    document = Document(docx_path)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert "ResearchAgent Workspace Export" in text
    assert "Project ID: demo_project" in text
    assert "not a production compliance archive" in text
    assert "peer review certificate" in text
    assert "scientific validation" in text


def test_workspace_latex_escapes_text_and_uses_approved_references_only(
    demo_project_dir: Path,
) -> None:
    build_workspace_export(demo_project_dir, "demo_project")
    latex_path = demo_project_dir / "exports" / "workspace" / "research_workspace_export.tex"
    latex = latex_path.read_text(encoding="utf-8")

    assert "\\documentclass" in latex
    assert "ResearchAgent Workspace Export" in latex
    assert "No approved verified references are available" in latex
    assert "Demo PDF Literature Placeholder" not in latex
    assert "No DOI" not in latex
    assert "demo\\_project" in latex


def test_workspace_trust_report_lists_relative_source_files(demo_project_dir: Path) -> None:
    build_workspace_export(demo_project_dir, "demo_project")
    trust_path = demo_project_dir / "exports" / "workspace" / "trust_report.json"
    payload = json.loads(trust_path.read_text(encoding="utf-8"))

    assert payload["relative_path"] == "exports/workspace/trust_report.json"
    assert payload["source_files"]["manuscript_draft"] == "manuscript/draft.md"
    assert payload["source_files"]["audit_log"] == "audit/audit_log.jsonl"
    assert str(demo_project_dir) not in json.dumps(payload, ensure_ascii=False)
