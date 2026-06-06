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
from scripts.validate_v08 import create_version_for_revision_diff, main as validate_v08


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


def clean_v09_outputs(project_dir: Path) -> None:
    for relative_path in [
        "manuscript/revision_diffs/revision_diff_reviews.jsonl",
        "manuscript/revision_diffs/revision_diff_review_summary.json",
        "literature/metadata_review_actions.jsonl",
        "literature/metadata_review_summary.json",
        "literature/pdf_page_reviews.jsonl",
        "literature/pdf_page_review_summary.json",
        "analysis/analysis_timeline.json",
    ]:
        path = (project_dir / relative_path).resolve()
        assert_true(project_dir.resolve() in path.parents, f"cleanup escaped project: {relative_path}")
        path.unlink(missing_ok=True)


def create_revision_diff(client: TestClient, project_dir: Path) -> dict:
    version = create_version_for_revision_diff(client, project_dir)
    response = client.post(
        "/api/projects/demo_project/manuscript/revision-diffs/generate",
        json={"base_file": "manuscript/draft.md", "target_file": version["file"]},
    )
    assert_true(response.status_code == 200, "revision line diff API must return 200")
    diff = response.json()
    assert_true(diff["changes"], "revision diff must include at least one change")
    return diff


def assert_revision_diff_review(client: TestClient, project_dir: Path) -> None:
    draft_path = project_dir / "manuscript" / "draft.md"
    before_hash = sha256_file(draft_path)
    diff = create_revision_diff(client, project_dir)
    change = diff["changes"][0]
    response = client.post(
        "/api/projects/demo_project/manuscript/"
        f"revision-diffs/{diff['revision_diff_id']}/changes/{change['change_id']}/review",
        json={"human_status": "needs_evidence", "reason": "validate_v09 evidence check"},
    )
    assert_true(response.status_code == 200, "revision diff review API must return 200")
    payload = response.json()
    assert_true(payload["human_status"] == "needs_evidence", "revision diff review status must persist")
    assert_true(
        (project_dir / "manuscript" / "revision_diffs" / "revision_diff_reviews.jsonl").exists(),
        "revision_diff_reviews.jsonl must exist",
    )
    summary_path = project_dir / "manuscript" / "revision_diffs" / "revision_diff_review_summary.json"
    assert_true(summary_path.exists(), "revision_diff_review_summary.json must exist")
    summary = read_json(summary_path)
    assert_true(isinstance(summary, dict), "revision diff review summary must be object")
    assert_true(summary["summary"]["reviewed"] >= 1, "revision diff review summary must count reviewed changes")
    assert_true(sha256_file(draft_path) == before_hash, "revision diff review must not modify draft.md")


def assert_metadata_review_workflow(client: TestClient, project_dir: Path) -> None:
    index_path = project_dir / "literature" / "literature_index.json"
    original_index = index_path.read_text(encoding="utf-8")
    literature = read_json(index_path)
    assert_true(isinstance(literature, list) and literature, "literature index must be non-empty")
    literature_id = literature[0]["literature_id"]
    patch_response = client.patch(
        f"/api/projects/demo_project/literature/{literature_id}",
        json={
            "title": "validate_v09 metadata review marker",
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
    changes = [
        change
        for record in diff_response.json()["records"]
        if record["literature_id"] == literature_id
        for change in record["changes"]
        if change["field"] == "title"
    ]
    assert_true(bool(changes), "metadata diff must include title change")
    before_action = index_path.read_text(encoding="utf-8")
    action_response = client.post(
        f"/api/projects/demo_project/literature/{literature_id}/metadata-review",
        json={
            "field": "title",
            "action": "request_revert",
            "source_history_id": changes[-1]["source_history_id"],
            "reason": "validate_v09 requests revert suggestion",
        },
    )
    assert_true(action_response.status_code == 200, "metadata review action API must return 200")
    action = action_response.json()
    assert_true(action["literature_index_modified"] is False, "metadata review action must not modify index")
    assert_true(index_path.read_text(encoding="utf-8") == before_action, "metadata review action must not change index")
    assert_true(
        (project_dir / "literature" / "metadata_review_actions.jsonl").exists(),
        "metadata_review_actions.jsonl must exist",
    )
    assert_true(
        (project_dir / "literature" / "metadata_review_summary.json").exists(),
        "metadata_review_summary.json must exist",
    )
    index_path.write_text(original_index, encoding="utf-8")


def assert_pdf_page_review_workflow(client: TestClient, project_dir: Path) -> None:
    report_response = client.get("/api/projects/demo_project/literature/pdf-quality-report")
    assert_true(report_response.status_code == 200, "PDF quality report API must return 200")
    pdfs = report_response.json()["pdfs"]
    assert_true(bool(pdfs), "demo PDF quality report must include at least one PDF")
    source_file = pdfs[0]["source_file"]
    response = client.post(
        "/api/projects/demo_project/literature/pdf-page-review",
        json={
            "source_file": source_file,
            "page_number": 1,
            "human_status": "needs_ocr",
            "reason": "validate_v09 flags OCR reservation only",
        },
    )
    assert_true(response.status_code == 200, "PDF page review API must return 200")
    review = response.json()
    assert_true(review["ocr_attempted"] is False, "PDF page review must not run OCR")
    assert_true(
        (project_dir / "literature" / "pdf_page_reviews.jsonl").exists(),
        "pdf_page_reviews.jsonl must exist",
    )
    assert_true(
        (project_dir / "literature" / "pdf_page_review_summary.json").exists(),
        "pdf_page_review_summary.json must exist",
    )


def assert_analysis_timeline(client: TestClient, project_dir: Path) -> None:
    comparison_response = client.post(
        "/api/projects/demo_project/analysis/compare",
        json={
            "base_provenance": "analysis/analysis_provenance.json",
            "target_provenance": "analysis/analysis_provenance.json",
        },
    )
    assert_true(comparison_response.status_code == 200, "analysis compare API must return 200")
    comparison_id = comparison_response.json()["comparison_id"]
    timeline_response = client.get("/api/projects/demo_project/analysis/timeline")
    assert_true(timeline_response.status_code == 200, "analysis timeline API must return 200")
    timeline = timeline_response.json()
    assert_true((project_dir / "analysis" / "analysis_timeline.json").exists(), "analysis_timeline.json must exist")
    linked = [
        comparison["comparison_id"]
        for entry in timeline["timeline"]
        for comparison in entry.get("comparisons", [])
    ]
    unlinked = [comparison["comparison_id"] for comparison in timeline["unlinked_comparisons"]]
    assert_true(
        comparison_id in linked or comparison_id in unlinked,
        "analysis timeline must include generated comparison id",
    )
    assert_true(
        all(not str(entry.get("run_id", "")).startswith("fake_") for entry in timeline["timeline"]),
        "analysis timeline must not fabricate run ids",
    )


def assert_filtered_audit_export(client: TestClient, project_dir: Path) -> None:
    response = client.post(
        "/api/projects/demo_project/audit/filtered-export",
        json={"risk_level": "low"},
    )
    assert_true(response.status_code == 200, "filtered audit export API must return 200")
    export = response.json()
    export_path = project_dir / "audit" / "filtered_exports" / f"{export['export_id']}.json"
    report_path = project_dir / export["report_file"]
    assert_true(export_path.exists(), "filtered audit export JSON must exist")
    assert_true(report_path.exists(), "filtered audit markdown report must exist")
    serialized = json.dumps(export, ensure_ascii=False)
    report_text = report_path.read_text(encoding="utf-8")
    for text in [serialized, report_text]:
        assert_true("sk_live_" not in text, "filtered audit export must not contain secret key marker")
        assert_true("api_key" not in text.lower(), "filtered audit export must not contain API key marker")
        assert_true(":\\" not in text and ":/" not in text, "filtered audit export must not contain absolute paths")


def assert_failure_boundaries(client: TestClient) -> None:
    invalid_revision = client.post(
        "/api/projects/demo_project/manuscript/revision-diffs/revision_diff_999/changes/change_001/review",
        json={"human_status": "auto_accept", "reason": "invalid"},
    )
    assert_true(invalid_revision.status_code == 422, "invalid revision review status must return 422")

    invalid_metadata = client.post(
        "/api/projects/demo_project/literature/lit_001/metadata-review",
        json={
            "field": "title",
            "action": "auto_verify",
            "source_history_id": "lit_hist_001",
            "reason": "invalid",
        },
    )
    assert_true(invalid_metadata.status_code == 422, "invalid metadata action must return 422")

    invalid_pdf_path = client.post(
        "/api/projects/demo_project/literature/pdf-page-review",
        json={
            "source_file": "../secret.pdf",
            "page_number": 1,
            "human_status": "needs_ocr",
            "reason": "invalid",
        },
    )
    assert_true(invalid_pdf_path.status_code == 422, "PDF path traversal must return 422")

    missing_export = client.get(
        "/api/projects/demo_project/audit/filtered-exports/audit_filtered_export_999/report"
    )
    assert_true(missing_export.status_code == 404, "missing filtered audit report must return 404")


def assert_frontend_markers() -> None:
    files = [
        "apps/web/components/RevisionDiffReviewPanel.tsx",
        "apps/web/components/MetadataReviewWorkflowPanel.tsx",
        "apps/web/components/PDFPageReviewPanel.tsx",
        "apps/web/components/AnalysisTimelinePanel.tsx",
        "apps/web/components/AuditFilterExportPanel.tsx",
    ]
    for relative_path in files:
        assert_true((ROOT / relative_path).exists(), f"{relative_path} must exist")
    api_text = (ROOT / "apps" / "web" / "lib" / "api.ts").read_text(encoding="utf-8")
    for marker in [
        "mockRevisionDiffReviews",
        "mockMetadataReviewActions",
        "mockPDFPageReviews",
        "mockAnalysisTimeline",
        "mockAuditFilteredExports",
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
    run_quietly(validate_v08)

    run_quietly(seed_demo)
    response = run_quietly(lambda: workflow_service.run_workflow("demo_project"))
    assert_true(response.workflow_status == "completed", "workflow must complete")

    project_dir = storage_service.project_dir("demo_project")
    assert_true(project_dir.exists(), "demo_project must exist")
    clean_v09_outputs(project_dir)
    assert_true(
        (ROOT / "docs" / "v0.9_acceptance_criteria.md").exists(),
        "v0.9 acceptance criteria document must exist",
    )

    client = TestClient(app)
    assert_revision_diff_review(client, project_dir)
    assert_metadata_review_workflow(client, project_dir)
    assert_pdf_page_review_workflow(client, project_dir)
    assert_analysis_timeline(client, project_dir)
    assert_filtered_audit_export(client, project_dir)
    assert_failure_boundaries(client)
    assert_frontend_markers()

    print("ResearchAgent v0.9 validation passed.")


if __name__ == "__main__":
    main()
