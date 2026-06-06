from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from app.tools.file_tools import ensure_dir, write_json


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def create_figures(csv_path: Path, output_dir: Path) -> list[dict[str, Any]]:
    ensure_dir(output_dir)
    if not csv_path.exists():
        raise FileNotFoundError(f"source_data 不存在：{csv_path}")

    project_dir = output_dir.parent
    source_data = _relative(csv_path, project_dir)
    data_hash = sha256_file(csv_path)
    created_at = datetime.now(timezone.utc).isoformat()
    df = pd.read_csv(csv_path)
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        raise ValueError("CSV 中没有可绘图的数值列。")

    first_column = numeric_df.columns[0]
    fig1_png = output_dir / "figure_1.png"
    fig1_svg = output_dir / "figure_1.svg"
    plt.figure(figsize=(7, 4.5))
    plt.hist(numeric_df[first_column].dropna(), bins=12, color="#6d5dfc", edgecolor="#ffffff")
    plt.title(f"Distribution of {first_column}")
    plt.xlabel(first_column)
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(fig1_png, dpi=160)
    plt.savefig(fig1_svg)
    plt.close()

    fig2_png = output_dir / "figure_2.png"
    fig2_svg = output_dir / "figure_2.svg"
    if len(numeric_df.columns) >= 2:
        corr = numeric_df.corr(numeric_only=True).fillna(0)
        plt.figure(figsize=(6, 5))
        image = plt.imshow(corr, cmap="viridis", vmin=-1, vmax=1)
        plt.colorbar(image, fraction=0.046, pad=0.04)
        plt.xticks(range(len(corr.columns)), corr.columns, rotation=45, ha="right")
        plt.yticks(range(len(corr.columns)), corr.columns)
        plt.title("Correlation heatmap")
        plt.tight_layout()
    else:
        plt.figure(figsize=(7, 4.5))
        plt.scatter(range(len(numeric_df[first_column])), numeric_df[first_column], color="#12b5cb")
        plt.title(f"Scatter of {first_column}")
        plt.xlabel("Index")
        plt.ylabel(first_column)
        plt.tight_layout()
    plt.savefig(fig2_png, dpi=160)
    plt.savefig(fig2_svg)
    plt.close()

    provenance = [
        {
            "figure_id": "fig_001",
            "title": f"Distribution of {first_column}",
            "figure_type": "histogram",
            "source_data": source_data,
            "analysis_file": "analysis/result_summary.json",
            "script_or_function": "app.tools.plotting.create_figures",
            "output_files": ["figures/figure_1.png", "figures/figure_1.svg"],
            "is_ai_generated": False,
            "is_experimental_result": True,
            "created_at": created_at,
            "data_hash": data_hash,
            "warnings": [],
        },
        {
            "figure_id": "fig_002",
            "title": "Correlation heatmap" if len(numeric_df.columns) >= 2 else f"Scatter of {first_column}",
            "figure_type": "heatmap" if len(numeric_df.columns) >= 2 else "scatter",
            "source_data": source_data,
            "analysis_file": "analysis/result_summary.json",
            "script_or_function": "app.tools.plotting.create_figures",
            "output_files": ["figures/figure_2.png", "figures/figure_2.svg"],
            "is_ai_generated": False,
            "is_experimental_result": True,
            "created_at": created_at,
            "data_hash": data_hash,
            "warnings": [],
        },
    ]
    write_json(output_dir / "figure_provenance.json", provenance)
    return provenance
