from __future__ import annotations

import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.tools.auto_scientist.idea_generator import generate_scientist_ideas
from app.tools.auto_scientist.reference_brief import build_reference_brief
from app.tools.auto_scientist.scientist_loop import run_auto_scientist
from app.tools.evidence_trust_package import build_evidence_trust_package
from app.tools.human_review_queue import build_human_review_queue
from main import app
from tests.v12_helpers import base_literature_entry, write_v12_project


def test_reference_based_ideas_write_local_reference_brief(demo_project_dir: Path) -> None:
    ideas = generate_scientist_ideas(
        demo_project_dir,
        "demo_project",
        project_name="Demo Materials Project",
        domain="materials",
        topic="efficiency and stability",
        max_ideas=1,
        reference_literature_ids=["lit_001"],
    )

    assert ideas["reference_literature_ids"] == ["lit_001"]
    assert ideas["reference_brief_file"] == "auto_scientist/reference_brief.json"
    assert ideas["reference_brief"]["summary"]["reference_count"] == 1
    assert ideas["ideas"][0]["reference_literature_ids"] == ["lit_001"]
    assert "selected local reference materials" in " ".join(ideas["ideas"][0]["limitations"])
    assert "novelty" in " ".join(ideas["ideas"][0]["limitations"])
    assert (demo_project_dir / "auto_scientist" / "reference_brief.json").exists()
    assert (demo_project_dir / "auto_scientist" / "reference_brief.md").exists()


def test_invalid_reference_literature_id_returns_400(demo_project_dir: Path) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/auto-scientist/ideas",
        json={
            "topic": "bounded local ideation",
            "reference_literature_ids": ["missing_lit"],
        },
    )

    assert response.status_code == 400
    assert "literature_id not found" in response.text


def test_placeholder_metadata_is_not_verified_source(tmp_path: Path) -> None:
    write_v12_project(
        tmp_path,
        [
            base_literature_entry(
                metadata_status="placeholder",
                human_verified=False,
                reference_verification_status=None,
            )
        ],
        source_text="# Placeholder source\n\nThis placeholder local source mentions retrieval coverage and limitations.",
    )

    brief = build_reference_brief(tmp_path, "local_project", ["lit_001"])
    record = brief["records"][0]

    assert record["verified_source"] is False
    assert record["coverage"]["source_passage_count"] >= 1
    assert brief["summary"]["placeholder_metadata_count"] == 1
    assert any("placeholder" in warning for warning in record["warnings"])
    assert "literature_index.json" in (tmp_path / "auto_scientist" / "reference_brief.md").read_text(encoding="utf-8")


def test_reference_brief_enters_run_review_queue_and_trust_package(demo_project_dir: Path) -> None:
    payload = run_auto_scientist(
        "demo_project",
        topic="bounded local ideation",
        max_ideas=1,
        max_experiments_per_idea=1,
        write_paper=False,
        export_latex=False,
        reference_literature_ids=["lit_001"],
    )

    run = payload["run"]
    assert run["reference_literature_ids"] == ["lit_001"]
    assert run["reference_brief_file"] == "auto_scientist/reference_brief.json"
    assert run["reference_brief_summary"]["reference_count"] == 1

    queue = build_human_review_queue(demo_project_dir, "demo_project")
    assert any(item["review_id"] == "auto_scientist_reference_brief_review" for item in queue["items"])

    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    paths = {item["relative_path"] for item in package["files"]}
    assert "auto_scientist/reference_brief.json" in paths
    assert "auto_scientist/reference_brief.md" in paths
    package_path = demo_project_dir / package["package_file"]
    with zipfile.ZipFile(package_path) as zf:
        names = set(zf.namelist())
    assert "evidence_trust_package/auto_scientist/reference_brief.json" in names

    brief = json.loads((demo_project_dir / "auto_scientist" / "reference_brief.json").read_text(encoding="utf-8"))
    assert "scientific validity" in " ".join(brief["limitations"])
