from __future__ import annotations

from app.agents.base import BaseAgent
from app.workflows.state import ResearchState


class RefinementAgent(BaseAgent):
    name = "Refinement Agent"
    description = "只做语言润色，不新增事实、数字或引用。"

    def run(self, state: ResearchState) -> ResearchState:
        self.log(state, "refining manuscript language")
        draft_path = state.project_dir / "manuscript" / "draft.md"
        draft = state.manuscript or draft_path.read_text(encoding="utf-8")
        refined = (
            draft.replace("本文为 ResearchAgent v0.1 生成的可审计科研草稿。", "本文是由 ResearchAgent v0.1 生成的可审计科研草稿。")
            .replace("当前初稿的目标不是替代作者完成论文", "当前初稿的目标并非替代作者完成论文")
            .replace("可以帮助识别候选趋势", "可用于识别候选趋势")
        )
        report = {
            "changed_sections": ["Abstract", "Introduction", "Discussion"],
            "preserved_numbers": True,
            "warnings": [
                "润色未新增实验结论。",
                "润色未新增真实引用。",
                "请作者人工核验所有数据和论断。",
            ],
        }
        state.refined_manuscript = refined
        self.save_output(state, "manuscript/readable.md", refined, "manuscript", "Readable manuscript draft")
        self.save_output(state, "manuscript/refined.md", refined, "manuscript", "润色版论文草稿")
        self.save_output(
            state,
            "manuscript/refinement_report.json",
            report,
            "manuscript",
            "润色报告",
        )
        return state
