from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.schemas import ProjectCreate
from app.services.project_service import project_service
from app.services.storage_service import storage_service
from app.tools.audit_log import append_audit_event, audit_log_path, verify_audit_hash_chain
from main import app


def _records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_audit_hash_chain_verifies_and_detects_tampering() -> None:
    project_id = f"v05_audit_{uuid.uuid4().hex[:8]}"
    project_service.create_project(
        ProjectCreate(name="v0.5 audit test", domain="materials"),
        project_id=project_id,
        overwrite=True,
    )
    project_dir = storage_service.project_dir(project_id)
    append_audit_event(
        project_dir,
        project_id,
        "pytest_audit_event",
        "First pytest audit event.",
        {"step": 1},
        source="test",
    )
    append_audit_event(
        project_dir,
        project_id,
        "pytest_audit_event",
        "Second pytest audit event.",
        {"step": 2},
        source="test",
    )

    path = audit_log_path(project_dir)
    records = _records(path)
    assert records
    assert records[0]["prev_hash"] == "GENESIS"
    for previous, current in zip(records, records[1:]):
        assert current["prev_hash"] == previous["entry_hash"]

    direct = verify_audit_hash_chain(project_dir)
    assert direct["valid"] is True

    client = TestClient(app)
    api_response = client.get(f"/api/projects/{project_id}/audit/verify")
    assert api_response.status_code == 200
    assert api_response.json()["valid"] is True

    records[0]["summary"] = "Tampered summary."
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )

    tampered = verify_audit_hash_chain(project_dir)
    assert tampered["valid"] is False
    assert tampered["first_invalid_index"] == 0

    tampered_response = client.get(f"/api/projects/{project_id}/audit/verify")
    assert tampered_response.status_code == 200
    assert tampered_response.json()["valid"] is False
