from __future__ import annotations

import contextlib
import io
import json
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


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def run_quietly(func) -> object:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        return func()


def main() -> None:
    run_quietly(validate_v01)
    run_quietly(validate_v02)
    run_quietly(seed_demo)
    response = run_quietly(lambda: workflow_service.run_workflow("demo_project"))
    assert_true(response.workflow_status == "completed", "workflow must complete")

    project_dir = storage_service.project_dir("demo_project")
    assert_true(project_dir.exists(), "demo_project must exist")

    claim_alignment_path = project_dir / "provenance" / "claim_alignment.json"
    assert_true(claim_alignment_path.exists(), "claim_alignment.json must exist")
    claim_alignment = read_json(claim_alignment_path)
    assert_true(isinstance(claim_alignment, dict), "claim_alignment.json must be an object")
    aligned_claims = claim_alignment.get("aligned_claims")
    assert_true(isinstance(aligned_claims, list), "aligned_claims must be a list")
    assert_true(
        any(isinstance(item, dict) and item.get("matched_claim_id") for item in aligned_claims),
        "claim_alignment must include at least one matched claim",
    )
    assert_true(
        any(isinstance(item, dict) and item.get("section") == "Results" for item in aligned_claims),
        "claim_alignment must check at least one Results sentence",
    )

    review_path = project_dir / "reviews" / "review_report.json"
    assert_true(review_path.exists(), "review_report.json must exist")
    review = read_json(review_path)
    assert_true(isinstance(review, dict), "review_report.json must be an object")
    assert_true("sentence_issues" in review, "review_report.json must include sentence_issues")
    assert_true(isinstance(review["sentence_issues"], list), "sentence_issues must be a list")
    for field in [
        "overall_decision",
        "evidence_issues",
        "figure_issues",
        "citation_issues",
        "overclaims",
        "consistency_checks",
    ]:
        assert_true(field in review, f"review_report.json must include {field}")
    assert_true(
        review.get("overall_decision") in {"major_revision", "reject"},
        "demo review decision must be major_revision or reject",
    )

    literature_index_path = project_dir / "literature" / "literature_index.json"
    assert_true(literature_index_path.exists(), "literature_index.json must exist")
    literature_index = read_json(literature_index_path)
    assert_true(isinstance(literature_index, list), "literature_index.json must be a list")
    assert_true(literature_index, "literature_index.json must not be empty")
    for entry in literature_index:
        assert_true(isinstance(entry, dict), "literature entry must be an object")
        assert_true("metadata_status" in entry, "literature entry must include metadata_status")
        assert_true("human_verified" in entry, "literature entry must include human_verified")

    pdf_entries = [
        entry
        for entry in literature_index
        if isinstance(entry, dict) and entry.get("source_type") == "pdf"
    ]
    for entry in pdf_entries:
        metadata_file = project_dir / str(entry.get("parse_metadata_file"))
        assert_true(metadata_file.exists(), f"PDF parse metadata missing: {metadata_file}")
        metadata = read_json(metadata_file)
        assert_true(isinstance(metadata, dict), "PDF metadata must be an object")
        for field in ["quality_score", "quality_label", "needs_manual_review"]:
            assert_true(field in metadata, f"PDF metadata must include {field}")

    analysis_provenance_path = project_dir / "analysis" / "analysis_provenance.json"
    assert_true(analysis_provenance_path.exists(), "analysis_provenance.json must exist")
    analysis_provenance = read_json(analysis_provenance_path)
    assert_true(isinstance(analysis_provenance, dict), "analysis_provenance must be object")
    for field in ["input_data_hash", "analysis_function", "generated_files", "runtime"]:
        assert_true(analysis_provenance.get(field), f"analysis_provenance must include {field}")

    draft_path = project_dir / "manuscript" / "draft.md"
    assert_true(draft_path.exists(), "draft.md must exist")
    draft = draft_path.read_text(encoding="utf-8")
    assert_true("Evidence Checklist" in draft, "draft.md must include Evidence Checklist")
    assert_true("claim_" in draft, "draft.md must include claim_id")

    figure_path = project_dir / "figures" / "figure_provenance.json"
    assert_true(figure_path.exists(), "figure_provenance.json must exist")
    figures = read_json(figure_path)
    assert_true(isinstance(figures, list) and figures, "figure_provenance must be a non-empty list")
    for figure in figures:
        assert_true(isinstance(figure, dict), "figure record must be object")
        assert_true(bool(figure.get("data_hash")), "figure record must include data_hash")

    evidence_path = project_dir / "provenance" / "evidence.json"
    assert_true(evidence_path.exists(), "evidence.json must exist")
    evidence = read_json(evidence_path)
    assert_true(isinstance(evidence, list), "evidence.json must be a list")
    analysis_claims = [
        claim
        for claim in evidence
        if isinstance(claim, dict)
        and claim.get("evidence_type") in {"analysis", "analysis_summary"}
    ]
    assert_true(analysis_claims, "evidence.json must include an analysis claim")
    assert_true(
        all(
            claim.get("analysis_provenance_file") == "analysis/analysis_provenance.json"
            for claim in analysis_claims
        ),
        "analysis evidence claim must bind analysis_provenance.json",
    )

    client = TestClient(app)
    for endpoint in [
        "/api/projects/demo_project/claim-alignment",
        "/api/projects/demo_project/analysis/provenance",
        "/api/projects/demo_project/literature",
        "/api/projects/demo_project/review/sentence-issues",
    ]:
        api_response = client.get(endpoint)
        assert_true(api_response.status_code == 200, f"API must be readable: {endpoint}")

    original_index = literature_index_path.read_text(encoding="utf-8")
    first_literature_id = literature_index[0]["literature_id"]
    patch_response = client.patch(
        f"/api/projects/demo_project/literature/{first_literature_id}",
        json={
            "title": "v0.3 validation metadata marker",
            "authors": [],
            "year": None,
            "doi": None,
            "journal": "v0.3 validation journal marker",
            "metadata_status": "placeholder",
            "human_verified": False,
        },
    )
    assert_true(patch_response.status_code == 200, "literature PATCH API must accept valid input")
    patched_index = read_json(literature_index_path)
    assert_true(
        any(
            isinstance(entry, dict)
            and entry.get("literature_id") == first_literature_id
            and entry.get("journal") == "v0.3 validation journal marker"
            for entry in patched_index
        ),
        "literature PATCH must update literature_index.json",
    )
    literature_index_path.write_text(original_index, encoding="utf-8")

    print("ResearchAgent v0.3 validation passed.")


if __name__ == "__main__":
    main()
