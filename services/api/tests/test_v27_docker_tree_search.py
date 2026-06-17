from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.tools.auto_scientist.experiment_tree_search import run_experiment_tree_search, score_experiment_result
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


def test_experiment_tree_hardening_isolates_failed_child_nodes(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    base_plan = {
        "topic": "tree hardening",
        "research_question": "Can sibling nodes remain reviewable after a child failure?",
        "retrieval_mode": "local_hybrid_fts",
        "experiments": [{"config": {"topic": "tree hardening", "research_question": "rq"}}],
    }
    initial_results = [
        {
            "experiment_id": "base",
            "template_name": "rag_retrieval_eval",
            "status": "completed",
            "generated_code_execution": False,
            "output_files": ["auto_scientist/experiments/run_tree/base/experiment_result.json"],
            "result": {
                "metrics": {"top_source_score": 0.5},
                "claims": [{"support_status": "supported", "claim": "base claim"}],
            },
        }
    ]

    def fake_run_experiment_plan(project_dir_arg, project_id, child_plan, run_id, progress_callback=None):
        experiments = child_plan["experiments"]
        failed = experiments[0]
        sibling = experiments[1]
        return [
            {
                "created_at": "2026-01-01T00:00:00+00:00",
                "run_id": run_id,
                "experiment_id": failed["experiment_id"],
                "template_name": failed["template_name"],
                "status": "failed",
                "error": "RuntimeError",
                "safe_execution": True,
                "generated_code_execution": False,
                "arbitrary_code_execution": False,
                "output_files": ["auto_scientist/experiments/run_tree/failed/experiment_result.json"],
                "metric_keys": [],
                "result": {
                    "status": "failed",
                    "error": "RuntimeError",
                    "metrics": {},
                    "claims": [],
                    "summary_markdown": "# Failed experiment\n\nRuntimeError: synthetic failure\n",
                },
            },
            {
                "created_at": "2026-01-01T00:00:01+00:00",
                "run_id": run_id,
                "experiment_id": sibling["experiment_id"],
                "template_name": sibling["template_name"],
                "status": "completed",
                "safe_execution": True,
                "generated_code_execution": False,
                "arbitrary_code_execution": False,
                "output_files": ["auto_scientist/experiments/run_tree/sibling/experiment_result.json"],
                "metric_keys": ["top_source_score"],
                "result": {
                    "status": "completed",
                    "metrics": {"top_source_score": 0.9},
                    "claims": [{"support_status": "supported", "claim": "sibling claim"}],
                },
            },
        ]

    monkeypatch.setattr("app.tools.auto_scientist.experiment_tree_search.run_experiment_plan", fake_run_experiment_plan)

    tree = run_experiment_tree_search(
        project_dir,
        "demo_project",
        base_plan,
        "run_tree",
        initial_results,
        max_depth=1,
        branching_factor=2,
    )

    statuses = {node["status"] for node in tree["nodes"]}
    assert "failed" in statuses
    assert "completed" in statuses
    assert tree["best_node"]["status"] == "completed"
    assert tree["failure_count"] == 1
    assert tree["failure_log_file"] == "auto_scientist/experiment_tree_failures.jsonl"
    for node in tree["nodes"]:
        assert "score_breakdown" in node
        assert "artifact_refs" in node
        assert "selection_rationale" in node
        assert "failure_reason" in node
    failure_log = project_dir / "auto_scientist" / "experiment_tree_failures.jsonl"
    failures = [json.loads(line) for line in failure_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(failures) == 1
    assert failures[0]["failure_reason"].startswith("status=failed")

    queue = build_human_review_queue(project_dir, "demo_project")
    tree_review = next(item for item in queue["items"] if item["review_id"] == "auto_scientist_experiment_tree_review")
    assert tree_review["recommended_action"] == "review_score_breakdown_failure_isolation_and_best_node_rationale"
    assert "score breakdowns" in tree_review["description"]

    package = build_evidence_trust_package(project_dir, "demo_project")
    package_paths = {str(item["relative_path"]) for item in package["files"]}
    assert "auto_scientist/experiment_tree_failures.jsonl" in package_paths


def test_experiment_tree_best_node_tie_breaker_is_deterministic(tmp_path: Path) -> None:
    first = {
        "experiment_id": "a",
        "template_name": "rag_retrieval_eval",
        "status": "completed",
        "generated_code_execution": False,
        "output_files": [],
        "result": {"metrics": {}, "claims": []},
    }
    second = {
        "experiment_id": "b",
        "template_name": "rag_retrieval_eval",
        "status": "completed",
        "generated_code_execution": False,
        "output_files": [],
        "result": {"metrics": {}, "claims": []},
    }
    base_plan = {"topic": "tie", "research_question": "tie", "retrieval_mode": "local_hybrid_fts", "experiments": []}

    tree_one = run_experiment_tree_search(tmp_path / "one", "demo_project", base_plan, "run_tie_1", [second, first], max_depth=0)
    tree_two = run_experiment_tree_search(tmp_path / "two", "demo_project", base_plan, "run_tie_2", [first, second], max_depth=0)

    assert tree_one["best_node"]["node_id"] == "node_d0_a"
    assert tree_two["best_node"]["node_id"] == "node_d0_a"
    assert tree_one["best_node_selection"]["tie_breaker_fields"]
    assert tree_one["best_node"]["score_breakdown"]["total"] == tree_one["best_node"]["score"]
    summary = (tmp_path / "one" / "auto_scientist" / "experiment_tree.md").read_text(encoding="utf-8")
    assert "Best Node Candidate Summary" in summary
    assert "local product heuristic" in summary


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
    assert tree["best_node_selection"]["selected_node_id"] == tree["best_node"]["node_id"]
    assert tree["best_node"]["score_breakdown"]["total"] == tree["best_node"]["score"]
    assert tree["child_experiment_count"] >= 1
    assert (demo_project_dir / "auto_scientist" / "experiment_tree.json").exists()
    assert (demo_project_dir / "auto_scientist" / "experiment_tree.md").exists()
    assert (demo_project_dir / "auto_scientist" / "experiment_tree_failures.jsonl").exists()
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
