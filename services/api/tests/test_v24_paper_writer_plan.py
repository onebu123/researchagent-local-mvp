from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.tools.paper_writer.paper_plan import generate_paper_plan, read_paper_plan
from app.tools.paper_writer.outline_builder import generate_paper_outline, read_paper_outline


def test_auto_paper_writer_generates_plan_from_local_evidence(demo_project_dir: Path) -> None:
    plan = generate_paper_plan(
        demo_project_dir,
        "demo_project",
        project_name="Demo Materials Project",
        domain="materials",
        paper_type="research_article",
        topic="efficiency and stability",
    )

    assert plan["schema_version"].endswith("paper_plan.v1")
    assert plan["paper_type"] == "research_article"
    assert plan["title_candidates"]
    assert plan["target_sections"]
    assert plan["available_evidence_summary"]["rag_chunk_count"] > 0
    assert "human-verified" in " ".join(plan["missing_evidence_warnings"]).lower()
    assert (demo_project_dir / "manuscript" / "paper_plan.json").exists()
    assert read_paper_plan(demo_project_dir)["project_id"] == "demo_project"


def test_auto_paper_writer_generates_outline_with_section_status(demo_project_dir: Path) -> None:
    generate_paper_plan(
        demo_project_dir,
        "demo_project",
        project_name="Demo Materials Project",
        domain="materials",
        topic="efficiency and stability",
    )
    outline = generate_paper_outline(
        demo_project_dir,
        "demo_project",
        project_name="Demo Materials Project",
        domain="materials",
    )

    assert outline["schema_version"].endswith("outline.v1")
    assert outline["sections"]
    assert outline["summary"]["section_count"] == len(outline["sections"])
    assert {"ready", "weak_evidence", "missing_evidence"}.intersection(
        {section["status"] for section in outline["sections"]}
    )
    assert (demo_project_dir / "manuscript" / "outline.json").exists()
    assert read_paper_outline(demo_project_dir)["project_id"] == "demo_project"


def test_auto_paper_writer_plan_api(demo_project_dir: Path) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/paper-writer/plan",
        json={"paper_type": "literature_review", "topic": "local evidence synthesis"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["paper_type"] == "literature_review"
    assert payload["topic"] == "local evidence synthesis"
    status = client.get("/api/projects/demo_project/paper-writer/status")
    assert status.status_code == 200
    assert status.json()["plan"]["available"] is True
