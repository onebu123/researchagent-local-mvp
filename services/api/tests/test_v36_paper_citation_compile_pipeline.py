from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.services.project_service import ProjectNotFoundError, project_service
from scripts.seed_demo import main as seed_demo
from app.tools.auto_scientist.paper_citation_binding import (
    CITATION_BOUND_AUTOSCIENTIST_MD,
    LATEST_PAPER_CITATION_BINDING_JSON,
    PAPER_CITATION_BINDINGS_JSON,
    PAPER_CITATION_BINDINGS_MD,
    generate_paper_citation_bindings,
)
from app.tools.auto_scientist.paper_compile import (
    LATEX_COMPILE_REPORT_JSON,
    LATEX_COMPILE_REPORT_MD,
    PREVIEW_PDF_FILE,
    compile_auto_scientist_paper,
)
from app.tools.auto_scientist.scientist_loop import run_auto_scientist
from app.tools.evidence_trust_package import build_evidence_trust_package
from app.tools.human_review_queue import build_human_review_queue


def _ensure_demo_project_record() -> None:
    try:
        project_service.require_project("demo_project")
    except ProjectNotFoundError:
        seed_demo()


def _make_auto_scientist_paper(project_dir: Path) -> None:
    _ensure_demo_project_record()
    if (project_dir / "manuscript" / "auto_scientist_paper.md").exists() and (project_dir / "manuscript" / "auto_scientist_paper.tex").exists():
        return
    run_auto_scientist(
        "demo_project",
        topic="paper citation and compile pipeline",
        research_question="Can automatically generated manuscripts bind claims to citations and compile artifacts?",
        max_ideas=1,
        max_experiments_per_idea=1,
        write_paper=True,
        export_latex=True,
        allow_generated_code_experiments=False,
        enable_experiment_tree_search=False,
    )


def test_paper_citation_binding_artifacts_queue_and_trust_package(demo_project_dir: Path) -> None:
    _make_auto_scientist_paper(demo_project_dir)

    payload = generate_paper_citation_bindings(demo_project_dir, "demo_project", top_k=3)

    assert payload["schema_version"].endswith("paper_citation_binding.v1")
    assert payload["manuscript_file"].startswith("manuscript/")
    assert payload["summary"]["claim_like_sentences"] >= 1
    assert payload["summary"]["bound"] + payload["summary"]["weak_binding"] + payload["summary"]["unbound"] >= 1
    assert payload["bindings"]
    first_claim = next(item for item in payload["bindings"] if item["claim_like"])
    assert "citation_support_status" in first_claim
    assert "matched_source_passages" in first_claim
    assert "recommended_action" in first_claim

    assert (demo_project_dir / PAPER_CITATION_BINDINGS_JSON).exists()
    assert (demo_project_dir / PAPER_CITATION_BINDINGS_MD).exists()
    assert (demo_project_dir / LATEST_PAPER_CITATION_BINDING_JSON).exists()
    assert (demo_project_dir / CITATION_BOUND_AUTOSCIENTIST_MD).exists()

    queue = build_human_review_queue(demo_project_dir, "demo_project")
    review_ids = {item["review_id"] for item in queue["items"]}
    assert "auto_scientist_paper_citation_binding_review" in review_ids

    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    paths = {item["relative_path"] for item in package["files"]}
    assert "manuscript/paper_citation_bindings.json" in paths
    assert "manuscript/paper_citation_bindings.md" in paths
    assert "manuscript/auto_scientist_paper_citation_bound.md" in paths


def test_paper_compile_pipeline_preview_and_api_contract(demo_project_dir: Path) -> None:
    _make_auto_scientist_paper(demo_project_dir)

    report = compile_auto_scientist_paper(
        demo_project_dir,
        "demo_project",
        manuscript_tex_relative_path="manuscript/auto_scientist_paper.tex",
        engine="none",
        generate_preview_pdf=True,
    )

    assert report["schema_version"].endswith("paper_compile.v1")
    assert report["source_tex_file"] == "manuscript/auto_scientist_paper.tex"
    assert report["compile_status"] == "compile_skipped"
    assert report["compiled_pdf"] is False
    assert report["preview_pdf_generated"] is True
    assert report["preview_pdf_file"] == PREVIEW_PDF_FILE
    assert (demo_project_dir / LATEX_COMPILE_REPORT_JSON).exists()
    assert (demo_project_dir / LATEX_COMPILE_REPORT_MD).exists()
    assert (demo_project_dir / PREVIEW_PDF_FILE).read_bytes().startswith(b"%PDF-")

    queue = build_human_review_queue(demo_project_dir, "demo_project")
    review_ids = {item["review_id"] for item in queue["items"]}
    assert "auto_scientist_paper_compile_review" in review_ids

    client = TestClient(app)
    citation_response = client.post(
        "/api/projects/demo_project/auto-scientist/paper-citation-bindings",
        json={"top_k": 2},
    )
    assert citation_response.status_code == 200, citation_response.text
    assert citation_response.json()["binding_file"] == PAPER_CITATION_BINDINGS_JSON

    compile_response = client.post(
        "/api/projects/demo_project/auto-scientist/paper-compile",
        json={"manuscript_tex_relative_path": "manuscript/auto_scientist_paper.tex", "engine": "none", "generate_preview_pdf": True},
    )
    assert compile_response.status_code == 200, compile_response.text
    assert compile_response.json()["relative_path"] == LATEX_COMPILE_REPORT_JSON

    get_compile = client.get("/api/projects/demo_project/auto-scientist/paper-compile")
    assert get_compile.status_code == 200, get_compile.text
    assert get_compile.json()["preview_pdf_file"] == PREVIEW_PDF_FILE

    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    paths = {item["relative_path"] for item in package["files"]}
    assert "manuscript/latex_compile_report.json" in paths
    assert "manuscript/latex_compile_report.md" in paths
    assert PREVIEW_PDF_FILE in paths
