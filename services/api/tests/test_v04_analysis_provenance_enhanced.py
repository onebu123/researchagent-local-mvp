from __future__ import annotations

import json
from pathlib import Path


def test_analysis_provenance_contains_v04_fields(demo_project_dir: Path) -> None:
    provenance = json.loads(
        (demo_project_dir / "analysis" / "analysis_provenance.json").read_text(encoding="utf-8")
    )

    assert provenance["parameters"]["analysis_mode"] == "descriptive_csv_profile"
    assert provenance["parameters"]["generate_correlation_matrix"] is True
    assert provenance["parameters"]["generate_figures"] is True
    assert provenance["parameters"]["missing_value_policy"] == "report_only"
    assert provenance["script_version"]["analysis_agent"] == "v0.4"
    assert provenance["script_version"]["csv_profile_tool"] == "v0.4"
    assert provenance["script_version"]["plotting_tool"] == "v0.4"
    assert provenance["random_seed"] == 42
    assert isinstance(provenance["output_file_hashes"], dict)

    for relative_path in provenance["generated_files"]:
        assert relative_path in provenance["output_file_hashes"]
        assert len(provenance["output_file_hashes"][relative_path]) == 64
        assert (demo_project_dir / relative_path).exists()


def test_analysis_provenance_limitations_protect_statistical_boundary(demo_project_dir: Path) -> None:
    provenance = json.loads(
        (demo_project_dir / "analysis" / "analysis_provenance.json").read_text(encoding="utf-8")
    )
    limitations = "\n".join(provenance["limitations"]).lower()

    assert "descriptive analysis only" in limitations
    assert "p-values" in limitations
    assert "causal inference" in limitations
