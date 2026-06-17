from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from app.tools.auto_scientist.experiment_tree_ops import (
    EXPERIMENT_TREE_RERUNS_JSONL,
    EXPERIMENT_TREE_SELECTION_JSON,
    LATEST_PAPER_REWRITE_JSON,
    list_experiment_tree_nodes,
    rerun_experiment_tree_node,
    rewrite_auto_scientist_paper_from_tree,
    select_experiment_tree_node,
)
from app.tools.auto_scientist.scientist_loop import run_auto_scientist
from app.tools.evidence_trust_package import build_evidence_trust_package


def test_experiment_tree_node_select_rerun_and_paper_rewrite(demo_project_dir: Path) -> None:
    payload = run_auto_scientist(
        "demo_project",
        topic="tree node manuscript rewrite",
        research_question="Can selected experiment tree nodes drive a safer manuscript rewrite?",
        max_ideas=1,
        max_experiments_per_idea=1,
        write_paper=True,
        export_latex=True,
        allow_generated_code_experiments=False,
        enable_experiment_tree_search=True,
        experiment_tree_max_depth=1,
        experiment_tree_branching_factor=1,
    )
    assert payload["run"]["experiment_tree_search_enabled"] is True
    nodes_payload = list_experiment_tree_nodes(demo_project_dir)
    assert nodes_payload["nodes"]
    node_id = nodes_payload["nodes"][0]["node_id"]

    selection = select_experiment_tree_node(
        demo_project_dir,
        "demo_project",
        node_id,
        reason="unit test selects a tree node",
    )
    assert selection["latest_selection"]["node_id"] == node_id
    assert (demo_project_dir / EXPERIMENT_TREE_SELECTION_JSON).exists()

    rerun = rerun_experiment_tree_node(demo_project_dir, "demo_project", node_id)
    assert rerun["source_node_id"] == node_id
    assert rerun["results"]
    assert (demo_project_dir / EXPERIMENT_TREE_RERUNS_JSONL).exists()

    rewrite = rewrite_auto_scientist_paper_from_tree(
        demo_project_dir,
        "demo_project",
        node_id=node_id,
        reason="unit test rewrites manuscript from tree node",
    )
    assert rewrite["selected_node_id"] == node_id
    assert rewrite["paper_file"] == "manuscript/auto_scientist_paper.md"
    assert (demo_project_dir / LATEST_PAPER_REWRITE_JSON).exists()
    manuscript = (demo_project_dir / "manuscript" / "auto_scientist_paper.md").read_text(encoding="utf-8")
    assert "Tree search best node for manuscript emphasis" in manuscript
    assert "not scientific proof" in manuscript


def test_experiment_tree_node_api_and_trust_package(demo_project_dir: Path) -> None:
    run_auto_scientist(
        "demo_project",
        topic="tree node API workflow",
        research_question="Can the API expose tree nodes for review and rerun?",
        max_ideas=1,
        max_experiments_per_idea=1,
        write_paper=True,
        export_latex=True,
        enable_experiment_tree_search=True,
        experiment_tree_max_depth=1,
        experiment_tree_branching_factor=1,
    )
    client = TestClient(app)
    nodes_response = client.get("/api/projects/demo_project/auto-scientist/experiment-tree/nodes")
    assert nodes_response.status_code == 200, nodes_response.text
    node_id = nodes_response.json()["nodes"][0]["node_id"]

    select_response = client.post(
        "/api/projects/demo_project/auto-scientist/experiment-tree/select",
        json={"node_id": node_id, "reason": "api selected best candidate"},
    )
    assert select_response.status_code == 200, select_response.text
    assert select_response.json()["latest_selection"]["node_id"] == node_id

    rerun_response = client.post(
        "/api/projects/demo_project/auto-scientist/experiment-tree/rerun-node",
        json={"node_id": node_id, "sandbox_mode": "subprocess"},
    )
    assert rerun_response.status_code == 200, rerun_response.text
    assert rerun_response.json()["results"]

    rewrite_response = client.post(
        "/api/projects/demo_project/auto-scientist/experiment-tree/rewrite-paper",
        json={"node_id": node_id, "reason": "api rewrite from selected node"},
    )
    assert rewrite_response.status_code == 200, rewrite_response.text
    assert rewrite_response.json()["selected_node_id"] == node_id

    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    paths = {item["relative_path"] for item in package["files"]}
    assert "auto_scientist/experiment_tree_selection.json" in paths
    assert "auto_scientist/experiment_tree_reruns.jsonl" in paths
    assert "auto_scientist/latest_paper_rewrite.json" in paths
    assert "auto_scientist/paper_rewrites.jsonl" in paths
