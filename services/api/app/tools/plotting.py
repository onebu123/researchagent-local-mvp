from __future__ import annotations

import hashlib
import html
import zlib
from datetime import datetime, timezone
from pathlib import Path
from struct import pack
from typing import Any

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


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return pack("!I", len(data)) + kind + data + pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _write_minimal_png(path: Path, width: int = 320, height: int = 180) -> None:
    """Write a tiny deterministic grayscale PNG without matplotlib.

    The project tests and release packages need figure artifacts, but the local
    runtime should not depend on interactive plotting hooks.  This placeholder
    PNG is intentionally simple; the richer, inspectable chart is the adjacent
    SVG written by `_write_svg_chart`.
    """
    width = max(1, min(width, 640))
    height = max(1, min(height, 480))
    raw = b"".join(b"\x00" + (b"\xf5" * width) for _ in range(height))
    payload = b"\x89PNG\r\n\x1a\n"
    payload += _png_chunk(b"IHDR", pack("!IIBBBBB", width, height, 8, 0, 0, 0, 0))
    payload += _png_chunk(b"IDAT", zlib.compress(raw, level=9))
    payload += _png_chunk(b"IEND", b"")
    path.write_bytes(payload)


def _write_svg_chart(path: Path, title: str, labels: list[str], values: list[float]) -> None:
    width = 640
    height = 360
    margin_left = 70
    margin_bottom = 60
    plot_width = width - margin_left - 40
    plot_height = height - 90
    max_value = max([abs(value) for value in values] or [1.0]) or 1.0
    bar_width = plot_width / max(len(values), 1)
    rects: list[str] = []
    for index, value in enumerate(values):
        normalized = abs(value) / max_value
        bar_height = normalized * plot_height
        x = margin_left + index * bar_width + 4
        y = 50 + (plot_height - bar_height)
        label = html.escape(labels[index] if index < len(labels) else str(index + 1))
        rects.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(bar_width - 8, 2):.1f}" height="{bar_height:.1f}" />'
        )
        rects.append(
            f'<text x="{x + max(bar_width - 8, 2) / 2:.1f}" y="{height - 28}" text-anchor="middle" font-size="10">{label[:12]}</text>'
        )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <title>{html.escape(title)}</title>
  <rect x="0" y="0" width="{width}" height="{height}" fill="white" />
  <text x="{margin_left}" y="30" font-size="18" font-family="sans-serif">{html.escape(title)}</text>
  <line x1="{margin_left}" y1="50" x2="{margin_left}" y2="{50 + plot_height}" stroke="black" />
  <line x1="{margin_left}" y1="{50 + plot_height}" x2="{margin_left + plot_width}" y2="{50 + plot_height}" stroke="black" />
  {''.join(rects)}
  <text x="{margin_left}" y="{height - 8}" font-size="11" font-family="sans-serif">Generated locally from project CSV; inspect provenance before external use.</text>
</svg>
'''
    path.write_text(svg, encoding="utf-8")


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

    first_column = str(numeric_df.columns[0])
    fig1_png = output_dir / "figure_1.png"
    fig1_svg = output_dir / "figure_1.svg"
    fig2_png = output_dir / "figure_2.png"
    fig2_svg = output_dir / "figure_2.svg"

    series = numeric_df[first_column].dropna().astype(float)
    if series.empty:
        raise ValueError("CSV 数值列没有可绘图的非空值。")
    bucket_count = min(12, max(1, len(series)))
    minimum = float(series.min())
    maximum = float(series.max())
    if minimum == maximum:
        bucket_labels = [first_column]
        bucket_values = [float(len(series))]
    else:
        span = maximum - minimum
        buckets = [0 for _ in range(bucket_count)]
        for value in series:
            idx = min(bucket_count - 1, int(((float(value) - minimum) / span) * bucket_count))
            buckets[idx] += 1
        bucket_labels = [str(index + 1) for index in range(bucket_count)]
        bucket_values = [float(value) for value in buckets]
    _write_minimal_png(fig1_png)
    _write_svg_chart(fig1_svg, f"Distribution of {first_column}", bucket_labels, bucket_values)

    means = numeric_df.mean(numeric_only=True).fillna(0)
    labels = [str(label) for label in means.index[:12]]
    values = [float(value) for value in means.iloc[:12]]
    _write_minimal_png(fig2_png)
    _write_svg_chart(fig2_svg, "Numeric column means", labels, values)

    provenance = [
        {
            "figure_id": "fig_001",
            "title": f"Distribution of {first_column}",
            "figure_type": "histogram_svg_with_png_placeholder",
            "source_data": source_data,
            "analysis_file": "analysis/result_summary.json",
            "script_or_function": "app.tools.plotting.create_figures",
            "output_files": ["figures/figure_1.png", "figures/figure_1.svg"],
            "is_ai_generated": False,
            "is_experimental_result": True,
            "created_at": created_at,
            "data_hash": data_hash,
            "warnings": ["PNG is a deterministic local placeholder; SVG contains the inspectable chart."],
        },
        {
            "figure_id": "fig_002",
            "title": "Numeric column means",
            "figure_type": "summary_bar_svg_with_png_placeholder",
            "source_data": source_data,
            "analysis_file": "analysis/result_summary.json",
            "script_or_function": "app.tools.plotting.create_figures",
            "output_files": ["figures/figure_2.png", "figures/figure_2.svg"],
            "is_ai_generated": False,
            "is_experimental_result": True,
            "created_at": created_at,
            "data_hash": data_hash,
            "warnings": ["PNG is a deterministic local placeholder; SVG contains the inspectable chart."],
        },
    ]
    write_json(output_dir / "figure_provenance.json", provenance)
    return provenance
