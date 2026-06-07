from __future__ import annotations

import json
from pathlib import Path

from app.tools.citation_grounding import generate_citation_grounding_report
from v12_helpers import base_literature_entry, write_v12_project


def test_citation_grounding_binds_claims_to_local_passages(tmp_path: Path) -> None:
    source_text = (
        "Adaptive retrieval improves local citation grounding. "
        "Adaptive retrieval reduces latency by 35 percent in the local benchmark."
    )
    write_v12_project(
        tmp_path,
        [
            base_literature_entry(
                metadata_status="verified",
                human_verified=True,
                reference_verification_status="approved",
            )
        ],
        source_text=source_text,
    )
    (tmp_path / "provenance").mkdir()
    (tmp_path / "provenance" / "evidence.json").write_text(
        json.dumps(
            [
                {
                    "claim_id": "claim_001",
                    "claim": "Adaptive retrieval reduces latency by 35 percent.",
                }
            ]
        ),
        encoding="utf-8",
    )

    report = generate_citation_grounding_report(tmp_path, "tmp_project")
    item = report["items"][0]

    assert item["candidate_chunk_id"]
    assert item["literature_id"] == "lit_001"
    assert item["signals"]["number_consistency"] == "match"
    assert item["signals"]["metadata_verified"] is True
    assert item["grounding_strength"] in {"strong", "moderate"}


def test_citation_grounding_caps_placeholder_metadata(tmp_path: Path) -> None:
    write_v12_project(
        tmp_path,
        [base_literature_entry()],
        source_text="Adaptive retrieval reduces latency by 35 percent in the local benchmark.",
    )
    (tmp_path / "provenance").mkdir()
    (tmp_path / "provenance" / "evidence.json").write_text(
        json.dumps([{"claim_id": "claim_001", "claim": "Adaptive retrieval reduces latency by 35 percent."}]),
        encoding="utf-8",
    )

    report = generate_citation_grounding_report(tmp_path, "tmp_project")

    assert report["items"][0]["signals"]["metadata_verified"] is False
    assert report["items"][0]["grounding_strength"] != "strong"
    assert report["items"][0]["requires_human_review"] is True
