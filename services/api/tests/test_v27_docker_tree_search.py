from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.tools.auto_scientist.experiment_tree_search import score_experiment_result
from app.tools.auto_scientist.generated_code_sandbox import run_generated_code_experiment
from app.tools.auto_scientist.scientist_loop import run_auto_scientist, read_auto_scientist_status
from app.tools.human_review_queue import build_human_review_queue
from app.tools.evidence_trust_package import build_evidence_trust_package


def test_docker_sandbox_mode_gracefully_reports_unavailable_without_running_unsafe_code(
    demo_project_dir: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.tools.auto_scientist.generated_code_sandbox.shutil.which", lambda _name: None)

    result = run_generated_code_experiment(
        demo_project_dir,
        "demo_project",
        "docker_unavailable_run",
        "docker_exp_001",
        {
            "topic": "docker sandbox smoke test",
            "research_question": "Can docker mode fail safely?",
            "generated_code_sandbox_mode": "docker",
            "generated_code_docker_image": "python:3.11-slim",
            "generated_code_timeout_seconds": 5,
            "generated_code_max_memory_mb": 512,
        },
    )

    assert result["status"] == "docker_unavailable"
    assert result["generated_code_execution"] is True
    assert result["arbitrary_code_execution"] is False
    sandbox = result["sandbox"]
    assert sandbox["enabled"] is False
    assert sandbox["runner"] == "docker_network_none_unavailable"
    assert sandbox["network_disabled_by_policy"] is True
    assert sandbox["network_disabled_by_docker"] is False
    assert sandbox["docker_available"] is False
    assert all(not Path(path).is_absolute() for path in sandbox["output_files"])


def test_experiment_result_scoring_prefers_completed_supported_results() -> None:
    strong = {
        "status": "completed",
        "result": {
            "metrics": {"top_source_score": 0.82},
            "claims": [{"support_status": "supported"}],
        },
    }
    weak = {
        "status": "failed",
        "result": {
            "metrics": {"top_source_score": 0.1},
            "claims": [{"support_status": "unsupported"}],
        },
    }

    assert score_experiment_result(strong) > score_experiment_result(weak)


def test_auto_scientist_experiment_tree_search_writes_reviewable_artifacts(demo_project_dir: Path) -> None:
    payload = run_auto_scientist(
        "demo_project",
        topic="agentic local experiment search",
        max_ideas=1,
        max_experiments_per_idea=1,
        write_paper=False,
        export_latex=False,
        allow_generated_code_experiments=False,
        enable_experiment_tree_search=True,
        experiment_tree_max_depth=1,
        experiment_tree_branching_factor=2,
    )

    tree = payload["experiment_tree"]
    assert tree["tree_search_enabled"] is True
    assert tree["node_count"] >= 2
    assert tree["best_node"]
    assert tree["child_experiment_count"] >= 1
    assert (demo_project_dir / "auto_scientist" / "experiment_tree.json").exists()
    assert (demo_project_dir / "auto_scientist" / "experiment_tree.md").exists()
    assert payload["run"]["experiment_tree_search_enabled"] is True
    assert payload["run"]["experiment_tree_file"] == "auto_scientist/experiment_tree.json"

    queue = build_human_review_queue(demo_project_dir, "demo_project")
    review_ids = {item["review_id"] for item in queue["items"]}
    assert "auto_scientist_experiment_tree_review" in review_ids

    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    package_paths = {str(item["relative_path"]) for item in package["files"]}
    assert "auto_scientist/experiment_tree.json" in package_paths
    assert "auto_scientist/experiment_tree.md" in package_paths


def test_auto_scientist_api_accepts_tree_and_docker_sandbox_policy_flags(demo_project_dir: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.tools.auto_scientist.generated_code_sandbox.shutil.which", lambda _name: None)
    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/auto-scientist/run",
        json={
            "topic": "docker policy plus tree search",
            "max_ideas": 1,
            "max_experiments_per_idea": 1,
            "write_paper": False,
            "export_latex": False,
            "allow_generated_code_experiments": True,
            "generated_code_sandbox_mode": "docker",
            "generated_code_docker_image": "python:3.11-slim",
            "enable_experiment_tree_search": True,
            "experiment_tree_max_depth": 1,
            "experiment_tree_branching_factor": 1,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["run"]["generated_code_experiments_enabled"] is True
    assert payload["run"]["generated_code_sandbox_mode"] == "docker"
    assert payload["run"]["experiment_tree_search_enabled"] is True
    assert payload["experiment_tree"]["tree_search_enabled"] is True
    status = read_auto_scientist_status("demo_project")
    assert status["experiment_tree_search_enabled"] is True
