from __future__ import annotations

import json
from pathlib import Path


def test_figure_provenance_has_hash_and_existing_outputs(demo_project_dir: Path) -> None:
    records = json.loads(
        (demo_project_dir / "figures" / "figure_provenance.json").read_text(encoding="utf-8")
    )

    assert len(records) >= 2
    for record in records:
        assert record["data_hash"]
        assert record["is_ai_generated"] is False
        assert record["is_experimental_result"] is True
        assert record["source_data"]
        assert (demo_project_dir / record["source_data"]).exists()
        assert record["output_files"]
        for output_file in record["output_files"]:
            assert (demo_project_dir / output_file).exists()
