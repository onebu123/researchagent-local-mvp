from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _capability(
    name: str,
    mode: str,
    configured: bool,
    fallback: str,
    notes: list[str],
) -> dict[str, Any]:
    return {
        "name": name,
        "mode": mode,
        "configured": configured,
        "fallback": fallback,
        "notes": notes,
    }


def get_production_scaffold_report() -> dict[str, Any]:
    database_configured = settings.database_backend == "postgresql" and settings.database_url_configured
    queue_configured = settings.queue_mode != "inline" and settings.queue_url_configured
    auth_configured = settings.auth_mode != "disabled" and settings.auth_secret_configured

    capabilities = [
        _capability(
            "database",
            settings.database_backend,
            database_configured,
            "sqlite",
            [
                "SQLite remains the default local demo store.",
                "PostgreSQL is optional and requires explicit backend and database connection settings.",
                "v2.0 does not run migrations against external databases automatically.",
            ],
        ),
        _capability(
            "task_queue",
            settings.queue_mode,
            queue_configured,
            "inline",
            [
                "Inline execution remains the default so demo workflows run without Redis or workers.",
                "External queue mode is a scaffold only until a worker is explicitly configured.",
            ],
        ),
        _capability(
            "auth",
            settings.auth_mode,
            auth_configured,
            "disabled",
            [
                "Auth is disabled by default for the local demo.",
                "Configured auth must be enforced server-side before any shared deployment.",
                "Do not rely on frontend controls as a security boundary.",
            ],
        ),
        _capability(
            "containers",
            "docker_compose",
            True,
            "local_process",
            [
                "Dockerfiles and docker-compose profiles are provided for repeatable local checks.",
                "Container scaffold is not a public deployment guarantee.",
            ],
        ),
    ]

    blocking_items = [
        "No production auth enforcement is enabled by default.",
        "PostgreSQL and queue backends are optional scaffolds, not required local dependencies.",
        "Secrets must be supplied outside git and must not appear in logs, reports, or exports.",
        "Deployment requires operator review of TLS, backups, monitoring, and rollback steps.",
    ]

    return {
        "version": "v2.0",
        "name": "Research Workspace scaffold",
        "generated_at": _utc_now(),
        "environment": settings.app_env,
        "status": "scaffold_ready_for_local_validation",
        "demo_safe": True,
        "mock_fallback": {
            "llm_mode": settings.llm_mode,
            "no_api_key_required": not settings.llm_api_key.strip(),
            "no_external_network_required": True,
        },
        "capabilities": capabilities,
        "worker": {
            "mode": settings.queue_mode,
            "concurrency": settings.worker_concurrency,
            "entrypoint": "python -m app.workers.research_worker",
            "fallback": "inline",
        },
        "deployment_documents": [
            "docs/deployment_v2.md",
            "docs/v2.0_acceptance_criteria.md",
            "docs/v2.0_acceptance_report.md",
        ],
        "validation": {
            "script": "python scripts/validate_v2.py",
            "requires_api_key": False,
            "requires_external_network": False,
        },
        "guardrails": [
            "Do not fabricate DOI, citations, p-values, significance, causal claims, OCR output, or scientific conclusions.",
            "Do not commit secrets, environment files with real values, stack traces, or local absolute paths.",
            "Do not present this scaffold as ready for peer review, compliance evidence, or shared deployment use.",
        ],
        "blocking_items": blocking_items,
    }


def run_worker_smoke() -> dict[str, Any]:
    return {
        "ok": True,
        "mode": settings.queue_mode,
        "fallback": "inline",
        "processed": 0,
        "message": "Worker scaffold smoke completed without external queue access.",
    }
