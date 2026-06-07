from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json
from app.tools.literature_index import load_literature_index
from app.tools.prompt_registry import load_prompt

PROMPT_VERSION = "metadata_extraction_v1"
PROVIDERS = {"mock_fixture", "crossref_optional", "semantic_scholar_optional"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def results_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "metadata_lookup_results.jsonl"


def summary_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "metadata_lookup_summary.json"


def _append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_metadata_lookup_results(project_dir: Path) -> dict[str, Any]:
    path = results_path(project_dir)
    records: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
    summary = {}
    if summary_path(project_dir).exists():
        payload = json.loads(summary_path(project_dir).read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            summary = payload
    return {"results": records, "summary": summary}


def _base_record(entry: dict[str, Any], provider: str) -> dict[str, Any]:
    return {
        "lookup_id": "",
        "created_at": _utc_now(),
        "provider": provider,
        "literature_id": entry.get("literature_id"),
        "source_file": entry.get("source_file"),
        "query_title": entry.get("title"),
        "candidates": [],
        "status": "needs_human_review",
        "human_verification_required": True,
        "literature_index_modified": False,
        "warnings": [
            "Lookup results are drafts only.",
            "No metadata is written back to literature_index.json.",
        ],
    }


def _mock_lookup(entry: dict[str, Any], provider: str) -> dict[str, Any]:
    record = _base_record(entry, provider)
    candidate: dict[str, Any] = {
        "title": entry.get("title"),
        "doi": entry.get("doi"),
        "authors": entry.get("authors") or [],
        "year": entry.get("year"),
        "journal": entry.get("journal"),
        "confidence": "low",
        "source": "existing_local_metadata",
        "human_verified": False,
    }
    candidate = {key: value for key, value in candidate.items() if value not in (None, "", [])}
    if candidate:
        record["candidates"] = [candidate]
    if not entry.get("doi"):
        record["warnings"].append("No DOI candidate was supplied by the mock provider.")
    return record


def _read_url_json(url: str, timeout: float = 10.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "ResearchAgent-local-mvp/1.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _crossref_lookup(entry: dict[str, Any], provider: str) -> dict[str, Any]:
    record = _base_record(entry, provider)
    title = str(entry.get("title") or "").strip()
    if not title:
        record["warnings"].append("No title available for Crossref query.")
        return record
    query = urllib.parse.urlencode({"query.title": title, "rows": "1"})
    try:
        payload = _read_url_json(f"https://api.crossref.org/works?{query}")
        items = payload.get("message", {}).get("items", [])
    except Exception as exc:
        record["status"] = "provider_failed"
        record["warnings"].append(f"Crossref optional lookup failed: {exc.__class__.__name__}")
        return record
    candidates: list[dict[str, Any]] = []
    for item in items[:1] if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        candidate: dict[str, Any] = {
            "title": (item.get("title") or [None])[0] if isinstance(item.get("title"), list) else None,
            "doi": item.get("DOI"),
            "journal": (item.get("container-title") or [None])[0]
            if isinstance(item.get("container-title"), list)
            else None,
            "year": ((item.get("published-print") or item.get("published-online") or {}).get("date-parts") or [[None]])[0][0],
            "source": "crossref",
            "confidence": "provider_candidate",
            "human_verified": False,
        }
        candidates.append({key: value for key, value in candidate.items() if value not in (None, "", [])})
    record["candidates"] = candidates
    return record


def _semantic_scholar_lookup(entry: dict[str, Any], provider: str) -> dict[str, Any]:
    record = _base_record(entry, provider)
    title = str(entry.get("title") or "").strip()
    if not title:
        record["warnings"].append("No title available for Semantic Scholar query.")
        return record
    query = urllib.parse.urlencode({"query": title, "limit": "1", "fields": "title,year,authors,venue,externalIds"})
    try:
        payload = _read_url_json(f"https://api.semanticscholar.org/graph/v1/paper/search?{query}")
        items = payload.get("data", [])
    except Exception as exc:
        record["status"] = "provider_failed"
        record["warnings"].append(
            f"Semantic Scholar optional lookup failed: {exc.__class__.__name__}"
        )
        return record
    candidates: list[dict[str, Any]] = []
    for item in items[:1] if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        external_ids = item.get("externalIds") if isinstance(item.get("externalIds"), dict) else {}
        authors = item.get("authors") if isinstance(item.get("authors"), list) else []
        candidate: dict[str, Any] = {
            "title": item.get("title"),
            "doi": external_ids.get("DOI"),
            "authors": [author.get("name") for author in authors if isinstance(author, dict) and author.get("name")],
            "year": item.get("year"),
            "journal": item.get("venue"),
            "source": "semantic_scholar",
            "confidence": "provider_candidate",
            "human_verified": False,
        }
        candidates.append({key: value for key, value in candidate.items() if value not in (None, "", [])})
    record["candidates"] = candidates
    return record


def run_metadata_lookup(project_dir: Path, project_id: str, provider: str = "mock_fixture") -> dict[str, Any]:
    if provider not in PROVIDERS:
        raise ValueError(f"Unsupported metadata lookup provider: {provider}")
    prompt = load_prompt(PROMPT_VERSION)
    entries = load_literature_index(project_dir)
    records: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, start=1):
        if provider == "crossref_optional":
            record = _crossref_lookup(entry, provider)
        elif provider == "semantic_scholar_optional":
            record = _semantic_scholar_lookup(entry, provider)
        else:
            record = _mock_lookup(entry, provider)
        record["lookup_id"] = f"metadata_lookup_{index:04d}"
        record["prompt_version"] = prompt["prompt_version"]
        records.append(record)
    _append_jsonl(results_path(project_dir), records)
    summary = {
        "generated_at": _utc_now(),
        "relative_path": "literature/metadata_lookup_summary.json",
        "results_file": "literature/metadata_lookup_results.jsonl",
        "provider": provider,
        "prompt_version": prompt["prompt_version"],
        "literature_index_modified": False,
        "records": len(records),
        "candidate_count": sum(len(record.get("candidates", [])) for record in records),
        "needs_human_review": len(records),
        "warnings": [
            "Metadata lookup results are drafts and require human verification.",
            "No DOI, author, journal, year, or page metadata is fabricated.",
        ],
    }
    write_json(summary_path(project_dir), summary)
    append_audit_event(
        project_dir,
        project_id,
        "run_literature_metadata_lookup",
        "Literature metadata lookup draft was generated without modifying literature_index.json.",
        {
            "provider": provider,
            "result_count": len(records),
            "literature_index_modified": False,
        },
        source="api",
        event_category="literature",
        risk_level="low",
        entity_type="literature",
        entity_id="metadata_lookup",
    )
    return {"results": records, "summary": summary}
