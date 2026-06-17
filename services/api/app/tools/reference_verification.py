from __future__ import annotations

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json
from app.tools.literature_index import load_literature_index
from app.tools.reference_match_score import calculate_match_scores

ReferenceProvider = Literal[
    "mock_fixture",
    "crossref_optional",
    "semantic_scholar_optional",
    "openalex_optional",
    "arxiv_optional",
    "pubmed_optional",
]

PROVIDERS: set[str] = {
    "mock_fixture",
    "crossref_optional",
    "semantic_scholar_optional",
    "openalex_optional",
    "arxiv_optional",
    "pubmed_optional",
}
STATUSES = {
    "verified_candidate",
    "ambiguous_match",
    "no_match",
    "provider_failed",
    "needs_human_review",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def reference_verification_dir(project_dir: Path) -> Path:
    return project_dir / "literature" / "reference_verification"


def reference_verification_results_path(project_dir: Path) -> Path:
    return reference_verification_dir(project_dir) / "reference_verification_results.jsonl"


def reference_verification_summary_path(project_dir: Path) -> Path:
    return reference_verification_dir(project_dir) / "reference_verification_summary.json"


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def read_reference_verification_results(project_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(reference_verification_results_path(project_dir))


def _query_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": entry.get("title") or "Unknown title",
        "authors": entry.get("authors") if isinstance(entry.get("authors"), list) else [],
        "year": entry.get("year"),
        "doi": entry.get("doi"),
        "journal": entry.get("journal"),
    }


def _clean_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    result = {
        "title": candidate.get("title"),
        "authors": candidate.get("authors") if isinstance(candidate.get("authors"), list) else [],
        "year": candidate.get("year"),
        "doi": candidate.get("doi"),
        "journal": candidate.get("journal"),
        "url": candidate.get("url"),
        "provider_record_id": candidate.get("provider_record_id"),
        "provider_url": candidate.get("provider_url"),
        "source": candidate.get("source"),
    }
    return result


def _mock_candidate(entry: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    title = str(entry.get("title") or "").strip()
    warnings: list[str] = []
    if not title:
        return None, ["Local record has no title; mock provider cannot create a candidate."]
    if entry.get("metadata_status") == "placeholder":
        warnings.append("Mock candidate is based on placeholder local metadata and requires review.")
    if not entry.get("doi"):
        warnings.append("No DOI candidate was supplied; DOI was not fabricated.")
    return (
        _clean_candidate(
            {
                "title": title,
                "authors": entry.get("authors") if isinstance(entry.get("authors"), list) else [],
                "year": entry.get("year"),
                "doi": entry.get("doi"),
                "journal": entry.get("journal"),
                "url": None,
                "provider_record_id": None,
                "provider_url": None,
                "source": "existing_local_metadata",
            }
        ),
        warnings,
    )


def _optional_provider_failure(provider: str, reason: str) -> tuple[None, list[str], str]:
    return (
        None,
        [f"{provider} failed gracefully; no metadata was written to literature_index.json."],
        reason,
    )


def _read_url_json(url: str, timeout: float = 10.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "ResearchAgent-local-mvp/3.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_url_text(url: str, timeout: float = 10.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "ResearchAgent-local-mvp/3.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _first(value: Any) -> Any:
    if isinstance(value, list) and value:
        return value[0]
    return None


def _date_parts_year(value: Any) -> Any:
    if not isinstance(value, dict):
        return None
    parts = value.get("date-parts")
    if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
        return parts[0][0]
    return None


def _crossref_author_names(item: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for author in item.get("author", []) if isinstance(item.get("author"), list) else []:
        if not isinstance(author, dict):
            continue
        parts = [str(author.get("given") or "").strip(), str(author.get("family") or "").strip()]
        name = " ".join(part for part in parts if part)
        if name:
            names.append(name)
    return names


def _crossref_candidate(entry: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], str | None]:
    title = str(entry.get("title") or "").strip()
    doi = str(entry.get("doi") or "").strip()
    if not title and not doi:
        return None, ["No title or DOI available for Crossref query."], None
    query = {"rows": "1"}
    if doi:
        query["filter"] = f"doi:{doi}"
    else:
        query["query.title"] = title
    payload = _read_url_json(f"https://api.crossref.org/works?{urllib.parse.urlencode(query)}")
    items = payload.get("message", {}).get("items", [])
    item = _first(items) if isinstance(items, list) else None
    if not isinstance(item, dict):
        return None, ["Crossref returned no candidate for this local record."], None
    year = (
        _date_parts_year(item.get("published-print"))
        or _date_parts_year(item.get("published-online"))
        or _date_parts_year(item.get("published"))
        or _date_parts_year(item.get("issued"))
    )
    item_doi = item.get("DOI")
    provider_url = item.get("URL") or (f"https://doi.org/{item_doi}" if item_doi else None)
    return (
        _clean_candidate(
            {
                "title": _first(item.get("title")) if isinstance(item.get("title"), list) else item.get("title"),
                "authors": _crossref_author_names(item),
                "year": year,
                "doi": item_doi,
                "journal": _first(item.get("container-title"))
                if isinstance(item.get("container-title"), list)
                else None,
                "url": provider_url,
                "provider_record_id": item_doi,
                "provider_url": provider_url,
                "source": "crossref",
            }
        ),
        ["Crossref candidate metadata requires human review before approval."],
        None,
    )


def _semantic_scholar_candidate(entry: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], str | None]:
    title = str(entry.get("title") or "").strip()
    doi = str(entry.get("doi") or "").strip()
    query_text = doi or title
    if not query_text:
        return None, ["No title or DOI available for Semantic Scholar query."], None
    query = urllib.parse.urlencode(
        {"query": query_text, "limit": "1", "fields": "title,year,authors,venue,externalIds,paperId,url"}
    )
    payload = _read_url_json(f"https://api.semanticscholar.org/graph/v1/paper/search?{query}")
    items = payload.get("data", [])
    item = _first(items) if isinstance(items, list) else None
    if not isinstance(item, dict):
        return None, ["Semantic Scholar returned no candidate for this local record."], None
    external_ids = item.get("externalIds") if isinstance(item.get("externalIds"), dict) else {}
    authors = item.get("authors") if isinstance(item.get("authors"), list) else []
    paper_id = item.get("paperId")
    provider_url = item.get("url") or (f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else None)
    return (
        _clean_candidate(
            {
                "title": item.get("title"),
                "authors": [author.get("name") for author in authors if isinstance(author, dict) and author.get("name")],
                "year": item.get("year"),
                "doi": external_ids.get("DOI"),
                "journal": item.get("venue"),
                "url": provider_url,
                "provider_record_id": paper_id,
                "provider_url": provider_url,
                "source": "semantic_scholar",
            }
        ),
        ["Semantic Scholar candidate metadata requires human review before approval."],
        None,
    )


def _openalex_candidate(entry: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], str | None]:
    title = str(entry.get("title") or "").strip()
    doi = str(entry.get("doi") or "").strip()
    if not title and not doi:
        return None, ["No title or DOI available for OpenAlex query."], None
    if doi:
        query = urllib.parse.urlencode({"filter": f"doi:{doi}", "per-page": "1"})
    else:
        query = urllib.parse.urlencode({"search": title, "per-page": "1"})
    payload = _read_url_json(f"https://api.openalex.org/works?{query}")
    items = payload.get("results", [])
    item = _first(items) if isinstance(items, list) else None
    if not isinstance(item, dict):
        return None, ["OpenAlex returned no candidate for this local record."], None
    authorships = item.get("authorships") if isinstance(item.get("authorships"), list) else []
    source = ((item.get("primary_location") or {}).get("source") or {}) if isinstance(item.get("primary_location"), dict) else {}
    doi_value = item.get("doi")
    if isinstance(doi_value, str):
        doi_value = doi_value.replace("https://doi.org/", "")
    return (
        _clean_candidate(
            {
                "title": item.get("display_name"),
                "authors": [
                    author.get("author", {}).get("display_name")
                    for author in authorships
                    if isinstance(author, dict)
                    and isinstance(author.get("author"), dict)
                    and author.get("author", {}).get("display_name")
                ],
                "year": item.get("publication_year"),
                "doi": doi_value,
                "journal": source.get("display_name") if isinstance(source, dict) else None,
                "url": item.get("id"),
                "provider_record_id": item.get("id"),
                "provider_url": item.get("id"),
                "source": "openalex",
            }
        ),
        ["OpenAlex candidate metadata requires human review before approval."],
        None,
    )


def _xml_text(node: ET.Element, path: str, namespaces: dict[str, str]) -> str | None:
    child = node.find(path, namespaces)
    if child is None or child.text is None:
        return None
    return " ".join(child.text.split()) or None


def _arxiv_candidate(entry: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], str | None]:
    title = str(entry.get("title") or "").strip()
    if not title:
        return None, ["No title available for arXiv query."], None
    query = urllib.parse.urlencode({"search_query": f'ti:"{title}"', "start": "0", "max_results": "1"})
    xml_text = _read_url_text(f"https://export.arxiv.org/api/query?{query}")
    root = ET.fromstring(xml_text)
    namespaces = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    entry_node = root.find("atom:entry", namespaces)
    if entry_node is None:
        return None, ["arXiv returned no candidate for this local record."], None
    published = _xml_text(entry_node, "atom:published", namespaces)
    provider_url = _xml_text(entry_node, "atom:id", namespaces)
    authors = [
        " ".join((author.findtext("atom:name", default="", namespaces=namespaces) or "").split())
        for author in entry_node.findall("atom:author", namespaces)
    ]
    return (
        _clean_candidate(
            {
                "title": _xml_text(entry_node, "atom:title", namespaces),
                "authors": [author for author in authors if author],
                "year": published[:4] if published else None,
                "doi": _xml_text(entry_node, "arxiv:doi", namespaces),
                "journal": "arXiv",
                "url": provider_url,
                "provider_record_id": provider_url.rsplit("/", 1)[-1] if provider_url else None,
                "provider_url": provider_url,
                "source": "arxiv",
            }
        ),
        ["arXiv candidate metadata requires human review before approval."],
        None,
    )


def _provider_candidate(
    entry: dict[str, Any],
    provider: str,
) -> tuple[dict[str, Any] | None, list[str], str | None, bool]:
    if provider == "mock_fixture":
        candidate, warnings = _mock_candidate(entry)
        return candidate, warnings, None, False
    if provider == "pubmed_optional":
        candidate, warnings, error = _optional_provider_failure(
            provider,
            "PubMed optional lookup is not implemented in this local release candidate.",
        )
        return candidate, warnings, error, True
    lookup = {
        "crossref_optional": _crossref_candidate,
        "semantic_scholar_optional": _semantic_scholar_candidate,
        "openalex_optional": _openalex_candidate,
        "arxiv_optional": _arxiv_candidate,
    }.get(provider)
    if lookup is None:
        candidate, warnings, error = _optional_provider_failure(provider, "Unknown optional provider.")
        return candidate, warnings, error, True
    try:
        candidate, warnings, error = lookup(entry)
    except Exception as exc:
        candidate, warnings, error = _optional_provider_failure(
            provider,
            f"{provider} optional lookup failed: {exc.__class__.__name__}",
        )
        return candidate, warnings, error, True
    return candidate, warnings, error, False


def _verification_status(
    entry: dict[str, Any],
    candidate: dict[str, Any] | None,
    provider_failed: bool,
    scores: dict[str, Any],
) -> str:
    if provider_failed:
        return "provider_failed"
    if not candidate:
        return "no_match"
    if entry.get("metadata_status") == "placeholder":
        return "needs_human_review"
    confidence = float(scores.get("overall_confidence") or 0.0)
    if confidence >= 0.82 and (
        scores.get("doi_match") == "match" or scores.get("title_match_score", 0) >= 0.9
    ):
        return "verified_candidate"
    if confidence >= 0.45:
        return "ambiguous_match"
    return "needs_human_review"


def _empty_candidate() -> dict[str, Any]:
    return _clean_candidate({})


def _build_result(
    index: int,
    entry: dict[str, Any],
    provider: str,
) -> dict[str, Any]:
    query = _query_from_entry(entry)
    candidate, warnings, error, provider_failed = _provider_candidate(entry, provider)

    scores = calculate_match_scores(query, candidate)
    status = _verification_status(entry, candidate, provider_failed, scores)
    return {
        "verification_id": f"ref_verify_{index:04d}",
        "literature_id": entry.get("literature_id"),
        "provider": provider,
        "query": query,
        "candidate": candidate or _empty_candidate(),
        "match_scores": scores,
        "status": status,
        "verification_status": status,
        "requires_human_approval": True,
        "applied_to_literature_index": False,
        "warnings": warnings,
        "error": error,
        "created_at": _utc_now(),
    }


def summarize_reference_verification(project_dir: Path) -> dict[str, Any]:
    results = read_reference_verification_results(project_dir)
    summary_counts = {
        "total": len(results),
        "total_records": len(results),
        "verified_candidate": 0,
        "ambiguous_match": 0,
        "no_match": 0,
        "provider_failed": 0,
        "needs_human_review": 0,
        "approved": 0,
        "rejected": 0,
    }
    provider_counts = {
        "mock_fixture": 0,
        "crossref_optional": 0,
        "semantic_scholar_optional": 0,
        "openalex_optional": 0,
        "arxiv_optional": 0,
        "pubmed_optional": 0,
    }
    for result in results:
        status = str(result.get("verification_status") or "")
        provider = str(result.get("provider") or "")
        if status in summary_counts:
            summary_counts[status] += 1
        if provider in provider_counts:
            provider_counts[provider] += 1

    approvals_path = project_dir / "literature" / "reference_approvals.jsonl"
    for approval in _read_jsonl(approvals_path):
        decision = str(approval.get("decision") or "")
        if decision == "approved":
            summary_counts["approved"] += 1
        if decision == "rejected":
            summary_counts["rejected"] += 1

    payload = {
        "generated_at": _utc_now(),
        "total": len(results),
        "total_records": len(results),
        "summary": summary_counts,
        "providers": provider_counts,
    }
    write_json(reference_verification_summary_path(project_dir), payload)
    return payload


def read_reference_verification_summary(project_dir: Path) -> dict[str, Any]:
    path = reference_verification_summary_path(project_dir)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return summarize_reference_verification(project_dir)


def run_reference_verification(
    project_dir: Path,
    project_id: str,
    provider: ReferenceProvider = "mock_fixture",
    literature_id: str | None = None,
) -> dict[str, Any]:
    if provider not in PROVIDERS:
        raise ValueError(f"unsupported reference verification provider: {provider}")
    entries = load_literature_index(project_dir)
    if literature_id:
        entries = [entry for entry in entries if entry.get("literature_id") == literature_id]
        if not entries:
            raise ValueError(f"literature_id not found: {literature_id}")

    results = [_build_result(index, entry, provider) for index, entry in enumerate(entries, start=1)]
    _write_jsonl(reference_verification_results_path(project_dir), results)
    summary = summarize_reference_verification(project_dir)
    append_audit_event(
        project_dir,
        project_id,
        "run_reference_verification",
        "Reference verification candidates were generated without modifying literature_index.json.",
        {
            "provider": provider,
            "literature_id": literature_id,
            "result_count": len(results),
            "results_file": "literature/reference_verification/reference_verification_results.jsonl",
            "summary_file": "literature/reference_verification/reference_verification_summary.json",
            "literature_index_modified": False,
        },
        source="api",
        event_category="literature",
        risk_level="low",
        entity_type="literature",
        entity_id=literature_id or "reference_verification",
    )
    return {"results": results, "summary": summary, "literature_index_modified": False}


def mark_verification_applied(project_dir: Path, verification_id: str) -> None:
    path = reference_verification_results_path(project_dir)
    results = read_reference_verification_results(project_dir)
    changed = False
    for result in results:
        if result.get("verification_id") == verification_id:
            result["applied_to_literature_index"] = True
            changed = True
    if changed:
        _write_jsonl(path, results)
        summarize_reference_verification(project_dir)
