from __future__ import annotations

import json
from pathlib import Path

from app.tools.manuscript_references import generate_manuscript_references, read_references_preview
from app.tools.reference_approval import record_reference_approval
from app.tools.reference_verification import run_reference_verification
from v12_helpers import base_literature_entry, write_v12_project


def test_manuscript_references_only_include_approved_verified_records(tmp_path: Path) -> None:
    write_v12_project(
        tmp_path,
        [
            base_literature_entry(
                title="Approved Reference",
                metadata_status="verified",
                human_verified=True,
                reference_verification_status="approved",
                reference_verification_id="ref_verify_0001",
            ),
            base_literature_entry(literature_id="lit_002", title="Candidate Reference"),
        ],
    )
    run_reference_verification(tmp_path, "tmp_project", literature_id="lit_002")

    status = generate_manuscript_references(tmp_path, "tmp_project")
    preview = read_references_preview(tmp_path, "tmp_project")["content"]

    assert [record["title"] for record in status["verified_references"]] == ["Approved Reference"]
    assert status["candidate_references"][0]["title"] == "Candidate Reference"
    assert "Approved Reference" in preview
    assert "Candidate Reference" not in preview


def test_latest_rejected_approval_excludes_even_previously_approved_index_record(tmp_path: Path) -> None:
    write_v12_project(
        tmp_path,
        [
            base_literature_entry(
                metadata_status="verified",
                human_verified=True,
                reference_verification_status="approved",
                reference_verification_id="ref_verify_0001",
            )
        ],
    )
    result = run_reference_verification(tmp_path, "tmp_project")["results"][0]
    record_reference_approval(tmp_path, "tmp_project", result["verification_id"], "rejected")

    status = generate_manuscript_references(tmp_path, "tmp_project")

    assert status["verified_references"] == []
    assert status["placeholder_records"][0]["warning"] == "Latest reference approval decision is rejected."
