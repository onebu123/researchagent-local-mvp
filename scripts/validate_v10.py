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
from scripts.create_failure_fixture import create_failure_fixture
from scripts.seed_demo import main as seed_demo
from scripts.validate_v08 import create_version_for_revision_diff
from scripts.validate_v09 import main as validate_v09


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


def clean_v10_outputs(project_dir: Path) -> None:
    for relative_path in [
        "provenance/evidence_claim_reviews.jsonl",
        "provenance/evidence_claim_review_summary.json",
        "reviews/reviewer_closure_summary.json",
        "literature/pdf_page_text_previews.json",
        "analysis/analysis_timeline.json",
        "trust/trust_summary.json",
        "trust/v1_readiness_report.json",
    ]:
        path = (project_dir / relative_path).resolve()
        assert_true(project_dir.resolve() in path.parents, f"cleanup escaped project: {relative_path}")
        path.unlink(missing_ok=True)
    for path in (project_dir / "literature").glob("metadata_revert_preview_*.json"):
        resolved = path.resolve()
        assert_true(project_dir.resolve() in resolved.parents, f"cleanup escaped project: {path}")
        resolved.unlink(missing_ok=True)


def assert_evidence_claim_review(client: TestClient, project_dir: Path) -> None:
    evidence_path = project_dir / "provenance" / "evidence.json"
    before_hash = sha256_file(evidence_path)
    response = client.post(
        "/api/projects/demo_project/evidence/claims/claim_001/review",
        json={"human_status": "supported", "reason": "validate_v10 claim review"},
    )
    assert_true(response.status_code == 200, "evidence claim review API must return 200")
    payload = response.json()
    assert_true(payload["evidence_modified"] is False, "evidence review must not modify evidence.json")
    assert_true(payload["summary"]["summary"]["reviewed"] >= 1, "evidence review summary must count reviewed claims")
    assert_true((project_dir / "provenance" / "evidence_claim_reviews.jsonl").exists(), "evidence claim reviews JSONL must exist")
    assert_true((project_dir / "provenance" / "evidence_claim_review_summary.json").exists(), "evidence claim review summary must exist")
    assert_true(sha256_file(evidence_path) == before_hash, "evidence review must preserve evidence.json bytes")

    invalid = client.post(
        "/api/projects/demo_project/evidence/claims/claim_001/review",
        json={"human_status": "auto_supported", "reason": "invalid"},
    )
    assert_true(invalid.status_code == 422, "invalid evidence human_status must return 422")


def assert_metadata_revert_preview(client: TestClient, project_dir: Path) -> None:
    index_path = project_dir / "literature" / "literature_index.json"
    original_index = index_path.read_text(encoding="utf-8")
    literature = read_json(index_path)
    assert_true(isinstance(literature, list) and literature, "literature index must be non-empty")
    literature_id = literature[0]["literature_id"]
    patch_response = client.patch(
        f"/api/projects/demo_project/literature/{literature_id}",
        json={
            "title": "validate_v10 metadata revert preview marker",
            "authors": [],
            "year": None,
            "doi": None,
            "journal": None,
            "metadata_status": "placeholder",
            "human_verified": False,
        },
    )
    assert_true(patch_response.status_code == 200, "literature patch API must return 200")
    history_response = client.get(f"/api/projects/demo_project/literature/{literature_id}/history")
    assert_true(history_response.status_code == 200, "literature history API must return 200")
    history_id = history_response.json()[-1]["history_id"]
    before_preview = index_path.read_text(encoding="utf-8")
    preview_response = client.post(
        f"/api/projects/demo_project/literature/{literature_id}/metadata/revert-preview",
        json={"field": "title", "source_history_id": history_id},
    )
    assert_true(preview_response.status_code == 200, "metadata revert preview API must return 200")
    preview = preview_response.json()
    assert_true(preview["applied"] is False, "metadata revert preview must not apply changes")
    assert_true(preview["literature_index_modified"] is False, "metadata revert preview must not modify index")
    assert_true((project_dir / preview["relative_path"]).exists(), "metadata revert preview file must exist")
    assert_true(index_path.read_text(encoding="utf-8") == before_preview, "metadata revert preview must preserve index")
    index_path.write_text(original_index, encoding="utf-8")


def assert_pdf_page_text_preview(client: TestClient, project_dir: Path) -> None:
    response = client.get("/api/projects/demo_project/literature/pdf-page-text-preview")
    assert_true(response.status_code == 200, "PDF page text preview API must return 200")
    payload = response.json()
    assert_true((project_dir / "literature" / "pdf_page_text_previews.json").exists(), "PDF page text preview JSON must exist")
    assert_true(payload["summary"]["ocr_attempted"] is False, "PDF text preview must not attempt OCR")
    assert_true(payload["pages"], "PDF text preview must include at least one page")
    first_page = payload["pages"][0]
    assert_true("text_preview" in first_page, "PDF text preview page must include text_preview")
    traversal = client.get(
        "/api/projects/demo_project/literature/pdf-page-text-preview",
        params={"source_file": "../secret.pdf"},
    )
    assert_true(traversal.status_code == 400, "PDF text preview path traversal must be rejected")


def assert_revision_closure(client: TestClient, project_dir: Path) -> None:
    version = create_version_for_revision_diff(client, project_dir)
    diff_response = client.post(
        "/api/projects/demo_project/manuscript/revision-diffs/generate",
        json={"base_file": "manuscript/draft.md", "target_file": version["file"]},
    )
    assert_true(diff_response.status_code == 200, "revision diff API must return 200")
    diff = diff_response.json()
    assert_true(diff["changes"], "revision diff must include changes")
    change = diff["changes"][0]
    review_response = client.post(
        "/api/projects/demo_project/manuscript/"
        f"revision-diffs/{diff['revision_diff_id']}/changes/{change['change_id']}/review",
        json={"human_status": "accepted", "reason": "validate_v10 closure"},
    )
    assert_true(review_response.status_code == 200, "revision diff review API must return 200")
    closure_response = client.get("/api/projects/demo_project/review/closure-summary")
    assert_true(closure_response.status_code == 200, "review closure API must return 200")
    closure = closure_response.json()
    assert_true((project_dir / "reviews" / "reviewer_closure_summary.json").exists(), "reviewer closure summary must exist")
    assert_true(closure["summary"]["closed"] >= 1, "at least one reviewer issue must be closed by accepted diff review")
    assert_true("workflow closure only" in json.dumps(closure, ensure_ascii=False), "closure summary must include local workflow caveat")


def assert_failure_fixture_and_timeline(client: TestClient, project_dir: Path) -> None:
    fixture = create_failure_fixture("demo_project")
    assert_true(fixture["is_fixture"] is True, "failure fixture must be marked is_fixture")
    compare_response = client.post(
        "/api/projects/demo_project/analysis/compare",
        json={
            "base_provenance": "analysis/analysis_provenance.json",
            "target_provenance": "analysis/analysis_provenance.json",
        },
    )
    assert_true(compare_response.status_code == 200, "analysis compare API must return 200")
    timeline_response = client.get("/api/projects/demo_project/analysis/timeline/enhanced")
    assert_true(timeline_response.status_code == 200, "enhanced analysis timeline API must return 200")
    timeline = timeline_response.json()
    assert_true(timeline["change_summary"]["failed_runs"] >= 1, "timeline must count failed runs")
    assert_true(timeline["failed_run_diagnostics"], "timeline must include failed run diagnostics")
    assert_true(any(item["is_fixture"] for item in timeline["failed_run_diagnostics"]), "timeline must include fixture diagnostic")
    assert_true((project_dir / "analysis" / "analysis_timeline.json").exists(), "analysis timeline JSON must exist")


def assert_trust_and_readiness(client: TestClient, project_dir: Path) -> None:
    trust_response = client.get("/api/projects/demo_project/trust/summary")
    assert_true(trust_response.status_code == 200, "trust summary API must return 200")
    trust = trust_response.json()
    assert_true((project_dir / "trust" / "trust_summary.json").exists(), "trust summary JSON must exist")
    assert_true("overall_status" in trust, "trust summary must include overall_status")
    assert_true("blocking_issues" in trust, "trust summary must include blocking issues")

    readiness_response = client.get("/api/projects/demo_project/trust/readiness-report")
    assert_true(readiness_response.status_code == 200, "readiness report API must return 200")
    readiness = readiness_response.json()
    assert_true((project_dir / "trust" / "v1_readiness_report.json").exists(), "v1 readiness report JSON must exist")
    assert_true(readiness["production_gaps"], "readiness report must list production gaps")
    assert_true("production_ready" not in readiness["readiness_level"], "readiness level must not claim production readiness")


def assert_failure_boundaries(client: TestClient) -> None:
    missing_project_responses = [
        client.get("/api/projects/missing_project/trust/summary"),
        client.get("/api/projects/missing_project/review/closure-summary"),
        client.get("/api/projects/missing_project/literature/pdf-page-text-preview"),
        client.get("/api/projects/missing_project/analysis/timeline/enhanced"),
        client.get("/api/projects/missing_project/trust/readiness-report"),
    ]
    assert_true(all(response.status_code == 404 for response in missing_project_responses), "v0.10 missing project endpoints must return 404")

    missing_claim = client.post(
        "/api/projects/demo_project/evidence/claims/claim_999/review",
        json={"human_status": "supported", "reason": "missing"},
    )
    assert_true(missing_claim.status_code == 404, "missing evidence claim must return 404")


def assert_frontend_markers() -> None:
    files = [
        "apps/web/components/EvidenceClaimReviewPanel.tsx",
        "apps/web/components/GlobalTrustDashboard.tsx",
        "apps/web/components/ReviewerClosurePanel.tsx",
        "apps/web/components/MetadataRevertPreviewPanel.tsx",
        "apps/web/components/PDFPageTextPreviewPanel.tsx",
        "apps/web/components/ReadinessReportPanel.tsx",
        "apps/web/e2e/v10-trust-readiness.spec.ts",
    ]
    for relative_path in files:
        assert_true((ROOT / relative_path).exists(), f"{relative_path} must exist")
    api_text = (ROOT / "apps" / "web" / "lib" / "api.ts").read_text(encoding="utf-8")
    for marker in [
        "mockEvidenceClaimReviews",
        "mockTrustSummary",
        "mockReviewerClosureSummary",
        "mockMetadataRevertPreview",
        "mockPDFPageTextPreview",
        "mockReadinessReport",
    ]:
        assert_true(marker in api_text, f"frontend mock data must include {marker}")
    page_text = (ROOT / "apps" / "web" / "app" / "page.tsx").read_text(encoding="utf-8")
    for marker in [
        "Evidence Claim Review",
        "Global Trust Dashboard",
        "Reviewer Closure",
        "Metadata Revert Preview",
        "PDF Page Text Preview",
        "v1.0 Readiness",
    ]:
        assert_true(marker in page_text, f"dashboard must include {marker}")
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
    run_quietly(validate_v09)
    run_quietly(seed_demo)
    response = run_quietly(lambda: workflow_service.run_workflow("demo_project"))
    assert_true(response.workflow_status == "completed", "workflow must complete")

    project_dir = storage_service.project_dir("demo_project")
    assert_true(project_dir.exists(), "demo_project must exist")
    clean_v10_outputs(project_dir)
    assert_true(
        (ROOT / "docs" / "v0.10_acceptance_criteria.md").exists(),
        "v0.10 acceptance criteria document must exist",
    )

    client = TestClient(app)
    assert_evidence_claim_review(client, project_dir)
    assert_metadata_revert_preview(client, project_dir)
    assert_pdf_page_text_preview(client, project_dir)
    assert_revision_closure(client, project_dir)
    assert_failure_fixture_and_timeline(client, project_dir)
    assert_trust_and_readiness(client, project_dir)
    assert_failure_boundaries(client)
    assert_frontend_markers()

    print("ResearchAgent v0.10 validation passed.")


if __name__ == "__main__":
    main()
