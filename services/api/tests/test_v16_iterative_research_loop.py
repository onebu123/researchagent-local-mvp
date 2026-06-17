from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.tools.iterative_research_loop import (
    read_agent_runs,
    read_iterative_research_loop_latest,
    run_iterative_research_loop,
)
from main import app


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_iterative_loop_mock_outputs_are_deterministic(demo_project_dir: Path) -> None:
    result = run_iterative_research_loop(
        "demo_project",
        max_rounds=1,
        topic="local demo materials analysis",
    )

    assert result["mode"] == "mock_offline"
    assert result["executed_rounds"] == 1
    assert result["rounds"][0]["round_id"] == "round_1"
    assert result["rounds"][0]["draft_file"] == "manuscript/draft_round_1.md"

    draft = (demo_project_dir / "manuscript" / "draft_round_1.md").read_text(encoding="utf-8")
    assert "# ResearchAgent Iterative Draft Round 1" in draft
    assert "Evidence-grounded claims" in draft
    assert "mock/offline mode" in draft
    assert (demo_project_dir / "agent" / "allowed_claims.json").exists()
    assert (demo_project_dir / "agent" / "unsupported_claims.json").exists()
    assert (demo_project_dir / "agent" / "generation_notes.json").exists()


def test_reviewer_issue_enters_revision_plan(demo_project_dir: Path) -> None:
    result = run_iterative_research_loop("demo_project", max_rounds=1)
    plan_file = result["rounds"][0]["revision_plan_file"]
    plan = _load_json(demo_project_dir / plan_file)

    reviewer_names = {
        reviewer["reviewer_name"]
        for reviewer in result["rounds"][0]["reviewer_records"]
        if reviewer["blocking_issues"]
    }
    patch_sources = {patch["issue_source"] for patch in plan["patches"]}

    assert "CitationReviewer" in reviewer_names
    assert "CitationReviewer" in patch_sources
    assert all(patch["requires_human_approval"] is True for patch in plan["patches"])
    assert all(patch["auto_applied"] is False for patch in plan["patches"])


def test_revision_does_not_overwrite_formal_draft(demo_project_dir: Path) -> None:
    formal_draft = demo_project_dir / "manuscript" / "draft.md"
    before = formal_draft.read_text(encoding="utf-8")

    result = run_iterative_research_loop("demo_project", max_rounds=1)

    assert formal_draft.read_text(encoding="utf-8") == before
    assert result["formal_draft_modified"] is False
    assert (demo_project_dir / "manuscript" / "revised_round_1.md").exists()


def test_iterative_loop_respects_max_rounds_when_blocking_issues_remain(
    demo_project_dir: Path,
) -> None:
    result = run_iterative_research_loop("demo_project", max_rounds=2)

    assert result["executed_rounds"] == 2
    assert result["stopped_reason"] == "max_rounds_reached"
    assert [round_item["round_number"] for round_item in result["rounds"]] == [1, 2]
    assert all(round_item["blocking_issue_count"] >= 1 for round_item in result["rounds"])


def test_iterative_loop_records_audit_run_history_and_agent_runs(
    demo_project_dir: Path,
) -> None:
    result = run_iterative_research_loop("demo_project", max_rounds=1)

    audit_log = (demo_project_dir / "audit" / "audit_log.jsonl").read_text(encoding="utf-8")
    run_history = _load_json(demo_project_dir / "runs" / "run_history.json")
    agent_runs = read_agent_runs("demo_project")
    latest = read_iterative_research_loop_latest("demo_project")

    assert "iterative_generator_round" in audit_log
    assert "iterative_reviewer_round" in audit_log
    assert "iterative_reviser_round" in audit_log
    assert any(run["run_type"] == "iterative_research_loop" for run in run_history["runs"])
    assert agent_runs
    assert agent_runs[-1]["round_id"] == result["rounds"][0]["round_id"]
    assert latest["available"] is True
    assert latest["latest_outputs"]["research_loop_runs_file"] == "agent/research_loop_runs.jsonl"


def test_iterative_loop_api_contracts(demo_project_dir: Path) -> None:
    client = TestClient(app)

    created = client.post(
        "/api/projects/demo_project/agent/iterative-loop",
        json={"max_rounds": 1, "research_question": "What does the local evidence support?"},
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["executed_rounds"] == 1
    assert payload["latest_outputs"]["latest_revision_plan_file"] == "agent/revision_plan_round_1.json"

    latest = client.get("/api/projects/demo_project/agent/iterative-loop/latest")
    assert latest.status_code == 200
    assert latest.json()["available"] is True

    runs = client.get("/api/projects/demo_project/agent/runs")
    assert runs.status_code == 200
    assert runs.json()
