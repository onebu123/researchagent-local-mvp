from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.workflows.state import ResearchState


def _first_output_file(figure: dict[str, Any] | None) -> str | None:
    if not figure:
        return None
    output_files = figure.get("output_files") or []
    return output_files[0] if output_files else None


class ProvenanceAgent(BaseAgent):
    name = "Provenance Agent"
    description = "为 Results claim 生成多条 evidence JSON。"

    def run(self, state: ResearchState) -> ResearchState:
        self.log(state, "writing evidence ledger")
        stats = state.analysis_results or {}
        data_file = state.data_files[0] if state.data_files else f"data/{stats.get('source_data', 'demo_data.csv')}"
        numeric_columns = stats.get("numeric_columns") or []
        figure = state.figures[0] if state.figures else None
        figure_file = _first_output_file(figure)
        analysis_provenance_file = "analysis/analysis_provenance.json"

        claims = [
            {
                "claim_id": "claim_001",
                "section": "Results",
                "claim": (
                    f"The dataset contains {stats.get('row_count', 0)} samples, "
                    f"{stats.get('column_count', 0)} columns, and {len(numeric_columns)} numerical variables."
                ),
                "evidence_type": "analysis_summary",
                "data_file": data_file,
                "analysis_file": "analysis/result_summary.json",
                "analysis_provenance_file": analysis_provenance_file,
                "figure_file": None,
                "figure_provenance_file": None,
                "manuscript_file": "manuscript/draft.md",
                "evidence_status": "supported" if stats else "missing",
                "human_verified": False,
            },
            {
                "claim_id": "claim_002",
                "section": "Results",
                "claim": (
                    f"Figure 1 summarizes the distribution shown in {figure_file}."
                    if figure_file
                    else "Figure 1 should summarize the distribution, but no figure file is available."
                ),
                "evidence_type": "figure",
                "data_file": data_file,
                "analysis_file": "analysis/result_summary.json",
                "analysis_provenance_file": analysis_provenance_file,
                "figure_file": figure_file,
                "figure_provenance_file": "figures/figure_provenance.json",
                "manuscript_file": "manuscript/draft.md",
                "evidence_status": "supported" if figure_file else "missing",
                "human_verified": False,
            },
            {
                "claim_id": "claim_003",
                "section": "Results",
                "claim": (
                    "The Results section is limited to descriptive statistics and figure provenance; "
                    "it does not include fabricated test records, DOI records, or unsupported mechanism claims."
                ),
                "evidence_type": "manuscript_results",
                "data_file": data_file,
                "analysis_file": "analysis/result_summary.json",
                "analysis_provenance_file": analysis_provenance_file,
                "figure_file": figure_file,
                "figure_provenance_file": "figures/figure_provenance.json" if figure_file else None,
                "manuscript_file": "manuscript/draft.md",
                "evidence_status": "supported" if stats else "partial",
                "human_verified": False,
            },
        ]
        state.provenance = claims
        self.save_output(
            state,
            "provenance/evidence.json",
            claims,
            "provenance",
            "证据链 JSON",
        )
        return state
