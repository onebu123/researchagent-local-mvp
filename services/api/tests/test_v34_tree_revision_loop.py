from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.services.project_service import ProjectNotFoundError, project_service
from scripts.seed_demo import main as seed_demo
from app.tools.auto_scientist.experiment_tree_ops import list_experiment_tree_nodes, select_experiment_tree_node
from app.tools.auto_scientist.scientist_loop import run_auto_scientist
from app.tools.auto_scientist.tree_revision_loop import (
    LATEST_TREE_REVISION_APPLICATION_JSON,
    REVISED_AUTONOMOUS_PAPER_MD,
    TREE_REVISION_APPLICATIONS_JSONL,
    TREE_REVISION_PATCHES_JSON,
    TREE_REVISION_PLAN_JSON,
    apply_tree_revision_patches,
    generate_tree_revision_plan,
)
from app.tools.evidence_trust_package import build_evidence_trust_package
from app.tools.human_review_queue import DECISIONS_FILE, build_human_review_queue, record_human_review_decision




def _ensure_demo_project_record() -> None:
    try:
        project_service.require_project("demo_project")
    except ProjectNotFoundError:
        seed_demo()


def _make_tree_run(project_dir: Path) -> str:
    _ensure_demo_project_record()
    # Keep tree-revision approval gates isolated across tests that share demo_project.
    (project_dir / DECISIONS_FILE).unlink(missing_ok=True)
    run_auto_scientist(
        "demo_project",
        topic="tree revision loop",
        research_question="Can selected experiment nodes drive cautious manuscript revision?",
        max_ideas=1,
        max_experiments_per_idea=1,
        write_paper=True,
        export_latex=True,
        allow_generated_code_experiments=False,
        enable_experiment_tree_search=True,
        experiment_tree_max_depth=1,
        experiment_tree_branching_factor=1,
    )
    nodes = list_experiment_tree_nodes(project_dir)
    assert nodes["nodes"]
    return str(nodes["nodes"][0]["node_id"])


def test_tree_revision_plan_requires_human_approval_before_apply(demo_project_dir: Path) -> None:
    node_id = _make_tree_run(demo_project_dir)
    select_experiment_tree_node(demo_project_dir, "demo_project", node_id, reason="unit test selected node")

    plan = generate_tree_revision_plan(
        demo_project_dir,
        "demo_project",
        node_id=node_id,
        reason="unit test revision plan",
    )

    assert plan["selected_node_id"] == node_id
    assert plan["patch_suggestions"]
    assert (demo_project_dir / TREE_REVISION_PLAN_JSON).exists()
    assert (demo_project_dir / TREE_REVISION_PATCHES_JSON).exists()

    queue = build_human_review_queue(demo_project_dir, "demo_project")
    review_ids = {item["review_id"] for item in queue["items"]}
    for patch in plan["patch_suggestions"]:
        assert patch["review_id"] in review_ids

    try:
        apply_tree_revision_patches(demo_project_dir, "demo_project")
    except PermissionError as exc:
        assert "require approved human review" in str(exc)
    else:  # pragma: no cover - explicit failure path
        raise AssertionError("tree revision patches must require approval before application")

    for patch in plan["patch_suggestions"]:
        record_human_review_decision(
            demo_project_dir,
            "demo_project",
            patch["review_id"],
            "approved",
            "unit test approved tree revision patch",
            source="test",
        )

    application = apply_tree_revision_patches(
        demo_project_dir,
        "demo_project",
        reason="unit test apply approved patches",
        require_human_approval=True,
        rerun_claim_audit=True,
        regenerate_trust_package=True,
    )

    assert application["human_approval_satisfied"] is True
    assert application["applied_patch_ids"]
    assert application["revised_paper_file"] == REVISED_AUTONOMOUS_PAPER_MD
    assert (demo_project_dir / REVISED_AUTONOMOUS_PAPER_MD).exists()
    assert (demo_project_dir / TREE_REVISION_APPLICATIONS_JSONL).exists()
    assert (demo_project_dir / LATEST_TREE_REVISION_APPLICATION_JSON).exists()
    revised = (demo_project_dir / REVISED_AUTONOMOUS_PAPER_MD).read_text(encoding="utf-8")
    assert "Selected Experiment Node Interpretation" in revised
    assert "requires human review" in revised


def test_tree_revision_api_and_trust_package_contract(demo_project_dir: Path) -> None:
    node_id = _make_tree_run(demo_project_dir)
    client = TestClient(app)

    plan_response = client.post(
        "/api/projects/demo_project/auto-scientist/experiment-tree/revision-plan",
        json={"node_id": node_id, "reason": "api creates revision plan"},
    )
    assert plan_response.status_code == 200, plan_response.text
    plan = plan_response.json()
    assert plan["selected_node_id"] == node_id
    assert plan["patch_suggestions"]

    blocked_apply = client.post(
        "/api/projects/demo_project/auto-scientist/experiment-tree/apply-revision",
        json={"reason": "should be blocked until approval"},
    )
    assert blocked_apply.status_code == 403, blocked_apply.text

    for patch in plan["patch_suggestions"]:
        decision_response = client.post(
            f"/api/projects/demo_project/human-review-queue/{patch['review_id']}/decision",
            json={"decision": "approved", "reason": "api approval for tree patch"},
        )
        assert decision_response.status_code == 200, decision_response.text

    apply_response = client.post(
        "/api/projects/demo_project/auto-scientist/experiment-tree/apply-revision",
        json={"reason": "api applies approved tree patches", "rerun_claim_audit": True, "regenerate_trust_package": True},
    )
    assert apply_response.status_code == 200, apply_response.text
    assert apply_response.json()["revised_paper_file"] == REVISED_AUTONOMOUS_PAPER_MD

    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    paths = {item["relative_path"] for item in package["files"]}
    assert "auto_scientist/tree_revision_plan.json" in paths
    assert "auto_scientist/tree_revision_patches.json" in paths
    assert "auto_scientist/tree_revision_applications.jsonl" in paths
    assert "auto_scientist/latest_tree_revision_application.json" in paths
    assert "manuscript/auto_scientist_paper_revised.md" in paths
