from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import relative_posix, write_json
from app.tools.literature_index import load_literature_index


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def pdf_quality_report_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "pdf_quality_report.json"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _page_number(page: dict[str, Any], fallback: int) -> int:
    value = page.get("page_number")
    return int(value) if isinstance(value, int) and value > 0 else fallback


def _char_count(page: dict[str, Any]) -> int:
    value = page.get("char_count")
    return int(value) if isinstance(value, int) and value >= 0 else 0


def _issue_categories(
    pages: list[dict[str, Any]],
    metadata: dict[str, Any],
    page_count: int,
) -> dict[str, int]:
    warning_count = len(metadata.get("warnings") or [])
    return {
        "low_text": sum(1 for page in pages if 0 < _char_count(page) < 200),
        "empty_page": sum(1 for page in pages if page.get("empty") is True or _char_count(page) == 0),
        "fallback_parser": 1
        if metadata.get("extraction_method") == "fallback"
        or str(metadata.get("parser") or "").lower().startswith("basic")
        else 0,
        "many_warnings": 1 if warning_count >= 3 else 0,
        "ocr_not_configured": sum(
            1
            for page in pages
            if isinstance(page.get("ocr"), dict)
            and page["ocr"].get("ocr_status") == "not_configured"
        )
        or page_count,
    }


def _recommended_action(
    quality_label: str,
    low_quality_pages: list[int],
    suspected_scanned_pages: list[int],
) -> str:
    if quality_label in {"failed", "low"}:
        return "manual_check_required"
    if suspected_scanned_pages:
        return "manual_check_suspected_scanned_pages"
    if low_quality_pages:
        return "manual_check_low_quality_pages"
    return "no_action"


def _pdf_record(project_dir: Path, entry: dict[str, Any]) -> dict[str, Any]:
    metadata_file = entry.get("parse_metadata_file")
    metadata: dict[str, Any] = {}
    if isinstance(metadata_file, str) and metadata_file:
        metadata_path = project_dir / metadata_file
        metadata_payload = _read_json(metadata_path, {})
        if isinstance(metadata_payload, dict):
            metadata = metadata_payload

    pages = metadata.get("pages") if isinstance(metadata.get("pages"), list) else entry.get("pages")
    pages = [page for page in pages if isinstance(page, dict)] if isinstance(pages, list) else []
    page_count = int(metadata.get("page_count") or entry.get("page_count") or len(pages) or 0)
    quality_label = str(metadata.get("quality_label") or entry.get("quality_label") or "failed")
    quality_score = float(metadata.get("quality_score") or entry.get("quality_score") or 0.0)

    low_quality_pages = [
        _page_number(page, index)
        for index, page in enumerate(pages, start=1)
        if _char_count(page) < 200 or page.get("quality_signal") in {"empty", "low"}
    ]
    empty_pages = [
        _page_number(page, index)
        for index, page in enumerate(pages, start=1)
        if page.get("empty") is True or _char_count(page) == 0
    ]
    suspected_scanned_pages = [
        _page_number(page, index)
        for index, page in enumerate(pages, start=1)
        if page_count > 0 and _char_count(page) < 20
    ]
    issue_categories = _issue_categories(pages, metadata, page_count)
    warnings = list(metadata.get("warnings") or entry.get("warnings") or [])
    if issue_categories["ocr_not_configured"] > 0:
        warnings.append("OCR is not configured; no OCR fallback was executed.")

    source_file = str(entry.get("source_file") or metadata.get("source_file") or "")
    return {
        "source_file": source_file,
        "metadata_file": str(metadata_file or metadata.get("metadata_file") or ""),
        "quality_label": quality_label,
        "quality_score": round(quality_score, 3),
        "page_count": page_count,
        "low_quality_pages": sorted(set(low_quality_pages)),
        "empty_pages": sorted(set(empty_pages)),
        "suspected_scanned_pages": sorted(set(suspected_scanned_pages)),
        "issue_categories": issue_categories,
        "recommended_action": _recommended_action(
            quality_label,
            low_quality_pages,
            suspected_scanned_pages,
        ),
        "ocr_attempted": False,
        "warnings": list(dict.fromkeys(warnings)),
    }


def generate_pdf_quality_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    entries = load_literature_index(project_dir)
    pdfs = [
        _pdf_record(project_dir, entry)
        for entry in entries
        if isinstance(entry, dict) and entry.get("source_type") == "pdf"
    ]
    summary = {
        "pdf_count": len(pdfs),
        "low_quality_pdf_count": sum(
            1 for record in pdfs if record["quality_label"] in {"low", "failed"}
        ),
        "pages_requiring_review": sum(
            len(set(record["low_quality_pages"]) | set(record["suspected_scanned_pages"]))
            for record in pdfs
        ),
    }
    payload = {
        "generated_at": _utc_now(),
        "relative_path": relative_posix(pdf_quality_report_path(project_dir), project_dir),
        "pdfs": pdfs,
        "summary": summary,
    }
    write_json(pdf_quality_report_path(project_dir), payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_pdf_quality_report",
        "PDF page quality report was generated without running OCR.",
        {
            "report_file": "literature/pdf_quality_report.json",
            "pdf_count": summary["pdf_count"],
            "pages_requiring_review": summary["pages_requiring_review"],
            "ocr_attempted": False,
        },
        source="api",
    )
    return payload


def load_pdf_quality_report(project_dir: Path) -> dict[str, Any]:
    path = pdf_quality_report_path(project_dir)
    if not path.exists():
        raise FileNotFoundError("literature/pdf_quality_report.json does not exist")
    payload = _read_json(path, {})
    if not isinstance(payload, dict):
        raise ValueError("pdf_quality_report.json must be an object")
    return payload

