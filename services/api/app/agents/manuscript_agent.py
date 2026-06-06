from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.tools.literature_index import load_literature_index
from app.workflows.state import ResearchState


def _claim_lines(claims: list[dict[str, Any]]) -> str:
    if not claims:
        return "- 暂无 claim。"
    return "\n".join(
        (
            f"- {claim['claim_id']}: {claim.get('evidence_status', 'missing')} / "
            f"{claim.get('evidence_type', 'unknown')} / {claim.get('claim', '')}"
        )
        for claim in claims
    )


def _figure_lines(figures: list[dict[str, Any]]) -> str:
    if not figures:
        return "- 图表尚未生成。"
    lines: list[str] = []
    for index, figure in enumerate(figures, start=1):
        output_files = ", ".join(figure.get("output_files", [])) or "missing output files"
        lines.append(
            f"- Figure {index}: {figure.get('title', 'Untitled figure')}; "
            f"source_data={figure.get('source_data', 'unknown')}; "
            f"data_hash={figure.get('data_hash', 'missing')}; "
            f"outputs={output_files}"
        )
    return "\n".join(lines)


def _reference_sections(index: list[dict[str, Any]]) -> str:
    placeholders = [
        entry
        for entry in index
        if entry.get("metadata_status") != "verified" or not entry.get("human_verified")
    ]
    verified = [
        entry
        for entry in index
        if entry.get("metadata_status") == "verified" and entry.get("human_verified")
    ]
    placeholder_lines = [
        (
            f"- {entry['literature_id']}: {entry.get('title') or entry.get('source_file')} "
            f"({entry.get('source_type', 'unknown')}; status={entry.get('metadata_status', 'placeholder')}; "
            "DOI not provided unless manually verified)"
        )
        for entry in placeholders
    ]
    verified_lines = []
    for entry in verified:
        authors = ", ".join(entry.get("authors") or []) or "Authors not provided"
        year = entry.get("year") if entry.get("year") is not None else "year not provided"
        journal = entry.get("journal") or "journal not provided"
        doi = entry.get("doi") or "DOI not provided"
        verified_lines.append(
            f"- {entry['literature_id']}: {authors}. {entry.get('title')} ({year}). {journal}. {doi}"
        )

    if not placeholder_lines:
        placeholder_lines = ["- None."]
    if not verified_lines:
        verified_lines = ["- None in v0.3 demo."]

    all_placeholder = bool(index) and len(placeholders) == len(index)
    warning = (
        "\n\nThese records are placeholders and require manual verification before submission."
        if all_placeholder
        else ""
    )
    return (
        "## Placeholder literature records\n\n"
        + "\n".join(placeholder_lines)
        + warning
        + "\n\n## Verified references\n\n"
        + "\n".join(verified_lines)
    )


class ManuscriptAgent(BaseAgent):
    name = "Manuscript Agent"
    description = "生成带 claim_id Evidence Checklist 的 Markdown 初稿。"

    def run(self, state: ResearchState) -> ResearchState:
        self.log(state, "writing manuscript draft")
        stats = state.analysis_results or {}
        row_count = stats.get("row_count", 0)
        column_count = stats.get("column_count", 0)
        numeric_columns = stats.get("numeric_columns", [])
        numeric_text = ", ".join(numeric_columns) if numeric_columns else "none"
        source_data = (
            state.data_files[0]
            if state.data_files
            else f"data/{stats.get('source_data', 'demo_data.csv')}"
        )
        claims = state.provenance
        literature_index = state.literature_index or load_literature_index(state.project_dir)
        references = _reference_sections(literature_index)
        placeholder_line = (
            "The literature records include placeholder metadata and require manual verification."
            if any(entry.get("metadata_status") == "placeholder" for entry in literature_index)
            else "The project literature records still require author review before submission."
        )

        draft = f"""# Title

{state.project_name}: A Traceable ResearchAgent Draft

# Abstract

This v0.3 draft is generated from project-local data, parsed literature text, figure provenance, evidence claims, and post-manuscript claim alignment. {placeholder_line} The dataset summary reports {row_count} rows, {column_count} columns, and {len(numeric_columns)} numerical variables. No unverified DOI, journal, year, page range, formal test result, or unsupported Results conclusion is created.

# Introduction

{state.project_name} focuses on connecting project files, descriptive data analysis, figure provenance, manuscript claims, and reviewer issues into a reviewable research draft. The current system is intended to support early drafting and audit preparation. It does not replace human source verification or formal domain review.

# Methods

The workflow reads literature files from `literature/`, CSV data from `data/`, writes `analysis/result_summary.json` and `analysis/analysis_provenance.json`, generates figures with `app.tools.plotting.create_figures`, records `figures/figure_provenance.json`, and links Results claims through `provenance/evidence.json`.

# Results

The Results section is limited to `analysis/result_summary.json`, `analysis/analysis_provenance.json`, and `figures/figure_provenance.json`. The source dataset is `{source_data}`. The analysis summary records {row_count} rows and {column_count} columns. Numerical variables are: {numeric_text}.

Figure provenance records:

{_figure_lines(state.figures)}

Linked Results claims:

{_claim_lines(claims)}

# Discussion

The current draft supports traceable descriptive reporting. It does not make formal performance, mechanism, or intervention conclusions. Before submission, the authors need verified references, human-reviewed evidence status, experimental context, and any required formal statistical plan.

# Conclusion

ResearchAgent v0.3 connects parsed literature text, metadata placeholders, PDF parse quality, analysis provenance, figure provenance, evidence claims, claim alignment, and reviewer checks into an initial trustworthy drafting chain. The output is a draft scaffold and must be manually reviewed before external use.

# References

{references}

# Evidence Checklist

{_claim_lines(claims)}
"""
        state.manuscript = draft
        self.save_output(state, "manuscript/draft.md", draft, "manuscript", "论文 Markdown 初稿")
        return state
