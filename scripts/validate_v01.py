from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from fastapi.testclient import TestClient

from main import app
from scripts.run_demo import REQUIRED_FILES
from scripts.seed_demo import main as seed_demo


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    client = TestClient(app)
    health = client.get("/health")
    assert_true(health.status_code == 200, "/health must return 200")
    assert_true(health.json().get("status") == "ok", "/health status must be ok")

    create_response = client.post(
        "/api/projects",
        json={
            "name": "验证项目",
            "domain": "materials",
            "language": "zh",
            "output_format": "markdown",
        },
    )
    assert_true(create_response.status_code == 201, "project creation must return 201")
    assert_true(bool(create_response.json().get("id")), "project id must exist")

    seed_demo()
    run_response = client.post("/api/projects/demo_project/workflow/run")
    assert_true(run_response.status_code == 200, "workflow run must return 200")
    payload = run_response.json()
    assert_true(payload["workflow_status"] == "completed", "workflow must complete")

    project_dir = ROOT / "projects" / "demo_project"
    for relative in REQUIRED_FILES:
        assert_true((project_dir / relative).exists(), f"required file missing: {relative}")

    evidence = json.loads((project_dir / "provenance" / "evidence.json").read_text(encoding="utf-8"))
    assert_true(len(evidence) >= 1, "evidence.json must contain at least one claim")

    figure_provenance = json.loads(
        (project_dir / "figures" / "figure_provenance.json").read_text(encoding="utf-8")
    )
    assert_true(
        all(item["is_ai_generated"] is False for item in figure_provenance),
        "all figures must have is_ai_generated=false",
    )

    review = json.loads((project_dir / "reviews" / "review_report.json").read_text(encoding="utf-8"))
    assert_true("overall_decision" in review, "review_report.json must include overall_decision")

    draft = (project_dir / "manuscript" / "draft.md").read_text(encoding="utf-8")
    for heading in [
        "Abstract",
        "Introduction",
        "Methods",
        "Results",
        "Discussion",
        "Conclusion",
        "Evidence Checklist",
    ]:
        assert_true(heading in draft, f"draft.md must include {heading}")

    print("ResearchAgent v0.1 validation passed.")


if __name__ == "__main__":
    main()
