from __future__ import annotations

import json
from pathlib import Path

from app.tools.patch_safety import check_patch_item


def _project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "project"
    (project_dir / "manuscript").mkdir(parents=True)
    (project_dir / "provenance").mkdir(parents=True)
    (project_dir / "manuscript" / "draft.md").write_text(
        "# Results\n\nThe sample showed 5 mg yield for claim_001.\n",
        encoding="utf-8",
    )
    (project_dir / "provenance" / "evidence.json").write_text(
        json.dumps([{"claim_id": "claim_001"}]),
        encoding="utf-8",
    )
    return project_dir


def _item(after: str) -> dict:
    return {
        "before": "The sample showed 5 mg yield for claim_001.",
        "after": after,
        "related_claim_id": "claim_001",
    }


def test_patch_safety_accepts_conservative_rewrite(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)

    result = check_patch_item(
        project_dir,
        _item("The sample showed 5 mg yield for claim_001 and remains descriptive."),
    )

    assert result["safe"] is True
    assert result["blocked_reasons"] == []


def test_patch_safety_blocks_p_values_doi_and_strong_terms(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)

    p_value = check_patch_item(project_dir, _item("The sample showed 5 mg yield, p < 0.05."))
    doi = check_patch_item(project_dir, _item("The sample showed 5 mg yield, doi:10.1234/demo."))
    strong = check_patch_item(project_dir, _item("The sample significantly improved 5 mg yield."))

    assert p_value["safe"] is False
    assert any("p-value" in reason for reason in p_value["blocked_reasons"])
    assert doi["safe"] is False
    assert any("DOI" in reason for reason in doi["blocked_reasons"])
    assert strong["safe"] is False
    assert any("strong conclusion" in reason for reason in strong["blocked_reasons"])


def test_patch_safety_blocks_number_unit_and_missing_claim_changes(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)

    changed_number = check_patch_item(project_dir, _item("The sample showed 6 mg yield."))
    changed_unit = check_patch_item(project_dir, _item("The sample showed 5 g yield."))
    missing_claim = check_patch_item(
        project_dir,
        {
            "before": "The sample showed 5 mg yield for claim_001.",
            "after": "The sample showed 5 mg yield for claim_999.",
            "related_claim_id": "claim_999",
        },
    )

    assert changed_number["safe"] is False
    assert any("numbers" in reason for reason in changed_number["blocked_reasons"])
    assert changed_unit["safe"] is False
    assert any("units" in reason for reason in changed_unit["blocked_reasons"])
    assert missing_claim["safe"] is False
    assert any("related_claim_id" in reason for reason in missing_claim["blocked_reasons"])


def test_patch_safety_blocks_missing_before_text(tmp_path: Path) -> None:
    project_dir = _project(tmp_path)

    result = check_patch_item(
        project_dir,
        {
            "before": "This sentence is not in the manuscript.",
            "after": "This sentence remains descriptive.",
            "related_claim_id": "claim_001",
        },
    )

    assert result["safe"] is False
    assert any("before text" in reason for reason in result["blocked_reasons"])
