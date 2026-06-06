from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
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
from scripts.validate_v04 import main as validate_v04
from scripts.validate_v05 import main as validate_v05
from scripts.validate_v06 import main as validate_v06
from scripts.validate_v07 import main as validate_v07


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def run_quietly(func) -> object:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        return func()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_v08_outputs(project_dir: Path) -> None:
    for relative_path in [
        "manuscript/revision_diffs",
        "analysis/comparisons",
    ]:
        path = (project_dir / relative_path).resolve()
        assert_true(project_dir.resolve() in path.parents, f"cleanup escaped project: {relative_path}")
        if path.exists():
            shutil.rmtree(path)
    for relative_path in [
        "literature/metadata_diff_report.json",
        "literature/metadata_review_batch.json",
        "literature/pdf_quality_report.json",
    ]:
        path = (project_dir / relative_path).resolve()
        assert_true(project_dir.resolve() in path.parents, f"cleanup escaped project: {relative_path}")
        path.unlink(missing_ok=True)


def find_safe_issue(project_dir: Path) -> dict:
    review = read_json(project_dir / "reviews" / "review_report.json")
    assert_true(isinstance(review, dict), "review_report.json must be object")
    issues = review.get("sentence_issues")
    assert_true(isinstance(issues, list) and issues, "sentence_issues must be non-empty")
    draft_text = (project_dir / "manuscript" / "draft.md").read_text(encoding="utf-8")
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        diff = issue.get("revision_diff")
        if isinstance(diff, dict) and diff.get("before") in draft_text and diff.get("after"):
            return issue
    raise AssertionError("no draft-backed revision_diff found for v0.8 validation")


def create_version_for_revision_diff(client: TestClient, project_dir: Path) -> dict:
    issue = find_safe_issue(project_dir)
    decision_response = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "accepted", "reason": "validate_v08 accepted revision"},
    )
    assert_true(decision_response.status_code == 200, "accepted revision decision must be recorded")
    patch_response = client.post("/api/projects/demo_project/manuscript/patches/generate", json={})
    assert_true(patch_response.status_code == 200, "patch generation API must return 200")
    patch = patch_response.json()
    assert_true(patch["items"], "patch must contain at least one item")
    confirm_response = client.post(
        f"/api/projects/demo_project/manuscript/patches/{patch['patch_id']}/confirm",
        json={"decision": "confirmed", "reason": "validate_v08 confirmed patch"},
    )
    assert_true(confirm_response.status_code == 200, "patch confirm API must return 200")
    version = confirm_response.json()["version"]
    assert_true(isinstance(version, dict), "confirmed patch must create version")
    return version


def assert_revision_line_diff(client: TestClient, project_dir: Path, version: dict) -> None:
    draft_hash = sha256_file(project_dir / "manuscript" / "draft.md")
    response = client.post(
        "/api/projects/demo_project/manuscript/revision-diffs/generate",
        json={"base_file": "manuscript/draft.md", "target_file": version["file"]},
    )
    assert_true(response.status_code == 200, "revision line diff API must return 200")
    diff = response.json()
    assert_true((project_dir / diff["relative_path"]).exists(), "revision line diff JSON must exist")
    assert_true(diff["changes"], "revision line diff must include changes")
    first_change = diff["changes"][0]
    for field in ["line_start", "line_end", "section", "before", "after"]:
        assert_true(field in first_change and first_change[field] is not None, f"revision diff must include {field}")
    assert_true(
        first_change["related_issue_ids"] or first_change["related_claim_ids"],
        "revision diff change must link issue or claim id",
    )
    assert_true(sha256_file(project_dir / "manuscript" / "draft.md") == draft_hash, "revision diff must not modify draft.md")


def assert_metadata_reports(client: TestClient, project_dir: Path) -> None:
    index_path = project_dir / "literature" / "literature_index.json"
    original_index = index_path.read_text(encoding="utf-8")
    literature = read_json(index_path)
    assert_true(isinstance(literature, list) and literature, "literature index must be non-empty")
    literature_id = literature[0]["literature_id"]
    patch_response = client.patch(
        f"/api/projects/demo_project/literature/{literature_id}",
        json={
            "title": "validate_v08 metadata diff marker",
            "authors": [],
            "year": None,
            "doi": None,
            "journal": None,
            "metadata_status": "placeholder",
            "human_verified": False,
        },
    )
    assert_true(patch_response.status_code == 200, "literature patch API must return 200")
    diff_response = client.get("/api/projects/demo_project/literature/metadata-diff")
    assert_true(diff_response.status_code == 200, "metadata diff API must return 200")
    report = diff_response.json()
    assert_true((project_dir / "literature" / "metadata_diff_report.json").exists(), "metadata diff report must exist")
    changes = [
        change
        for record in report["records"]
        for change in record["changes"]
        if record["literature_id"] == literature_id
    ]
    assert_true(bool(changes), "metadata diff report must include changed fields")
    assert_true(all("field" in change and "old_value" in change and "new_value" in change for change in changes), "metadata changes must include field old/new values")
    title_change = next(change for change in changes if change["field"] == "title")
    suggestion_response = client.post(
        f"/api/projects/demo_project/literature/{literature_id}/metadata/revert-suggestion",
        json={"field": "title", "source_history_id": title_change["source_history_id"]},
    )
    assert_true(suggestion_response.status_code == 200, "revert suggestion API must return 200")
    suggestion = suggestion_response.json()
    assert_true(suggestion["applied"] is False, "revert suggestion must not be applied")
    assert_true(suggestion["literature_index_modified"] is False, "revert suggestion must not modify index")

    batch_response = client.post("/api/projects/demo_project/literature/metadata-review-batch")
    assert_true(batch_response.status_code == 200, "metadata batch review API must return 200")
    batch = batch_response.json()
    assert_true((project_dir / "literature" / "metadata_review_batch.json").exists(), "metadata batch review report must exist")
    assert_true(batch["literature_index_modified"] is False, "metadata batch review must not modify index")
    placeholders = [record for record in batch["records"] if record["metadata_status"] == "placeholder"]
    assert_true(bool(placeholders), "metadata batch review must include placeholder literature")
    assert_true(all(record["recommended_action"] == "manual_review_required" for record in placeholders), "placeholder literature must require manual review")

    index_path.write_text(original_index, encoding="utf-8")


def assert_pdf_quality_report(client: TestClient, project_dir: Path) -> None:
    response = client.get("/api/projects/demo_project/literature/pdf-quality-report")
    assert_true(response.status_code == 200, "PDF quality report API must return 200")
    report = response.json()
    assert_true((project_dir / "literature" / "pdf_quality_report.json").exists(), "pdf_quality_report.json must exist")
    assert_true("summary" in report and "pdfs" in report, "PDF quality report must include summary and pdfs")
    for record in report["pdfs"]:
        for field in ["low_quality_pages", "suspected_scanned_pages", "issue_categories"]:
            assert_true(field in record, f"PDF quality record must include {field}")
        assert_true("ocr_not_configured" in record["issue_categories"], "PDF quality report must include OCR not configured category")
        assert_true(record["ocr_attempted"] is False, "v0.8 must not run OCR")


def assert_analysis_comparison(client: TestClient, project_dir: Path) -> None:
    response = client.post(
        "/api/projects/demo_project/analysis/compare",
        json={
            "base_provenance": "analysis/analysis_provenance.json",
            "target_provenance": "analysis/analysis_provenance.json",
        },
    )
    assert_true(response.status_code == 200, "analysis compare API must return 200")
    comparison = response.json()
    assert_true((project_dir / comparison["relative_path"]).exists(), "analysis comparison JSON must exist")
    for field in ["parameters", "input_data_hash", "output_file_hashes", "runtime", "warnings", "limitations"]:
        assert_true(field in comparison["diffs"], f"analysis comparison must include {field}")


def assert_audit_and_run_history(client: TestClient, project_dir: Path) -> None:
    audit_response = client.get("/api/projects/demo_project/audit")
    assert_true(audit_response.status_code == 200, "audit API must return 200")
    audit_entries = audit_response.json()
    assert_true(audit_entries, "audit log must be non-empty")
    latest = audit_entries[-1]
    for field in ["event_category", "risk_level", "entity_type", "entity_id"]:
        assert_true(latest.get(field), f"new audit entry must include {field}")

    verify_response = client.get("/api/projects/demo_project/audit/verify")
    assert_true(verify_response.status_code == 200, "audit verify API must return 200")
    assert_true(verify_response.json()["valid"] is True, "audit hash chain must remain valid")

    run_history = read_json(project_dir / "runs" / "run_history.json")
    assert_true(isinstance(run_history, dict) and isinstance(run_history.get("runs"), list), "run_history must be object with runs")
    assert_true(run_history["runs"], "run_history runs must be non-empty")
    latest_run = run_history["runs"][-1]
    for field in ["failure_diagnostics", "recoverable", "retry_hint"]:
        assert_true(field in latest_run, f"run history entry must include {field}")


def assert_frontend_markers() -> None:
    files = [
        "apps/web/components/RevisionLineDiffPanel.tsx",
        "apps/web/components/LiteratureMetadataDiffPanel.tsx",
        "apps/web/components/LiteratureMetadataBatchPanel.tsx",
        "apps/web/components/PDFQualityReportPanel.tsx",
        "apps/web/components/AnalysisComparePanel.tsx",
    ]
    for relative_path in files:
        assert_true((ROOT / relative_path).exists(), f"{relative_path} must exist")
    api_text = (ROOT / "apps" / "web" / "lib" / "api.ts").read_text(encoding="utf-8")
    for marker in [
        "mockRevisionLineDiffs",
        "mockLiteratureMetadataDiff",
        "mockLiteratureMetadataBatch",
        "mockPDFQualityReport",
        "mockAnalysisComparisons",
    ]:
        assert_true(marker in api_text, f"frontend mock data must include {marker}")
    npm_executable = shutil.which("npm") or shutil.which("npm.cmd")
    assert_true(npm_executable is not None, "npm executable must be available for frontend typecheck")
    subprocess.run(
        [npm_executable, "run", "typecheck"],
        cwd=ROOT / "apps" / "web",
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def main() -> None:
    run_quietly(validate_v01)
    run_quietly(validate_v02)
    run_quietly(validate_v03)
    run_quietly(validate_v04)
    run_quietly(validate_v05)
    run_quietly(validate_v06)
    run_quietly(validate_v07)

    run_quietly(seed_demo)
    response = run_quietly(lambda: workflow_service.run_workflow("demo_project"))
    assert_true(response.workflow_status == "completed", "workflow must complete")

    project_dir = storage_service.project_dir("demo_project")
    assert_true(project_dir.exists(), "demo_project must exist")
    clean_v08_outputs(project_dir)
    assert_true((ROOT / "docs" / "v0.8_acceptance_criteria.md").exists(), "v0.8 acceptance criteria document must exist")

    client = TestClient(app)
    version = create_version_for_revision_diff(client, project_dir)
    assert_revision_line_diff(client, project_dir, version)
    assert_metadata_reports(client, project_dir)
    assert_pdf_quality_report(client, project_dir)
    assert_analysis_comparison(client, project_dir)
    assert_audit_and_run_history(client, project_dir)
    assert_frontend_markers()

    print("ResearchAgent v0.8 validation passed.")


if __name__ == "__main__":
    main()
