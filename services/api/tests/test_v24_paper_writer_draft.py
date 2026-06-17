from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.tools.paper_writer.paper_plan import generate_paper_plan
from app.tools.paper_writer.outline_builder import generate_paper_outline
from app.tools.paper_writer.section_writer import generate_full_draft, read_full_draft_status
from app.tools.paper_writer.writer_eval import evaluate_auto_paper_draft

FORBIDDEN = ["statistically significant", "p-value", "causal", "proves", "proved"]


def test_auto_paper_writer_generates_auditable_full_draft(demo_project_dir: Path) -> None:
    generate_paper_plan(
        demo_project_dir,
        "demo_project",
        project_name="Demo Materials Project",
        domain="materials",
        topic="efficiency and stability",
    )
    generate_paper_outline(
        demo_project_dir,
        "demo_project",
        project_name="Demo Materials Project",
        domain="materials",
    )
    draft = generate_full_draft(
        demo_project_dir,
        "demo_project",
        project_name="Demo Materials Project",
        domain="materials",
    )

    draft_path = demo_project_dir / "manuscript" / "draft_full.md"
    audit_path = demo_project_dir / "manuscript" / "writing_audit.json"
    rounds_path = demo_project_dir / "manuscript" / "writing_rounds.jsonl"
    assert draft_path.exists()
    assert audit_path.exists()
    assert rounds_path.exists()
    content = draft_path.read_text(encoding="utf-8")
    assert "AI-generated draft" in content
    assert "Requires human review" in content
    lowered = content.lower()
    for term in FORBIDDEN:
        assert term not in lowered
    assert draft["writing_audit"]["human_review_required"] is True
    assert draft["sections"]
    assert draft["claim_audit"] is not None
    assert (demo_project_dir / "provenance" / "claim_audit.json").exists()


def test_auto_paper_writer_status_and_safety_eval(demo_project_dir: Path) -> None:
    generate_full_draft(
        demo_project_dir,
        "demo_project",
        project_name="Demo Materials Project",
        domain="materials",
    )
    status = read_full_draft_status(demo_project_dir)
    safety = evaluate_auto_paper_draft(demo_project_dir)

    assert status["available"] is True
    assert status["writing_audit"]["draft_file"] == "manuscript/draft_full.md"
    assert safety["has_ai_generated_notice"] is True
    assert safety["restricted_term_hits"] == []


def test_auto_paper_writer_draft_api_runs_offline(demo_project_dir: Path) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/paper-writer/draft",
        json={"retrieval_mode": "local_hybrid_fts", "run_claim_audit_after": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["draft_file"] == "manuscript/draft_full.md"
    assert payload["writing_audit"]["human_review_required"] is True
    assert payload["claim_audit"] is not None
