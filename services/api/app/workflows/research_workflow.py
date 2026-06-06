from __future__ import annotations

from collections.abc import Callable

from app.agents.analysis_agent import AnalysisAgent
from app.agents.base import BaseAgent
from app.agents.claim_alignment_agent import ClaimAlignmentAgent
from app.agents.figure_agent import FigureAgent
from app.agents.literature_agent import LiteratureAgent
from app.agents.manuscript_agent import ManuscriptAgent
from app.agents.provenance_agent import ProvenanceAgent
from app.agents.refinement_agent import RefinementAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.agents.topic_agent import TopicNoveltyAgent
from app.workflows.state import ResearchState


class ResearchWorkflow:
    def __init__(self) -> None:
        self.agents: list[tuple[str, BaseAgent]] = [
            ("literature", LiteratureAgent()),
            ("topic", TopicNoveltyAgent()),
            ("analysis", AnalysisAgent()),
            ("figure", FigureAgent()),
            ("provenance", ProvenanceAgent()),
            ("manuscript", ManuscriptAgent()),
            ("claim_alignment", ClaimAlignmentAgent()),
            ("refinement", RefinementAgent()),
            ("reviewer", ReviewerAgent()),
        ]

    def run(
        self,
        state: ResearchState,
        before_step: Callable[[str], None] | None = None,
    ) -> ResearchState:
        state.workflow_status = "running"
        for step_name, agent in self.agents:
            if before_step:
                before_step(step_name)
            state.current_step = step_name
            state = agent.run(state)
        state.workflow_status = "completed"
        state.current_step = "completed"
        return state

    def run_step(self, state: ResearchState, step: str) -> ResearchState:
        for step_name, agent in self.agents:
            if step_name == step or agent.name == step:
                state.workflow_status = "running"
                state.current_step = step_name
                state = agent.run(state)
                state.workflow_status = "completed"
                state.current_step = step_name
                return state
        raise KeyError(step)

    def step_names(self) -> list[str]:
        return [step for step, _agent in self.agents]
