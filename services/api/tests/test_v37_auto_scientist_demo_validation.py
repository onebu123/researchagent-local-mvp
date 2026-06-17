from __future__ import annotations

import json
from pathlib import Path

from scripts.run_auto_scientist_demo import REQUIRED_DEMO_ARTIFACTS, build_auto_scientist_demo_report
from scripts.validate_v37 import build_validation_report


def _write(path: Path, text: str = "{}") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_v37_static_validation_contract_passes() -> None:
    report = build_validation_report()
    assert report["passed"], report["failures"]
    assert report["coverage"]["source_files_checked"] >= 10
    assert report["coverage"]["frontend_markers_checked"] >= 5


def test_auto_scientist_demo_report_detects_required_artifacts(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    for relative in REQUIRED_DEMO_ARTIFACTS:
        if relative.endswith(".jsonl"):
            _write(project_dir / relative, '{"record": true}\n')
        elif relative.endswith(".md"):
            _write(project_dir / relative, "# Demo\n")
        elif relative.endswith(".tex"):
            _write(project_dir / relative, "\\documentclass{article}\n")
        elif relative.endswith(".pdf"):
            (project_dir / relative).parent.mkdir(parents=True, exist_ok=True)
            (project_dir / relative).write_bytes(b"%PDF-1.4\n% demo\n")
        else:
            _write(project_dir / relative, "{}")
    _write(project_dir / "auto_scientist" / "latest_run.json", json.dumps({"run_id": "run_demo", "status": "completed"}))
    _write(project_dir / "trust" / "human_review_queue.json", json.dumps({"summary": {"pending": 2}}))
    _write(project_dir / "exports" / "evidence_trust_package" / "manifest.json", json.dumps({"files": [{"relative_path": "x"}]}))
    _write(project_dir / "auto_scientist" / "experiment_claim_bindings.json", json.dumps({"summary": {"bound": 1}}))
    _write(project_dir / "manuscript" / "paper_citation_bindings.json", json.dumps({"summary": {"bound": 1}}))
    _write(project_dir / "manuscript" / "latex_compile_report.json", json.dumps({"compile_status": "preview_generated"}))

    report = build_auto_scientist_demo_report(project_dir, "demo_project")

    assert report["passed"] is True
    assert report["missing_required_artifacts"] == []
    assert report["summary"]["run_status"] == "completed"
    assert report["summary"]["trust_package_file_count"] == 1


def test_validate_v37_can_check_demo_report(tmp_path: Path) -> None:
    demo_report = tmp_path / "demo_report.json"
    demo_report.write_text(
        json.dumps(
            {
                "passed": True,
                "missing_required_artifacts": [],
                "summary": {
                    "run_status": "completed",
                    "experiment_count": 3,
                    "job_event_count": 8,
                    "trust_package_file_count": 20,
                    "latex_compile_status": "preview_generated",
                },
            }
        ),
        encoding="utf-8",
    )
    report = build_validation_report(demo_report)
    assert report["passed"], report["failures"]
    assert report["coverage"]["demo_report_checked"] is True
