from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.services.storage_service import storage_service
from app.services.workflow_service import workflow_service
from scripts.seed_demo import main as seed_demo


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    seed_demo()
    project_dir = storage_service.project_dir("demo_project")
    assert_true(project_dir.exists(), "demo_project must exist")

    response = workflow_service.run_workflow("demo_project")
    assert_true(response.workflow_status == "completed", "workflow must complete")

    literature_index_path = project_dir / "literature" / "literature_index.json"
    assert_true(literature_index_path.exists(), "literature_index.json must exist")
    literature_index = read_json(literature_index_path)
    assert_true(isinstance(literature_index, list), "literature_index.json must be a list")

    pdf_entries = [
        entry
        for entry in literature_index
        if isinstance(entry, dict) and entry.get("source_type") == "pdf"
    ]
    for entry in pdf_entries:
        metadata_file = project_dir / str(entry.get("parse_metadata_file"))
        assert_true(metadata_file.exists(), f"parsed metadata missing: {metadata_file}")
        metadata = read_json(metadata_file)
        assert_true(
            isinstance(metadata, dict) and "parse_status" in metadata,
            "parsed metadata must include parse_status",
        )

    assert_true((project_dir / "analysis" / "result_summary.json").exists(), "result_summary missing")

    figure_path = project_dir / "figures" / "figure_provenance.json"
    assert_true(figure_path.exists(), "figure_provenance.json must exist")
    figure_records = read_json(figure_path)
    assert_true(isinstance(figure_records, list), "figure_provenance.json must be a list")
    assert_true(len(figure_records) >= 2, "figure_provenance.json must contain at least 2 records")
    for record in figure_records:
        assert_true(isinstance(record, dict), "figure record must be object")
        assert_true(bool(record.get("data_hash")), "figure record must include data_hash")
        assert_true(record.get("is_ai_generated") is False, "figure must have is_ai_generated=false")
        output_files = record.get("output_files")
        assert_true(isinstance(output_files, list) and output_files, "figure output_files missing")
        for output_file in output_files:
            assert_true((project_dir / output_file).exists(), f"figure output file missing: {output_file}")

    draft_path = project_dir / "manuscript" / "draft.md"
    assert_true(draft_path.exists(), "draft.md must exist")
    draft = draft_path.read_text(encoding="utf-8")
    assert_true("Evidence Checklist" in draft, "draft.md must include Evidence Checklist")
    assert_true("claim_" in draft, "draft.md must include claim_id")

    evidence_path = project_dir / "provenance" / "evidence.json"
    assert_true(evidence_path.exists(), "evidence.json must exist")
    evidence = read_json(evidence_path)
    assert_true(isinstance(evidence, list), "evidence.json must be a list")
    assert_true(len(evidence) >= 3, "evidence.json must contain at least 3 claims")
    assert_true(
        any(isinstance(claim, dict) and claim.get("evidence_type") == "figure" for claim in evidence),
        "evidence.json must contain at least one figure claim",
    )

    review_path = project_dir / "reviews" / "review_report.json"
    assert_true(review_path.exists(), "review_report.json must exist")
    review = read_json(review_path)
    assert_true(isinstance(review, dict), "review_report.json must be an object")
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

    print("ResearchAgent v0.2 validation passed.")


if __name__ == "__main__":
    main()
