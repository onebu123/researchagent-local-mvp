from __future__ import annotations

from app.agents.base import BaseAgent
from app.tools.analysis_provenance import build_analysis_provenance
from app.tools.csv_profile import generate_demo_csv, profile_csv
from app.workflows.state import ResearchState


class AnalysisAgent(BaseAgent):
    name = "Analysis Agent"
    description = "读取 CSV 并生成基础统计分析和分析来源记录。"

    def run(self, state: ResearchState) -> ResearchState:
        self.log(state, "profiling csv data")
        data_dir = state.project_dir / "data"
        csv_files = sorted(data_dir.glob("*.csv"))
        generated_demo_data = False
        if not csv_files:
            csv_files = [generate_demo_csv(data_dir / "demo_data.csv")]
            generated_demo_data = True

        csv_path = csv_files[0]
        state.data_files = [path.relative_to(state.project_dir).as_posix() for path in csv_files]
        analysis_dir = state.project_dir / "analysis"
        stats = profile_csv(csv_path, analysis_dir)
        build_analysis_provenance(state.project_dir, csv_path, stats, generated_demo_data)
        state.analysis_results = stats

        for relative_path, title, mime in [
            ("analysis/result_summary.json", "基础统计分析", "application/json"),
            ("analysis/processed_data.csv", "处理后的数据", "text/csv"),
            ("analysis/run_log.txt", "分析运行日志", "text/plain"),
            ("analysis/analysis_provenance.json", "分析来源记录", "application/json"),
        ]:
            self.record_output(state, relative_path, "analysis", title, mime)
        return state
