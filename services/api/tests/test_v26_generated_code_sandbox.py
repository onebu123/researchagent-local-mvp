from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.tools.auto_scientist.generated_code_sandbox import (
    GENERATED_CODE_TEMPLATE,
    run_generated_code_experiment,
    scan_generated_python_source,
)
from app.tools.auto_scientist.idea_generator import generate_scientist_ideas
from app.tools.auto_scientist.experiment_runner import build_experiment_plan, run_experiment_plan
from app.tools.auto_scientist.scientist_loop import run_auto_scientist, read_auto_scientist_status
from app.tools.human_review_queue import build_human_review_queue
from app.tools.evidence_trust_package import build_evidence_trust_package


def test_generated_code_static_scan_rejects_unsafe_source() -> None:
    report = scan_generated_python_source("import os\nos.system('echo unsafe')\n")

    assert report["safe"] is False
    assert any("forbidden import" in item or "forbidden attribute" in item for item in report["findings"])


def test_generated_code_sandbox_writes_project_relative_artifacts(demo_project_dir: Path) -> None:
    result = run_generated_code_experiment(
        demo_project_dir,
        "demo_project",
        "sandbox_test_run",
        "sandbox_exp_001",
        {
            "topic": "local evidence synthesis",
            "research_question": "What does local evidence support?",
            "generated_code_timeout_seconds": 5,
            "generated_code_max_memory_mb": 512,
        },
    )

    assert result["status"] == "completed"
    assert result["generated_code_execution"] is True
    assert result["arbitrary_code_execution"] is False
    sandbox = result["sandbox"]
    assert sandbox["enabled"] is True
    assert sandbox["static_scan"]["safe"] is True
    assert sandbox["network_disabled_by_policy"] is True
    assert all(not Path(path).is_absolute() for path in sandbox["output_files"])
    for relative_path in sandbox["output_files"]:
        assert (demo_project_dir / relative_path).exists()


def test_experiment_plan_can_include_sandboxed_generated_code(demo_project_dir: Path) -> None:
    ideas = generate_scientist_ideas(
        demo_project_dir,
        "demo_project",
        project_name="Demo Project",
        domain="materials",
        topic="local evidence synthesis",
        max_ideas=1,
    )
    plan = build_experiment_plan(
        demo_project_dir,
        "demo_project",
        ideas,
        max_experiments_per_idea=1,
        allow_generated_code_experiments=True,
        generated_code_timeout_seconds=5,
        generated_code_max_memory_mb=512,
    )

    assert plan["generated_code_experiments_enabled"] is True
    assert GENERATED_CODE_TEMPLATE in plan["registered_templates"]
    assert any(item["template_name"] == GENERATED_CODE_TEMPLATE for item in plan["experiments"])

    results = run_experiment_plan(demo_project_dir, "demo_project", plan, run_id="sandbox_plan_test")
    generated_results = [item for item in results if item["template_name"] == GENERATED_CODE_TEMPLATE]
    assert generated_results
    assert generated_results[0]["status"] == "completed"
    assert generated_results[0]["generated_code_execution"] is True
    assert generated_results[0]["arbitrary_code_execution"] is False
    assert (generated_results[0]["result"].get("sandbox") or {}).get("static_scan", {}).get("safe") is True


def test_auto_scientist_generated_code_loop_routes_to_human_review(demo_project_dir: Path) -> None:
    payload = run_auto_scientist(
        "demo_project",
        topic="local evidence synthesis",
        max_ideas=1,
        max_experiments_per_idea=1,
        write_paper=False,
        export_latex=False,
        allow_generated_code_experiments=True,
        generated_code_timeout_seconds=5,
        generated_code_max_memory_mb=512,
    )

    run = payload["run"]
    assert run["generated_code_experiments_enabled"] is True
    assert run["sandboxed_generated_code"] is True
    assert run["arbitrary_code_execution"] is False
    assert any(item["template_name"] == GENERATED_CODE_TEMPLATE for item in payload["experiment_results"])
    status = read_auto_scientist_status("demo_project")
    assert status["generated_code_experiments_enabled"] is True

    queue = build_human_review_queue(demo_project_dir, "demo_project")
    review_ids = {item["review_id"] for item in queue["items"]}
    assert "auto_scientist_generated_code_review" in review_ids

    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    package_paths = {str(item["relative_path"]) for item in package["files"]}
    assert any(path.startswith("auto_scientist/generated_code/") for path in package_paths)


def test_auto_scientist_api_generated_code_flag_is_explicit(demo_project_dir: Path) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/auto-scientist/run",
        json={
            "topic": "local generated-code experiment manager",
            "max_ideas": 1,
            "max_experiments_per_idea": 1,
            "write_paper": False,
            "export_latex": False,
            "allow_generated_code_experiments": True,
            "generated_code_timeout_seconds": 5,
            "generated_code_max_memory_mb": 512,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["run"]["generated_code_experiments_enabled"] is True
    assert payload["run"]["arbitrary_code_execution"] is False
    assert any(item["template_name"] == GENERATED_CODE_TEMPLATE for item in payload["experiment_results"])
