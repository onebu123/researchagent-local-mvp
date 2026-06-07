from __future__ import annotations

import json
from pathlib import Path

from app.tools.bibtex_generator import generate_bibtex, read_bibtex


def test_bibtex_skips_unverified_demo_records(demo_project_dir: Path) -> None:
    report = generate_bibtex(demo_project_dir, "demo_project")
    bibtex = (demo_project_dir / "literature" / "references.bib").read_text(encoding="utf-8")

    assert report["formal_entries"] == 0
    assert report["skipped_records"] >= 1
    assert "@misc" not in bibtex
    assert "Skipped lit_" in bibtex


def test_bibtex_writes_verified_human_record_without_fabricating_missing_fields(tmp_path: Path) -> None:
    literature_dir = tmp_path / "literature"
    literature_dir.mkdir()
    (literature_dir / "literature_index.json").write_text(
        json.dumps(
            [
                {
                    "literature_id": "lit_001",
                    "source_file": "literature/verified.md",
                    "title": "Verified Local Paper",
                    "authors": ["Ada Lovelace"],
                    "year": 1843,
                    "doi": None,
                    "journal": None,
                    "source_type": "markdown",
                    "parsed_text_file": "literature/verified.md",
                    "metadata_status": "verified",
                    "human_verified": True,
                    "reference_verification_status": "approved",
                    "reference_verification_id": "ref_verify_0001",
                }
            ]
        ),
        encoding="utf-8",
    )

    report = generate_bibtex(tmp_path, "tmp_project")
    payload = read_bibtex(tmp_path, "tmp_project")

    assert report["formal_entries"] == 1
    assert "@misc" in payload["bibtex"]
    assert "author = {Ada Lovelace}" in payload["bibtex"]
    assert "doi =" not in payload["bibtex"]
    assert "journal =" not in payload["bibtex"]
