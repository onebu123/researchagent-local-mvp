from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

import app.config as config_module
import app.tools.production_scaffold as scaffold_module
from app.workers.research_worker import main as worker_main
from main import app


def test_v2_production_scaffold_defaults_keep_local_fallback() -> None:
    response = TestClient(app).get("/api/system/production-scaffold")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "v3.0.0-rc1"
    assert payload["demo_safe"] is True
    assert payload["mock_fallback"]["no_external_network_required"] is True
    assert payload["validation"]["requires_api_key"] is False
    assert payload["validation"]["script"] == "python scripts/validate_v2.py"
    assert any(item["name"] == "database" and item["fallback"] == "sqlite" for item in payload["capabilities"])
    assert any(item["name"] == "task_queue" and item["fallback"] == "inline" for item in payload["capabilities"])
    assert any(item["name"] == "auth" and item["fallback"] == "disabled" for item in payload["capabilities"])
    assert "production-ready" not in str(payload).lower()
    assert "peer-review-ready" not in str(payload).lower()
    assert "compliance-ready" not in str(payload).lower()


def test_v2_optional_backends_report_configured_without_secret_values(monkeypatch) -> None:
    postgres_url = "postgresql://" + "user:secret@example.local/research"
    redis_url = "redis://:" + "secret@example.local:6379/0"
    monkeypatch.setenv("DATABASE_BACKEND", "postgresql")
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("QUEUE_MODE", "redis")
    monkeypatch.setenv("QUEUE_URL", redis_url)
    monkeypatch.setenv("AUTH_MODE", "shared_secret")
    monkeypatch.setenv("AUTH_SHARED_SECRET", "local-secret-value")

    reloaded_config = importlib.reload(config_module)
    reloaded_scaffold = importlib.reload(scaffold_module)
    payload = reloaded_scaffold.get_production_scaffold_report()

    capabilities = {item["name"]: item for item in payload["capabilities"]}
    assert capabilities["database"]["mode"] == "postgresql"
    assert capabilities["database"]["configured"] is True
    assert capabilities["task_queue"]["mode"] == "redis"
    assert capabilities["task_queue"]["configured"] is True
    assert capabilities["auth"]["mode"] == "shared_secret"
    assert capabilities["auth"]["configured"] is True
    assert "local-secret-value" not in str(payload)
    assert postgres_url.split("@")[0] not in str(payload)
    assert redis_url.split("@")[0] not in str(payload)
    assert reloaded_config.settings.database_url_configured is True

    monkeypatch.delenv("DATABASE_BACKEND", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("QUEUE_MODE", raising=False)
    monkeypatch.delenv("QUEUE_URL", raising=False)
    monkeypatch.delenv("AUTH_MODE", raising=False)
    monkeypatch.delenv("AUTH_SHARED_SECRET", raising=False)
    importlib.reload(config_module)
    importlib.reload(scaffold_module)


def test_v2_worker_scaffold_smoke(capsys) -> None:
    worker_main()
    output = capsys.readouterr().out

    assert '"ok": true' in output
    assert "Worker scaffold smoke completed without external queue access" in output
