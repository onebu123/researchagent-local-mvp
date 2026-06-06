from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def _audit_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_audit_log_exists_and_records_workflow(demo_project_dir: Path) -> None:
    audit_path = demo_project_dir / "audit" / "audit_log.jsonl"

    assert audit_path.exists()
    records = _audit_records(audit_path)
    assert any(record["event_type"] == "run_workflow" for record in records)
    for record in records:
        assert record["actor"] == {"type": "local_user", "id": "local"}
        assert "details" in record


def test_audit_log_does_not_leak_absolute_paths(demo_project_dir: Path) -> None:
    audit_text = (demo_project_dir / "audit" / "audit_log.jsonl").read_text(encoding="utf-8")

    assert not re.search(r"[A-Za-z]:[\\/]", audit_text)
    assert "<secret_removed>" not in audit_text


def test_audit_api_returns_recent_events() -> None:
    client = TestClient(app)
    response = client.get("/api/projects/demo_project/audit")

    assert response.status_code == 200
    records = response.json()
    assert isinstance(records, list)
    assert any(record["event_type"] == "run_workflow" for record in records)
