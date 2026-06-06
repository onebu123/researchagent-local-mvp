from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def _contains_forbidden_value(value) -> bool:
    if isinstance(value, dict):
        return any(_contains_forbidden_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_value(item) for item in value)
    if isinstance(value, str):
        return "sk_live_" in value or "api_key" in value.lower() or bool(re.search(r"[A-Za-z]:[\\/]", value))
    return False


def test_audit_export_generates_json_and_integrity_report(demo_project_dir: Path) -> None:
    client = TestClient(app)

    response = client.post("/api/projects/demo_project/audit/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["hash_chain_valid"] is True
    assert payload["source_file"] == "audit/audit_log.jsonl"
    assert payload["entry_count"] == len(payload["entries"])
    assert payload["first_invalid_index"] is None
    assert not _contains_forbidden_value(payload)

    export_path = demo_project_dir / "audit" / "exports" / f"{payload['export_id']}.json"
    report_path = (
        demo_project_dir
        / "audit"
        / "exports"
        / f"audit_integrity_report_{payload['export_id'].removeprefix('audit_export_')}.md"
    )
    assert export_path.exists()
    assert report_path.exists()
    assert "not a production-grade tamper-proof audit system" in report_path.read_text(
        encoding="utf-8"
    )
    assert json.loads(export_path.read_text(encoding="utf-8"))["export_id"] == payload["export_id"]

    list_response = client.get("/api/projects/demo_project/audit/exports")
    get_response = client.get(f"/api/projects/demo_project/audit/exports/{payload['export_id']}")
    report_response = client.get(
        f"/api/projects/demo_project/audit/exports/{payload['export_id']}/report"
    )
    assert list_response.status_code == 200
    assert any(item["export_id"] == payload["export_id"] for item in list_response.json())
    assert get_response.status_code == 200
    assert get_response.json()["export_id"] == payload["export_id"]
    assert report_response.status_code == 200
    assert "Audit Integrity Report" in report_response.json()["content"]

