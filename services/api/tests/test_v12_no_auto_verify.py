from __future__ import annotations

import json
from pathlib import Path

from app.tools.reference_approval import record_reference_approval
from app.tools.reference_verification import run_reference_verification
from v12_helpers import base_literature_entry, write_v12_project


def test_verification_and_default_approval_never_auto_verify_or_apply(tmp_path: Path) -> None:
    index_path = write_v12_project(tmp_path, [base_literature_entry()])
    verification = run_reference_verification(tmp_path, "tmp_project")
    after_verification = json.loads(index_path.read_text(encoding="utf-8"))[0]

    assert after_verification["metadata_status"] == "placeholder"
    assert after_verification["human_verified"] is False
    assert "reference_verification_status" not in after_verification

    record_reference_approval(
        tmp_path,
        "tmp_project",
        verification["results"][0]["verification_id"],
        "approved",
        reason="approval captured without apply",
    )
    after_approval = json.loads(index_path.read_text(encoding="utf-8"))[0]

    assert after_approval["metadata_status"] == "placeholder"
    assert after_approval["human_verified"] is False
    assert "reference_verification_status" not in after_approval
