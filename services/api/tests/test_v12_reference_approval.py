from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.tools.reference_approval import record_reference_approval
from app.tools.reference_verification import run_reference_verification
from v12_helpers import base_literature_entry, write_v12_project


def test_reference_approval_default_does_not_apply_to_literature_index(tmp_path: Path) -> None:
    index_path = write_v12_project(tmp_path, [base_literature_entry()])
    result = run_reference_verification(tmp_path, "tmp_project")["results"][0]
    before = index_path.read_text(encoding="utf-8")

    approval = record_reference_approval(
        tmp_path,
        "tmp_project",
        result["verification_id"],
        "approved",
        reason="human reviewed but not applied yet",
    )

    assert approval["decision"] == "approved"
    assert approval["apply_to_literature_index"] is False
    assert approval["literature_index_modified"] is False
    assert index_path.read_text(encoding="utf-8") == before


def test_reference_approval_explicit_apply_updates_index_history_and_audit(tmp_path: Path) -> None:
    index_path = write_v12_project(tmp_path, [base_literature_entry()])
    result = run_reference_verification(tmp_path, "tmp_project")["results"][0]

    approval = record_reference_approval(
        tmp_path,
        "tmp_project",
        result["verification_id"],
        "approved",
        reason="approved by human reviewer",
        apply_to_literature_index=True,
    )

    updated = json.loads(index_path.read_text(encoding="utf-8"))[0]
    assert approval["literature_index_modified"] is True
    assert updated["metadata_status"] == "verified"
    assert updated["human_verified"] is True
    assert updated["reference_verification_status"] == "approved"
    assert updated["reference_verification_id"] == result["verification_id"]
    assert (tmp_path / "literature" / "metadata_history.jsonl").exists()
    assert (tmp_path / "audit" / "audit_log.jsonl").exists()


def test_rejected_reference_approval_cannot_apply_to_index(tmp_path: Path) -> None:
    write_v12_project(tmp_path, [base_literature_entry()])
    result = run_reference_verification(tmp_path, "tmp_project")["results"][0]

    with pytest.raises(ValueError, match="Only approved"):
        record_reference_approval(
            tmp_path,
            "tmp_project",
            result["verification_id"],
            "rejected",
            apply_to_literature_index=True,
        )
