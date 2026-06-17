from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.tools.auto_scientist.idea_generator import generate_scientist_ideas, read_scientist_ideas
from app.tools.auto_scientist.experiment_runner import build_experiment_plan, run_experiment_plan
from app.tools.auto_scientist.scientist_loop import run_auto_scientist, read_auto_scientist_status


def test_auto_scientist_generates_safe_ideas(demo_project_dir: Path) -> None:
    ideas = generate_scientist_ideas(
        demo_project_dir,
        "demo_project",
        project_name="Demo Materials Project",
        domain="materials",
        topic="efficiency and stability",
        max_ideas=2,
    )

    assert ideas["schema_version"].endswith("ideas.v1")
    assert ideas["arbitrary_code_execution"] is False
    assert len(ideas["ideas"]) == 2
    assert all(item["experiment_templates"] for item in ideas["ideas"])
    assert read_scientist_ideas(demo_project_dir)["project_id"] == "demo_project"
    assert (demo_project_dir / "auto_scientist" / "ideas.json").exists()


def test_auto_scientist_safe_experiment_runner_writes_artifacts(demo_project_dir: Path) -> None:
    ideas = generate_scientist_ideas(
        demo_project_dir,
        "demo_project",
        project_name="Demo Materials Project",
        domain="materials",
        topic="efficiency and stability",
        max_ideas=1,
    )
    plan = build_experiment_plan(demo_project_dir, "demo_project", ideas, max_experiments_per_idea=2)
    results = run_experiment_plan(demo_project_dir, "demo_project", plan, run_id="test_run")

    assert plan["arbitrary_code_execution"] is False
    assert plan["experiments"]
    assert results
    assert all(item["arbitrary_code_execution"] is False for item in results)
    for item in results:
        assert item["output_files"]
        for relative_path in item["output_files"]:
            assert (demo_project_dir / relative_path).exists()


def test_auto_scientist_full_loop_creates_paper_and_review(demo_project_dir: Path) -> None:
    payload = run_auto_scientist(
        "demo_project",
        topic="efficiency and stability",
        max_ideas=1,
        max_experiments_per_idea=2,
        write_paper=True,
        export_latex=True,
    )

    run = payload["run"]
    assert run["status"] == "completed"
    assert run["arbitrary_code_execution"] is False
    assert run["paper_outputs"]["draft_file"] == "manuscript/draft_full.md"
    assert run["paper_outputs"]["latex_file"] == "manuscript/draft_full.tex"
    assert run["autonomous_paper_file"] == "manuscript/auto_scientist_paper.md"
    assert run["autonomous_paper_latex_file"] == "manuscript/auto_scientist_paper.tex"
    assert payload["review"]["not_peer_review"] is True
    assert (demo_project_dir / "auto_scientist" / "latest_run.json").exists()
    assert (demo_project_dir / "auto_scientist" / "analysis.json").exists()
    assert (demo_project_dir / "auto_scientist" / "scientist_review.json").exists()
    assert (demo_project_dir / "manuscript" / "draft_full.md").exists()
    assert (demo_project_dir / "manuscript" / "auto_scientist_paper.md").exists()
    assert (demo_project_dir / "manuscript" / "auto_scientist_paper.tex").exists()
    assert (demo_project_dir / "auto_scientist" / "paper_audit.json").exists()
    status = read_auto_scientist_status("demo_project")
    assert status["latest_run"]["run_id"] == run["run_id"]


def test_auto_scientist_api_runs_offline(demo_project_dir: Path) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/auto-scientist/run",
        json={
            "topic": "local evidence synthesis",
            "max_ideas": 1,
            "max_experiments_per_idea": 1,
            "write_paper": True,
            "export_latex": True,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["run"]["arbitrary_code_execution"] is False
    assert payload["run"]["autonomous_paper_file"] == "manuscript/auto_scientist_paper.md"
    assert payload["experiment_results"]
    status = client.get("/api/projects/demo_project/auto-scientist/status")
    assert status.status_code == 200
    assert status.json()["latest_run"]["status"] == "completed"
