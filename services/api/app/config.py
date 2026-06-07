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
    cors_allow_origins: tuple[str, ...]
    database_backend: str
    database_url_configured: bool
    queue_mode: str
    queue_url_configured: bool
    auth_mode: str
    auth_secret_configured: bool
    worker_concurrency: int
    llm_mode: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_provider: str
    llm_timeout_seconds: float
    llm_max_retries: int


def _resolve_path(raw: str | None, default: Path, base: Path) -> Path:
    if not raw:
        return default
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def _split_csv(raw: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if raw is None:
        return default
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    return values or default


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
    default_cors_origins = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
    )
    return Settings(
        app_env=os.getenv("APP_ENV", "local"),
        project_root=project_root,
        projects_root=projects_root,
        database_path=database_path,
        cors_allow_origins=_split_csv(os.getenv("CORS_ALLOW_ORIGINS"), default_cors_origins),
        database_backend=os.getenv("DATABASE_BACKEND", "sqlite").strip().lower() or "sqlite",
        database_url_configured=bool(os.getenv("DATABASE_URL", "").strip()),
        queue_mode=os.getenv("QUEUE_MODE", "inline").strip().lower() or "inline",
        queue_url_configured=bool(
            os.getenv("QUEUE_URL", "").strip() or os.getenv("REDIS_URL", "").strip()
        ),
        auth_mode=os.getenv("AUTH_MODE", "disabled").strip().lower() or "disabled",
        auth_secret_configured=bool(os.getenv("AUTH_SHARED_SECRET", "").strip()),
        worker_concurrency=max(int(os.getenv("WORKER_CONCURRENCY", "1")), 1),
        llm_mode=os.getenv("LLM_MODE", "mock"),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        llm_provider=os.getenv("LLM_PROVIDER", "openai-compatible"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "20")),
        llm_max_retries=max(int(os.getenv("LLM_MAX_RETRIES", "1")), 0),
    )


settings = get_settings()
