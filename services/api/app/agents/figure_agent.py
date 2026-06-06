from __future__ import annotations

from app.agents.base import BaseAgent
from app.tools.csv_profile import generate_demo_csv
from app.tools.plotting import create_figures
from app.workflows.state import ResearchState


class FigureAgent(BaseAgent):
    name = "Figure Agent"
    description = "根据 CSV 生成 PNG/SVG 图表和 provenance。"

    def run(self, state: ResearchState) -> ResearchState:
        self.log(state, "creating figures")
        data_dir = state.project_dir / "data"
        csv_files = sorted(data_dir.glob("*.csv"))
        if not csv_files:
            csv_files = [generate_demo_csv(data_dir / "demo_data.csv")]
        provenance = create_figures(csv_files[0], state.project_dir / "figures")
        state.figures = provenance
        for relative_path, title, mime in [
            ("figures/figure_1.png", "图 1 PNG", "image/png"),
            ("figures/figure_1.svg", "图 1 SVG", "image/svg+xml"),
            ("figures/figure_2.png", "图 2 PNG", "image/png"),
            ("figures/figure_2.svg", "图 2 SVG", "image/svg+xml"),
            ("figures/figure_provenance.json", "图表来源记录", "application/json"),
        ]:
            self.record_output(state, relative_path, "figure", title, mime)
        return state
