from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.tools.file_tools import ensure_dir, write_json, write_text


def generate_demo_csv(path: Path, rows: int = 60) -> Path:
    ensure_dir(path.parent)
    rng = np.random.default_rng(42)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["sample_id", "temperature", "concentration", "efficiency", "stability", "band_gap"]
        )
        for index in range(rows):
            temperature = 300 + index * 2 + rng.normal(0, 3)
            concentration = 0.08 + (index % 10) * 0.015
            efficiency = 14.5 + 0.045 * temperature - 18 * concentration + rng.normal(0, 0.8)
            stability = 82 - 0.025 * temperature + 14 * concentration + rng.normal(0, 1.4)
            band_gap = 1.48 + 0.002 * (temperature - 300) - 0.08 * concentration
            writer.writerow(
                [
                    f"S{index + 1:03d}",
                    round(float(temperature), 3),
                    round(float(concentration), 4),
                    round(float(efficiency), 3),
                    round(float(stability), 3),
                    round(float(band_gap), 4),
                ]
            )
    return path


def profile_csv(csv_path: Path, output_dir: Path) -> dict[str, Any]:
    ensure_dir(output_dir)
    df = pd.read_csv(csv_path)
    numeric_df = df.select_dtypes(include="number")
    stats: dict[str, Any] = {
        "source_data": csv_path.name,
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "columns": list(df.columns),
        "numeric_columns": list(numeric_df.columns),
        "missing_values": {column: int(value) for column, value in df.isna().sum().items()},
        "descriptive_statistics": {},
        "correlation_matrix": {},
        "is_demo_data": "demo" in csv_path.name.lower(),
    }

    for column in numeric_df.columns:
        series = numeric_df[column]
        stats["descriptive_statistics"][column] = {
            "mean": round(float(series.mean()), 6),
            "std": round(float(series.std(ddof=1)), 6),
            "min": round(float(series.min()), 6),
            "max": round(float(series.max()), 6),
        }

    if not numeric_df.empty:
        corr = numeric_df.corr(numeric_only=True).fillna(0)
        stats["correlation_matrix"] = {
            column: {idx: round(float(value), 6) for idx, value in values.items()}
            for column, values in corr.to_dict().items()
        }

    processed_path = output_dir / "processed_data.csv"
    summary_path = output_dir / "result_summary.json"
    log_path = output_dir / "run_log.txt"
    df.to_csv(processed_path, index=False)
    write_json(summary_path, stats)
    write_text(
        log_path,
        "\n".join(
            [
                "Analysis Agent run log",
                f"source_data={csv_path.as_posix()}",
                f"rows={stats['row_count']}",
                f"columns={stats['column_count']}",
                f"numeric_columns={', '.join(stats['numeric_columns'])}",
                "No p-values were generated in v0.1.",
            ]
        ),
    )
    return stats
