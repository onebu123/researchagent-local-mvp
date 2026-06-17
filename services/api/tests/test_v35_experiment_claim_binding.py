from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.services.project_service import ProjectNotFoundError, project_service
from scripts.seed_demo import main as seed_demo
from app.tools.auto_scientist.experiment_claim_binding import (
    EXPERIMENT_CLAIM_BINDINGS_JSON,
    EXPERIMENT_CLAIM_BINDINGS_MD,
    LATEST_EXPERIMENT_CLAIM_BINDING_JSON,
    build_experiment_claim_bindings,
)
from app.tools.auto_scientist.scientist_loop import run_auto_scientist
from app.tools.evidence_trust_package import build_evidence_trust_package
from app.tools.human_review_queue import build_human_review_queue




def _ensure_demo_project_record() -> None:
    try:
        project_service.require_project("demo_project")
    except ProjectNotFoundError:
        seed_demo()


def _run_binding_workflow(project_dir: Path) -> dict:
    _ensure_demo_project_record()
    run_auto_scientist(
        "demo_project",
        topic="experiment claim binding",
        research_question="Can experiment outputs be traced into manuscript claims?",
        max_ideas=1,
        max_experiments_per_idea=1,
        write_paper=True,
        export_latex=True,
        allow_generated_code_experiments=False,
        enable_experiment_tree_search=True,
        experiment_tree_max_depth=1,
        experiment_tree_branching_factor=1,
    )
    payload = build_experiment_claim_bindings(project_dir, "demo_project")
    return payload


def test_experiment_claim_binding_artifacts_and_summary(demo_project_dir: Path) -> None:
    payload = _run_binding_workflow(demo_project_dir)

    assert payload["schema_version"].endswith(".experiment_claim_binding.v1")
    assert payload["manuscript_file"].startswith("manuscript/")
    assert payload["experiment_record_count"] >= 1
    assert payload["summary"]["claim_like_sentences"] >= 1
    assert payload["summary"]["bound"] + payload["summary"]["weak_binding"] + payload["summary"]["unbound"] >= 1
    assert payload["bindings"]

    first = payload["bindings"][0]
    assert "sentence" in first
    assert "binding_status" in first
    assert "claim_support_status" in first
    assert "evidence_artifacts" in first
    assert "human_review_required" in first

    assert (demo_project_dir / EXPERIMENT_CLAIM_BINDINGS_JSON).exists()
    assert (demo_project_dir / EXPERIMENT_CLAIM_BINDINGS_MD).exists()
    assert (demo_project_dir / LATEST_EXPERIMENT_CLAIM_BINDING_JSON).exists()


def test_experiment_claim_binding_api_queue_and_trust_package(demo_project_dir: Path) -> None:
    _run_binding_workflow(demo_project_dir)
    client = TestClient(app)

    get_response = client.get("/api/projects/demo_project/auto-scientist/experiment-claim-bindings")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["binding_file"] == EXPERIMENT_CLAIM_BINDINGS_JSON

    post_response = client.post(
        "/api/projects/demo_project/auto-scientist/experiment-claim-bindings",
        json={"top_k": 3},
    )
    assert post_response.status_code == 200, post_response.text
    assert post_response.json()["summary"]["claim_like_sentences"] >= 1

    queue = build_human_review_queue(demo_project_dir, "demo_project")
    review_ids = {item["review_id"] for item in queue["items"]}
    assert "auto_scientist_experiment_claim_binding_review" in review_ids

    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    paths = {item["relative_path"] for item in package["files"]}
    assert "auto_scientist/experiment_claim_bindings.json" in paths
    assert "auto_scientist/experiment_claim_bindings.md" in paths
    assert "auto_scientist/latest_experiment_claim_binding.json" in paths
