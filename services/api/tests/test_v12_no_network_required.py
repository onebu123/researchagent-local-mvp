from __future__ import annotations

import socket
from pathlib import Path

from app.tools.reference_verification import run_reference_verification
from v12_helpers import base_literature_entry, write_v12_project


def test_optional_reference_providers_fail_gracefully_without_network(
    tmp_path: Path,
    monkeypatch,
) -> None:
    write_v12_project(tmp_path, [base_literature_entry()])

    def _blocked_socket(*args, **kwargs):
        raise AssertionError("network must not be required")

    monkeypatch.setattr(socket, "create_connection", _blocked_socket)

    payload = run_reference_verification(tmp_path, "tmp_project", provider="crossref_optional")

    assert payload["literature_index_modified"] is False
    assert payload["results"][0]["status"] == "provider_failed"
    assert "gracefully" in payload["results"][0]["warnings"][0]
