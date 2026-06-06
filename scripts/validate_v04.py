from __future__ import annotations

import contextlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.services.storage_service import storage_service
from app.services.workflow_service import workflow_service
from main import app
from scripts.seed_demo import main as seed_demo
from scripts.validate_v01 import main as validate_v01
from scripts.validate_v02 import main as validate_v02
from scripts.validate_v03 import main as validate_v03


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def run_quietly(func) -> object:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        return func()


def assert_revision_diff(diff: dict) -> None:
    for field in [
        "can_auto_suggest",
        "before",
        "after",
        "change_type",
        "preserved_claim_id",
        "preserved_numbers",
        "preserved_units",
        "requires_human_approval",
        "warnings",
    ]:
        assert_true(field in diff, f"revision_diff must include {field}")
    assert_true(diff["requires_human_approval"] is True, "revision_diff requires human approval")
    assert_true(diff["before"], "revision_diff before must not be empty")
    assert_true(diff["after"], "revision_diff after must not be empty")


def assert_pdf_pages(project_dir: Path) -> None:
    metadata_path = project_dir / "literature" / "parsed" / "demo_pdf_literature.metadata.json"
    assert_true(metadata_path.exists(), "PDF parse metadata must exist")
    metadata = read_json(metadata_path)
    assert_true(isinstance(metadata, dict), "PDF metadata must be an object")
    pages = metadata.get("pages")
    assert_true(isinstance(pages, list) and pages, "PDF metadata pages must be non-empty list")
    empty_count = sum(1 for page in pages if isinstance(page, dict) and page.get("empty") is True)
    assert_true(metadata.get("empty_page_count") == empty_count, "empty_page_count must match pages")
    for page in pages:
        assert_true(isinstance(page, dict), "PDF page record must be object")
        for field in ["page_number", "char_count", "empty", "warnings", "quality_signal", "ocr"]:
            assert_true(field in page, f"PDF page must include {field}")
        ocr = page["ocr"]
        assert_true(isinstance(ocr, dict), "PDF page ocr must be object")
        assert_true(ocr.get("ocr_attempted") is False, "OCR must not run in v0.4")
        assert_true(ocr.get("ocr_engine") is None, "OCR engine must be reserved as null")
        assert_true(ocr.get("ocr_status") == "not_configured", "OCR status must be not_configured")
        assert_true(ocr.get("ocr_text_file") is None, "OCR text file must be null")


def assert_analysis_provenance(project_dir: Path) -> None:
    provenance_path = project_dir / "analysis" / "analysis_provenance.json"
    assert_true(provenance_path.exists(), "analysis_provenance.json must exist")
    provenance = read_json(provenance_path)
    assert_true(isinstance(provenance, dict), "analysis_provenance must be object")
    for field in ["parameters", "script_version", "random_seed", "output_file_hashes"]:
        assert_true(field in provenance, f"analysis_provenance must include {field}")
    assert_true(provenance["random_seed"] == 42, "random_seed must be 42 for demo")
    output_hashes = provenance["output_file_hashes"]
    assert_true(isinstance(output_hashes, dict), "output_file_hashes must be object")
    for relative_path in provenance.get("generated_files", []):
        assert_true(relative_path in output_hashes, f"output_file_hashes missing {relative_path}")
        assert_true((project_dir / relative_path).exists(), f"generated file missing: {relative_path}")
    limitations = "\n".join(str(item) for item in provenance.get("limitations", [])).lower()
    assert_true("p-values" in limitations, "limitations must state no p-values")
    assert_true("causal inference" in limitations, "limitations must state no causal inference")


def assert_audit_log(project_dir: Path) -> None:
    audit_path = project_dir / "audit" / "audit_log.jsonl"
    assert_true(audit_path.exists(), "audit_log.jsonl must exist")
    text = audit_path.read_text(encoding="utf-8")
    assert_true("run_workflow" in text or "run_workflow_step" in text, "audit log must record workflow")
    assert_true(not re.search(r"[A-Za-z]:[\\/]", text), "audit log must not include absolute paths")
    assert_true(ROOT.as_posix() not in text.replace("\\", "/"), "audit log must not include workspace path")


def assert_run_history(project_dir: Path) -> None:
    run_path = project_dir / "runs" / "run_history.json"
    assert_true(run_path.exists(), "run_history.json must exist")
    payload = read_json(run_path)
    assert_true(isinstance(payload, dict), "run_history must be object")
    runs = payload.get("runs")
    assert_true(isinstance(runs, list) and runs, "run_history runs must be non-empty")
    assert_true(
        any(isinstance(run, dict) and run.get("status") == "completed" for run in runs),
        "run_history must contain a completed run",
    )


def assert_frontend_typecheck() -> None:
    npm_command = "npm.cmd" if sys.platform.startswith("win") else "npm"
    result = subprocess.run(
        [npm_command, "run", "typecheck"],
        cwd=ROOT / "apps" / "web",
        capture_output=True,
        text=True,
        check=False,
    )
    assert_true(result.returncode == 0, "frontend typecheck must pass in validate_v04")


def main() -> None:
    run_quietly(validate_v01)
    run_quietly(validate_v02)
    run_quietly(validate_v03)
    run_quietly(seed_demo)
    response = run_quietly(lambda: workflow_service.run_workflow("demo_project"))
    assert_true(response.workflow_status == "completed", "workflow must complete")

    project_dir = storage_service.project_dir("demo_project")
    assert_true(project_dir.exists(), "demo_project must exist")

    review_path = project_dir / "reviews" / "review_report.json"
    assert_true(review_path.exists(), "review_report.json must exist")
    review = read_json(review_path)
    assert_true(isinstance(review, dict), "review_report.json must be object")
    sentence_issues = review.get("sentence_issues")
    assert_true(isinstance(sentence_issues, list) and sentence_issues, "sentence_issues must be non-empty")
    issue_with_diff = next(
        (issue for issue in sentence_issues if isinstance(issue, dict) and isinstance(issue.get("revision_diff"), dict)),
        None,
    )
    assert_true(issue_with_diff is not None, "at least one sentence issue must include revision_diff")
    assert_revision_diff(issue_with_diff["revision_diff"])

    client = TestClient(app)
    draft_path = project_dir / "manuscript" / "draft.md"
    original_draft = draft_path.read_text(encoding="utf-8")
    decision_response = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue_with_diff['issue_id']}/decision",
        json={"decision": "accepted", "reason": "validate_v04 acceptance marker"},
    )
    assert_true(decision_response.status_code == 200, "revision decision API must return 200")
    decision = decision_response.json()
    assert_true(decision["applied_to_manuscript"] is False, "revision decision must not apply to manuscript")
    assert_true(draft_path.read_text(encoding="utf-8") == original_draft, "draft.md must not change")
    decisions_path = project_dir / "reviews" / "revision_decisions.jsonl"
    assert_true(decisions_path.exists(), "revision_decisions.jsonl must exist")
    decisions = [json.loads(line) for line in decisions_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert_true(any(item["issue_id"] == issue_with_diff["issue_id"] for item in decisions), "decision JSONL must include issue")

    literature_index_path = project_dir / "literature" / "literature_index.json"
    original_index = literature_index_path.read_text(encoding="utf-8")
    literature_index = read_json(literature_index_path)
    assert_true(isinstance(literature_index, list) and literature_index, "literature_index must be non-empty")
    first_literature_id = literature_index[0]["literature_id"]
    patch_response = client.patch(
        f"/api/projects/demo_project/literature/{first_literature_id}",
        json={
            "title": "validate_v04 metadata history marker",
            "authors": [],
            "year": None,
            "doi": None,
            "journal": None,
            "metadata_status": "placeholder",
            "human_verified": False,
        },
    )
    assert_true(patch_response.status_code == 200, "literature PATCH must succeed")
    history_path = project_dir / "literature" / "metadata_history.jsonl"
    assert_true(history_path.exists(), "metadata_history.jsonl must exist after PATCH")
    history_text = history_path.read_text(encoding="utf-8")
    assert_true(first_literature_id in history_text, "metadata history must include literature_id")
    literature_index_path.write_text(original_index, encoding="utf-8")

    assert_pdf_pages(project_dir)
    assert_analysis_provenance(project_dir)
    assert_audit_log(project_dir)
    assert_run_history(project_dir)

    for endpoint in [
        "/api/projects/demo_project/review/revision-decisions",
        "/api/projects/demo_project/literature/history",
        "/api/projects/demo_project/audit",
        "/api/projects/demo_project/runs",
    ]:
        api_response = client.get(endpoint)
        assert_true(api_response.status_code == 200, f"API must be readable: {endpoint}")

    assert_frontend_typecheck()
    print("ResearchAgent v0.4 validation passed.")


if __name__ == "__main__":
    main()
