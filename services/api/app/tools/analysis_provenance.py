from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.tools.file_tools import relative_posix, write_json


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_analysis_provenance(
    project_dir: Path,
    csv_path: Path,
    stats: dict[str, Any],
    generated_demo_data: bool,
) -> dict[str, Any]:
    input_data_file = relative_posix(csv_path, project_dir)
    generated_files = [
        "analysis/result_summary.json",
        "analysis/processed_data.csv",
        "analysis/run_log.txt",
    ]
    output_file_hashes = {
        relative_path: sha256_file(project_dir / relative_path)
        for relative_path in generated_files
        if (project_dir / relative_path).exists()
    }
    provenance = {
        "analysis_id": "analysis_001",
        "input_data_file": input_data_file,
        "input_data_hash": sha256_file(csv_path) if csv_path.exists() else "",
        "analysis_function": "app.tools.csv_profile.profile_csv",
        "generated_files": generated_files,
        "parameters": {
            "analysis_mode": "descriptive_csv_profile",
            "generate_correlation_matrix": True,
            "generate_figures": True,
            "missing_value_policy": "report_only",
        },
        "script_version": {
            "analysis_agent": "v0.4",
            "csv_profile_tool": "v0.4",
            "plotting_tool": "v0.4",
        },
        "random_seed": 42,
        "random_seed_note": (
            "Used only for generated demo CSV data; uploaded CSV analysis is deterministic "
            "and does not sample rows."
        ),
        "output_file_hashes": output_file_hashes,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "python_version": sys.version.split()[0],
            "pandas_version": pd.__version__,
            "numpy_version": np.__version__,
        },
        "row_count": int(stats.get("row_count", 0)),
        "column_count": int(stats.get("column_count", 0)),
        "warnings": [],
        "limitations": [
            "ResearchAgent v0.4 performs descriptive analysis only.",
            "ResearchAgent v0.4 does not generate p-values or statistical significance claims.",
            "ResearchAgent v0.4 does not perform causal inference.",
            "Claims based on this analysis require human domain review before submission.",
        ],
        "is_demo_data": bool(generated_demo_data or stats.get("is_demo_data")),
    }
    write_json(project_dir / "analysis" / "analysis_provenance.json", provenance)
    return provenance
