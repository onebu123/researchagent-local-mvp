from __future__ import annotations

from pathlib import Path

from app.tools.bibtex_generator import generate_bibtex, read_bibtex
from v12_helpers import base_literature_entry, write_v12_project


def test_bibtex_formal_entries_require_reference_approval(tmp_path: Path) -> None:
    write_v12_project(
        tmp_path,
        [
            base_literature_entry(
                title="Approved BibTeX Reference",
                metadata_status="verified",
                human_verified=True,
                reference_verification_status="approved",
                reference_verification_id="ref_verify_0001",
            ),
            base_literature_entry(
                literature_id="lit_002",
                title="Verified But Not Approved",
                metadata_status="verified",
                human_verified=True,
            ),
        ],
    )

    report = generate_bibtex(tmp_path, "tmp_project")
    payload = read_bibtex(tmp_path, "tmp_project")

    assert report["formal_entries"] == 1
    assert report["approved_entries"] == 1
    assert report["candidate_records"] == 1
    assert "Approved BibTeX Reference" in payload["bibtex"]
    assert "Verified But Not Approved" in payload["bibtex"]
    assert "@misc{lit_001" in payload["bibtex"]
    assert "@misc{lit_002" not in payload["bibtex"]
