from __future__ import annotations

from pathlib import Path

from app.tools.literature_metadata_lookup import run_metadata_lookup


def test_metadata_lookup_mock_does_not_modify_literature_index(demo_project_dir: Path) -> None:
    index_path = demo_project_dir / "literature" / "literature_index.json"
    before = index_path.read_text(encoding="utf-8")

    payload = run_metadata_lookup(demo_project_dir, "demo_project", provider="mock_fixture")

    assert payload["summary"]["provider"] == "mock_fixture"
    assert payload["summary"]["literature_index_modified"] is False
    assert index_path.read_text(encoding="utf-8") == before
    assert all(record["human_verification_required"] for record in payload["results"])
    assert all("10." not in str(record.get("candidates", [])) for record in payload["results"])
