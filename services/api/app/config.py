from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_env: str
    project_root: Path
    projects_root: Path
    database_path: Path
    llm_mode: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str


def _resolve_path(raw: str | None, default: Path, base: Path) -> Path:
    if not raw:
        return default
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[3]
    projects_root = _resolve_path(
        os.getenv("PROJECTS_ROOT"),
        project_root / "projects",
        project_root,
    )
    database_path = _resolve_path(
        os.getenv("DATABASE_PATH"),
        projects_root / "research_agent.sqlite3",
        project_root,
    )
    return Settings(
        app_env=os.getenv("APP_ENV", "local"),
        project_root=project_root,
        projects_root=projects_root,
        database_path=database_path,
        llm_mode=os.getenv("LLM_MODE", "mock"),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    )


settings = get_settings()
