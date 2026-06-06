from __future__ import annotations

from app.agents.base import BaseAgent
from app.workflows.state import ResearchState


class TopicNoveltyAgent(BaseAgent):
    name = "Topic & Novelty Agent"
    description = "生成候选选题和新颖性风险，不承诺真实创新。"

    def run(self, state: ResearchState) -> ResearchState:
        self.log(state, "drafting candidate topics")
        topics = [
            {
                "title": "工艺温度对材料效率与稳定性协同影响的描述性研究",
                "hypothesis": "在 demo 数据范围内，温度变化可能与效率和稳定性指标存在可观察关联。",
                "novelty_risk": "medium",
                "feasibility": "high",
                "reason": "可直接使用项目 CSV 进行描述统计和相关矩阵分析，但缺少真实文献核验。",
            },
            {
                "title": "浓度参数对带隙与性能指标关系的初步探索",
                "hypothesis": "浓度与 band_gap、efficiency 的关系可通过图表形成候选问题。",
                "novelty_risk": "high",
                "feasibility": "medium",
                "reason": "v0.1 只能提出候选问题，不能证明新颖性或因果关系。",
            },
            {
                "title": "面向可审计论文草稿的证据链自动生成工作流",
                "hypothesis": "将分析结果、图表 provenance 和论文 claim 绑定可降低草稿审查成本。",
                "novelty_risk": "low",
                "feasibility": "high",
                "reason": "系统层选题与当前 MVP 功能直接匹配，仍需要真实用户研究验证。",
            },
        ]
        report = {
            "project_id": state.project_id,
            "source": "literature_review.md",
            "placeholder_warning": state.literature_is_placeholder,
            "topics": topics,
        }
        state.candidate_topics = topics
        state.novelty_report = report
        self.save_output(state, "literature/novelty_report.json", report, "topic", "候选选题与新颖性风险")
        return state
