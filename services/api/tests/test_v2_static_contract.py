from __future__ import annotations

from pathlib import Path

from app.tools.production_scaffold import get_production_scaffold_report


ROOT = Path(__file__).resolve().parents[3]


def test_v2_static_scaffold_keeps_optional_dependencies() -> None:
    config_text = (ROOT / "services" / "api" / "app" / "config.py").read_text(encoding="utf-8")
    scaffold_text = (
        ROOT / "services" / "api" / "app" / "tools" / "production_scaffold.py"
    ).read_text(encoding="utf-8")
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert 'os.getenv("DATABASE_BACKEND", "sqlite")' in config_text
    assert 'os.getenv("QUEUE_MODE", "inline")' in config_text
    assert 'os.getenv("AUTH_MODE", "disabled")' in config_text
    payload_text = str(get_production_scaffold_report())
    assert "DATABASE_URL" not in payload_text
    assert "AUTH_SHARED_SECRET" not in payload_text
    assert 'profiles: ["postgres"]' in compose_text
    assert 'profiles: ["queue"]' in compose_text
    assert 'profiles: ["worker"]' in compose_text


def test_v2_docs_and_frontend_include_required_markers() -> None:
    frontend_text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in [
            "apps/web/components/ProductionScaffoldPanel.tsx",
            "apps/web/e2e/v2-production-scaffold.spec.ts",
            "apps/web/lib/api.ts",
        ]
    )
    docs_text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in [
            "docs/deployment_v2.md",
            "docs/v2.0_acceptance_criteria.md",
            "docs/v2.0_acceptance_report.md",
        ]
    )

    for marker in [
        "Research Workspace Scaffold",
        "python scripts/validate_v2.py",
        "PostgreSQL",
        "auth",
        "inline",
    ]:
        assert marker in frontend_text or marker in docs_text

    assert "dangerouslySetInnerHTML" not in frontend_text
    assert "sk_live_" not in docs_text
