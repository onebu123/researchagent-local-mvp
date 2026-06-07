from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json, write_text


REPORT_PATH = "analysis/statistical_assistant_report.json"
NOTES_PATH = "analysis/statistical_assistant_notes.md"
SUMMARY_PATH = "analysis/result_summary.json"
PROCESSED_DATA_PATH = "analysis/processed_data.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_summary(project_dir: Path) -> dict[str, Any]:
    path = project_dir / SUMMARY_PATH
    if not path.exists():
        raise FileNotFoundError(f"{SUMMARY_PATH} does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{SUMMARY_PATH} must contain a JSON object")
    return payload


def _severity_for_missing_rate(rate: float) -> str:
    if rate >= 0.25:
        return "high"
    if rate > 0:
        return "medium"
    return "none"


def _association_strength(value: float) -> str:
    absolute = abs(value)
    if absolute >= 0.75:
        return "strong_association_candidate"
    if absolute >= 0.5:
        return "moderate_association_candidate"
    return "weak_association_candidate"


def _recommended_visualization(column: str, series: pd.Series) -> str:
    lowered = column.lower()
    if any(token in lowered for token in ["efficiency", "stability", "yield", "response"]):
        return "histogram_and_boxplot"
    if pd.api.types.is_numeric_dtype(series):
        return "histogram"
    return "bar_chart"


def _role_suggestions(column: str, series: pd.Series, row_count: int) -> tuple[list[str], list[str]]:
    lowered = column.lower()
    non_null = int(series.notna().sum())
    unique_count = int(series.nunique(dropna=True))
    unique_rate = unique_count / non_null if non_null else 0.0
    roles: list[str] = []
    reasons: list[str] = []

    if "id" in lowered or (row_count > 0 and unique_rate >= 0.95):
        roles.append("id-like")
        reasons.append("Values are mostly unique or the column name indicates an identifier.")

    if pd.api.types.is_numeric_dtype(series):
        roles.append("numeric")
        reasons.append("Column is numeric and can be profiled with descriptive statistics.")
        if any(token in lowered for token in ["efficiency", "stability", "yield", "response", "outcome"]):
            roles.append("outcome-candidate")
            reasons.append("Name suggests a measured response; human review must confirm the role.")
        elif "id" not in lowered:
            roles.append("predictor-candidate")
            reasons.append("Numeric process variable candidate; no causal role is inferred.")
    else:
        roles.append("categorical")
        reasons.append("Column is non-numeric and should be summarized by counts.")

    return roles, reasons


def _missingness(df: pd.DataFrame) -> list[dict[str, Any]]:
    row_count = int(df.shape[0])
    items: list[dict[str, Any]] = []
    for column in df.columns:
        missing_count = int(df[column].isna().sum())
        missing_rate = round(missing_count / row_count, 6) if row_count else 0.0
        items.append(
            {
                "column": column,
                "missing_count": missing_count,
                "missing_rate": missing_rate,
                "severity": _severity_for_missing_rate(missing_rate),
            }
        )
    return items


def _constant_columns(df: pd.DataFrame) -> tuple[list[str], list[dict[str, Any]]]:
    constants: list[str] = []
    near_constants: list[dict[str, Any]] = []
    row_count = int(df.shape[0])
    for column in df.columns:
        value_counts = df[column].value_counts(dropna=True)
        if value_counts.empty:
            constants.append(column)
            continue
        top_count = int(value_counts.iloc[0])
        unique_count = int(df[column].nunique(dropna=True))
        top_value_rate = round(top_count / row_count, 6) if row_count else 0.0
        if unique_count <= 1:
            constants.append(column)
        elif top_value_rate >= 0.95:
            near_constants.append(
                {
                    "column": column,
                    "top_value_rate": top_value_rate,
                    "unique_count": unique_count,
                }
            )
    return constants, near_constants


def _outlier_flags(numeric_df: pd.DataFrame, row_count: int) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for column in numeric_df.columns:
        series = numeric_df[column].dropna()
        if series.empty:
            continue
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        if iqr == 0:
            lower = q1
            upper = q3
            count = 0
        else:
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            count = int(((series < lower) | (series > upper)).sum())
        flags.append(
            {
                "column": column,
                "method": "iqr_1_5",
                "count": count,
                "rate": round(count / row_count, 6) if row_count else 0.0,
                "lower_bound": round(lower, 6),
                "upper_bound": round(upper, 6),
            }
        )
    return flags


def _variable_roles(df: pd.DataFrame) -> list[dict[str, Any]]:
    row_count = int(df.shape[0])
    roles: list[dict[str, Any]] = []
    for column in df.columns:
        suggestions, reasons = _role_suggestions(column, df[column], row_count)
        roles.append(
            {
                "column": column,
                "dtype": str(df[column].dtype),
                "role_suggestions": suggestions,
                "reasons": reasons,
            }
        )
    return roles


def _descriptive_cards(
    summary: dict[str, Any],
    numeric_df: pd.DataFrame,
) -> list[dict[str, Any]]:
    source_stats = summary.get("descriptive_statistics", {})
    if not isinstance(source_stats, dict):
        source_stats = {}
    missing_values = summary.get("missing_values", {})
    if not isinstance(missing_values, dict):
        missing_values = {}

    cards: list[dict[str, Any]] = []
    for column in numeric_df.columns:
        stats = source_stats.get(column, {})
        if not isinstance(stats, dict):
            stats = {}
        cards.append(
            {
                "column": column,
                "mean": stats.get("mean"),
                "std": stats.get("std"),
                "min": stats.get("min"),
                "max": stats.get("max"),
                "missing_count": int(missing_values.get(column, 0) or 0),
                "recommended_visualization": _recommended_visualization(column, numeric_df[column]),
                "notes": ["Descriptive card only; no inferential conclusion is generated."],
            }
        )
    return cards


def _correlation_review(summary: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = summary.get("correlation_matrix", {})
    if not isinstance(matrix, dict):
        return []

    seen: set[tuple[str, str]] = set()
    items: list[dict[str, Any]] = []
    for left, values in matrix.items():
        if not isinstance(values, dict):
            continue
        for right, raw_value in values.items():
            if left == right:
                continue
            key = tuple(sorted([str(left), str(right)]))
            if key in seen:
                continue
            seen.add(key)
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            if abs(value) < 0.5:
                continue
            items.append(
                {
                    "x": left,
                    "y": right,
                    "correlation": round(value, 6),
                    "association_strength": _association_strength(value),
                    "recommendation": "Review a scatter plot and source data before making any domain claim.",
                    "limitations": [
                        "Correlation is an association candidate only.",
                        "No causal relationship, p-value, or statistical significance is generated.",
                    ],
                }
            )
    return sorted(items, key=lambda item: abs(float(item["correlation"])), reverse=True)


def _method_suggestions(df: pd.DataFrame) -> list[dict[str, Any]]:
    numeric_columns = list(df.select_dtypes(include="number").columns)
    categorical_columns = [column for column in df.columns if column not in numeric_columns]
    suggestions = [
        {
            "method": "descriptive_summary",
            "status": "allowed",
            "reason": "Summarizes rows, columns, missing values, and numeric distributions.",
            "outputs": ["analysis/result_summary.json", REPORT_PATH],
        },
        {
            "method": "missingness_review",
            "status": "allowed",
            "reason": "Flags missing data for human review without imputing values.",
            "outputs": [REPORT_PATH],
        },
        {
            "method": "histogram_or_boxplot",
            "status": "suggested",
            "reason": f"Recommended for {len(numeric_columns)} numeric columns.",
            "outputs": ["figures/* if generated by the existing figure tool"],
        },
        {
            "method": "category_count_bar_chart",
            "status": "suggested",
            "reason": f"Recommended for {len(categorical_columns)} categorical or id-like columns when meaningful.",
            "outputs": ["future local chart preview"],
        },
        {
            "method": "inferential_statistics",
            "status": "blocked_without_human_protocol",
            "reason": "v1.4 does not generate p-values or statistical significance claims.",
            "outputs": [],
        },
        {
            "method": "causal_inference",
            "status": "blocked",
            "reason": "v1.4 does not infer causal relationships from local CSV correlations.",
            "outputs": [],
        },
    ]
    return suggestions


def _notes_markdown(report: dict[str, Any]) -> str:
    dataset = report["dataset"]
    health = report["data_health"]
    lines = [
        "# Statistical Assistant Notes",
        "",
        f"- Source summary: `{SUMMARY_PATH}`",
        f"- Source data: `{PROCESSED_DATA_PATH}`",
        f"- Rows / columns: {dataset['row_count']} / {dataset['column_count']}",
        f"- Numeric columns: {', '.join(dataset['numeric_columns']) or 'none'}",
        f"- Missing values flagged: {health['missing_value_columns']}",
        f"- Outlier checks: {health['outlier_flagged_columns']} numeric columns with IQR flags",
        "",
        "## Guardrails",
        "",
        "- This assistant only produces descriptive profiling and method suggestions.",
        "- It does not generate p-values, statistical significance claims, causal claims, or experimental conclusions.",
        "- Association candidates require human domain review before manuscript use.",
        "",
        "## Suggested Review Queue",
        "",
    ]
    for item in report["variable_roles"][:8]:
        roles = ", ".join(item["role_suggestions"])
        lines.append(f"- `{item['column']}`: {roles}")
    if report["correlation_review"]:
        lines.extend(["", "## Association Candidates", ""])
        for item in report["correlation_review"][:8]:
            lines.append(
                f"- `{item['x']}` vs `{item['y']}`: r={item['correlation']} "
                f"({item['association_strength']}); review visually before use."
            )
    return "\n".join(lines) + "\n"


def generate_statistical_assistant_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    analysis_dir = ensure_dir(project_dir / "analysis")
    summary = _load_summary(project_dir)
    processed_path = project_dir / PROCESSED_DATA_PATH
    if not processed_path.exists():
        raise FileNotFoundError(f"{PROCESSED_DATA_PATH} does not exist")

    df = pd.read_csv(processed_path)
    numeric_df = df.select_dtypes(include="number")
    row_count = int(df.shape[0])
    column_count = int(df.shape[1])
    constants, near_constants = _constant_columns(df)
    outliers = _outlier_flags(numeric_df, row_count)
    missing_items = _missingness(df)
    missing_value_columns = sum(1 for item in missing_items if item["missing_count"] > 0)
    outlier_flagged_columns = sum(1 for item in outliers if item["count"] > 0)
    warnings: list[str] = []
    if row_count < 30:
        warnings.append("Small sample size: descriptive summaries require human review.")
    if missing_value_columns:
        warnings.append("Missing values are present; no imputation was performed.")
    if constants or near_constants:
        warnings.append("Constant or near-constant columns may not be useful for modeling.")

    report = {
        "report_id": "statistical_assistant_001",
        "generated_at": _utc_now(),
        "relative_path": REPORT_PATH,
        "source_files": {
            "summary": SUMMARY_PATH,
            "processed_data": PROCESSED_DATA_PATH,
        },
        "dataset": {
            "row_count": row_count,
            "column_count": column_count,
            "columns": list(df.columns),
            "numeric_columns": list(numeric_df.columns),
            "categorical_columns": [column for column in df.columns if column not in numeric_df.columns],
            "is_demo_data": bool(summary.get("is_demo_data")),
        },
        "data_health": {
            "missingness": missing_items,
            "missing_value_columns": missing_value_columns,
            "constant_columns": constants,
            "near_constant_columns": near_constants,
            "outlier_flags": outliers,
            "outlier_flagged_columns": outlier_flagged_columns,
            "small_sample_warning": row_count < 30,
            "warnings": warnings,
        },
        "variable_roles": _variable_roles(df),
        "descriptive_cards": _descriptive_cards(summary, numeric_df),
        "correlation_review": _correlation_review(summary),
        "method_suggestions": _method_suggestions(df),
        "guardrails": [
            "Use this report as a local descriptive assistant, not as peer-review-ready evidence.",
            "Do not turn association candidates into causal claims.",
            "Do not report p-values or statistical significance from this v1.4 assistant.",
            "Do not treat demo data as real experimental evidence.",
        ],
        "limitations": [
            "ResearchAgent v1.4 performs descriptive statistical assistance only.",
            "ResearchAgent v1.4 does not generate p-values or statistical significance claims.",
            "ResearchAgent v1.4 does not perform causal inference.",
            "Method and variable-role suggestions require human domain review.",
        ],
    }

    write_json(analysis_dir / "statistical_assistant_report.json", report)
    write_text(analysis_dir / "statistical_assistant_notes.md", _notes_markdown(report))
    append_audit_event(
        project_dir,
        project_id,
        "generate_statistical_assistant",
        "Statistical assistant report was generated from local analysis outputs.",
        {
            "report_file": REPORT_PATH,
            "notes_file": NOTES_PATH,
            "source_files": [SUMMARY_PATH, PROCESSED_DATA_PATH],
            "row_count": row_count,
            "column_count": column_count,
        },
        source="api",
        event_category="analysis",
        risk_level="low",
        entity_type="analysis",
        entity_id="statistical_assistant_001",
    )
    return report
