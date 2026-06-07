from __future__ import annotations

import json
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
    "pubmed_optional",
]

PROVIDERS: set[str] = {
    "mock_fixture",
    "crossref_optional",
    "semantic_scholar_optional",
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
        {
            "title": title,
            "authors": entry.get("authors") if isinstance(entry.get("authors"), list) else [],
            "year": entry.get("year"),
            "doi": entry.get("doi"),
            "journal": entry.get("journal"),
            "url": None,
        },
        warnings,
    )


def _optional_provider_failure(provider: str) -> tuple[None, list[str], str]:
    return (
        None,
        [f"{provider} failed gracefully because optional network lookup is disabled in local MVP mode."],
        "optional provider is not configured in local MVP mode",
    )


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
    return {
        "title": None,
        "authors": [],
        "year": None,
        "doi": None,
        "journal": None,
        "url": None,
    }


def _build_result(
    index: int,
    entry: dict[str, Any],
    provider: str,
) -> dict[str, Any]:
    query = _query_from_entry(entry)
    provider_failed = False
    error: str | None = None
    if provider == "mock_fixture":
        candidate, warnings = _mock_candidate(entry)
    else:
        candidate, warnings, error = _optional_provider_failure(provider)
        provider_failed = True

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
