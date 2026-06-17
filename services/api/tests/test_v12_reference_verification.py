from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.tools.reference_verification as reference_verification
from app.tools.reference_verification import run_reference_verification
from main import app
from v12_helpers import base_literature_entry, write_v12_project


def test_reference_verification_generates_candidates_without_modifying_index(tmp_path: Path) -> None:
    index_path = write_v12_project(tmp_path, [base_literature_entry()])
    before = index_path.read_text(encoding="utf-8")

    payload = run_reference_verification(tmp_path, "tmp_project")

    assert payload["summary"]["total"] == 1
    assert payload["literature_index_modified"] is False
    assert index_path.read_text(encoding="utf-8") == before
    result = payload["results"][0]
    assert result["provider"] == "mock_fixture"
    assert result["status"] == "needs_human_review"
    assert result["candidate"]["doi"] is None
    assert result["candidate"]["title"] == "Adaptive Retrieval Improves Local Citation Grounding"


def test_reference_verification_api_contract_does_not_auto_apply(demo_project_dir: Path) -> None:
    client = TestClient(app)
    index_path = demo_project_dir / "literature" / "literature_index.json"
    before = index_path.read_text(encoding="utf-8")

    response = client.post(
        "/api/projects/demo_project/literature/reference-verification/run",
        json={"provider": "mock_fixture"},
    )

    assert response.status_code == 200
    assert response.json()["literature_index_modified"] is False
    assert index_path.read_text(encoding="utf-8") == before

    results = client.get("/api/projects/demo_project/literature/reference-verification/results")
    summary = client.get("/api/projects/demo_project/literature/reference-verification/summary")
    assert results.status_code == 200
    assert summary.status_code == 200
    assert isinstance(results.json(), list)
    assert summary.json()["summary"]["total"] >= 1

    # 确认响应中没有凭空写入 DOI。
    current = json.loads(index_path.read_text(encoding="utf-8"))
    assert all(entry.get("doi") is None for entry in current if entry.get("metadata_status") == "placeholder")


def test_crossref_optional_maps_candidate_without_auto_approval(tmp_path: Path, monkeypatch) -> None:
    index_path = write_v12_project(
        tmp_path,
        [
            base_literature_entry(
                doi="10.1234/local.2026.1",
                metadata_status="verified",
                human_verified=True,
            )
        ],
    )
    before = index_path.read_text(encoding="utf-8")

    def _fake_json(url: str, timeout: float = 10.0) -> dict:
        assert "api.crossref.org" in url
        return {
            "message": {
                "items": [
                    {
                        "title": ["Adaptive Retrieval Improves Local Citation Grounding"],
                        "author": [{"given": "Ada", "family": "Lovelace"}, {"given": "Grace", "family": "Hopper"}],
                        "published-print": {"date-parts": [[2026]]},
                        "DOI": "10.1234/local.2026.1",
                        "container-title": ["Journal of Local Methods"],
                        "URL": "https://doi.org/10.1234/local.2026.1",
                    }
                ]
            }
        }

    monkeypatch.setattr(reference_verification, "_read_url_json", _fake_json)

    payload = run_reference_verification(tmp_path, "tmp_project", provider="crossref_optional")

    result = payload["results"][0]
    assert result["status"] == "verified_candidate"
    assert result["provider"] == "crossref_optional"
    assert result["candidate"]["source"] == "crossref"
    assert result["candidate"]["provider_record_id"] == "10.1234/local.2026.1"
    assert result["requires_human_approval"] is True
    assert result["applied_to_literature_index"] is False
    assert index_path.read_text(encoding="utf-8") == before


def test_semantic_scholar_openalex_and_arxiv_optional_candidate_mapping(tmp_path: Path, monkeypatch) -> None:
    write_v12_project(
        tmp_path,
        [
            base_literature_entry(
                doi="10.1234/local.2026.1",
                metadata_status="verified",
                human_verified=True,
            )
        ],
    )

    def _fake_json(url: str, timeout: float = 10.0) -> dict:
        if "semanticscholar.org" in url:
            return {
                "data": [
                    {
                        "paperId": "S2-1",
                        "url": "https://www.semanticscholar.org/paper/S2-1",
                        "title": "Adaptive Retrieval Improves Local Citation Grounding",
                        "year": 2026,
                        "venue": "Journal of Local Methods",
                        "authors": [{"name": "Ada Lovelace"}, {"name": "Grace Hopper"}],
                        "externalIds": {"DOI": "10.1234/local.2026.1"},
                    }
                ]
            }
        if "api.openalex.org" in url:
            return {
                "results": [
                    {
                        "id": "https://openalex.org/W123",
                        "display_name": "Adaptive Retrieval Improves Local Citation Grounding",
                        "publication_year": 2026,
                        "doi": "https://doi.org/10.1234/local.2026.1",
                        "primary_location": {"source": {"display_name": "Journal of Local Methods"}},
                        "authorships": [
                            {"author": {"display_name": "Ada Lovelace"}},
                            {"author": {"display_name": "Grace Hopper"}},
                        ],
                    }
                ]
            }
        raise AssertionError(f"unexpected URL: {url}")

    def _fake_text(url: str, timeout: float = 10.0) -> str:
        assert "export.arxiv.org" in url
        return """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
          <entry>
            <id>http://arxiv.org/abs/2601.00001v1</id>
            <published>2026-01-01T00:00:00Z</published>
            <title>Adaptive Retrieval Improves Local Citation Grounding</title>
            <author><name>Ada Lovelace</name></author>
            <author><name>Grace Hopper</name></author>
            <arxiv:doi>10.1234/local.2026.1</arxiv:doi>
          </entry>
        </feed>"""

    monkeypatch.setattr(reference_verification, "_read_url_json", _fake_json)
    monkeypatch.setattr(reference_verification, "_read_url_text", _fake_text)

    semantic = run_reference_verification(tmp_path, "tmp_project", provider="semantic_scholar_optional")["results"][0]
    openalex = run_reference_verification(tmp_path, "tmp_project", provider="openalex_optional")["results"][0]
    arxiv = run_reference_verification(tmp_path, "tmp_project", provider="arxiv_optional")["results"][0]

    assert semantic["candidate"]["source"] == "semantic_scholar"
    assert semantic["candidate"]["provider_record_id"] == "S2-1"
    assert openalex["candidate"]["source"] == "openalex"
    assert openalex["candidate"]["provider_record_id"] == "https://openalex.org/W123"
    assert arxiv["candidate"]["source"] == "arxiv"
    assert arxiv["candidate"]["provider_record_id"] == "2601.00001v1"
    assert all(item["applied_to_literature_index"] is False for item in [semantic, openalex, arxiv])
