from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.tools.file_tools import write_json, write_text
from app.workflows.state import PendingOutput, ResearchState


class BaseAgent(ABC):
    name: str = "Base Agent"
    description: str = "Base research agent"

    @abstractmethod
    def run(self, state: ResearchState) -> ResearchState:
        raise NotImplementedError

    def log(self, state: ResearchState, message: str) -> None:
        state.current_step = self.name
        print(f"[{state.project_id}][{self.name}] {message}")

    def save_output(
        self,
        state: ResearchState,
        relative_path: str,
        content: str | dict[str, Any] | list[Any],
        kind: str,
        title: str,
        mime_type: str | None = None,
    ) -> Path:
        path = state.project_dir / relative_path
        if isinstance(content, (dict, list)):
            write_json(path, content)
            mime_type = mime_type or "application/json"
        else:
            write_text(path, content)
            mime_type = mime_type or self._mime_type(relative_path)
        self.record_output(state, relative_path, kind, title, mime_type)
        return path

    def record_output(
        self,
        state: ResearchState,
        relative_path: str,
        kind: str,
        title: str,
        mime_type: str,
    ) -> None:
        state.outputs.append(
            PendingOutput(
                agent_name=self.name,
                kind=kind,
                title=title,
                relative_path=relative_path,
                mime_type=mime_type,
            )
        )

    def _mime_type(self, relative_path: str) -> str:
        suffix = Path(relative_path).suffix.lower()
        if suffix == ".md":
            return "text/markdown"
        if suffix == ".txt":
            return "text/plain"
        if suffix == ".csv":
            return "text/csv"
        if suffix == ".svg":
            return "image/svg+xml"
        if suffix == ".png":
            return "image/png"
        return "application/octet-stream"
