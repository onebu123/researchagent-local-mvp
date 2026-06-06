from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.literature_index import load_literature_index
from app.tools.pdf_page_review import read_pdf_page_reviews
from app.tools.pdf_quality_report import generate_pdf_quality_report, load_pdf_quality_report


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "pdf_page_text_previews.json"


def _safe_source_file(source_file: str) -> str:
    cleaned = source_file.strip().replace("\\", "/")
    if not cleaned or cleaned.startswith("/") or ".." in cleaned.split("/"):
        raise ValueError("source_file must stay inside project")
    if not cleaned.startswith("literature/") or not cleaned.lower().endswith(".pdf"):
        raise ValueError("source_file must be a literature PDF")
    return cleaned


def _read_text(project_dir: Path, relative_path: str | None) -> str:
    if not relative_path:
        return ""
    path = project_dir / relative_path
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _quality_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    try:
        return load_pdf_quality_report(project_dir)
    except FileNotFoundError:
        return generate_pdf_quality_report(project_dir, project_id)


def _quality_by_source(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pdfs = report.get("pdfs") if isinstance(report.get("pdfs"), list) else []
    return {
        str(record.get("source_file")): record
        for record in pdfs
        if isinstance(record, dict) and isinstance(record.get("source_file"), str)
    }


def _auto_signal(record: dict[str, Any], page_number: int, page: dict[str, Any] | None) -> str:
    if page and isinstance(page.get("quality_signal"), str):
        return str(page["quality_signal"])
    if page_number in set(record.get("empty_pages") or []):
        return "empty"
    if page_number in set(record.get("suspected_scanned_pages") or []):
        return "suspected_scanned"
    if page_number in set(record.get("low_quality_pages") or []):
        return "low"
    categories = record.get("issue_categories") if isinstance(record.get("issue_categories"), dict) else {}
    if categories.get("ocr_not_configured"):
        return "ocr_not_configured"
    return "normal"


def _latest_page_reviews(project_dir: Path) -> dict[tuple[str, int], dict[str, Any]]:
    latest: dict[tuple[str, int], dict[str, Any]] = {}
    for review in read_pdf_page_reviews(project_dir):
        source_file = str(review.get("source_file") or "")
        page_number = int(review.get("page_number") or 0)
        latest[(source_file, page_number)] = review
    return latest


def _page_preview_text(
    project_dir: Path,
    entry: dict[str, Any],
    page: dict[str, Any] | None,
    page_number: int,
    page_count: int,
) -> tuple[str, str, list[str]]:
    warnings: list[str] = []
    if page and isinstance(page.get("text_preview"), str):
        return page["text_preview"][:500], "available", warnings
    if page and isinstance(page.get("text_file"), str):
        text = _read_text(project_dir, page["text_file"])
        return text[:500], "available" if text else "empty", warnings

    parsed_text = _read_text(project_dir, entry.get("parsed_text_file"))
    if not parsed_text:
        warnings.append("Parsed text file is missing or empty; no OCR was attempted.")
        return "", "not_parsed", warnings
    if page_count <= 1 or page_number == 1:
        return parsed_text[:500], "available", warnings
    warnings.append("Page-level parsed text is unavailable in fallback parser; no OCR was attempted.")
    return "", "not_parsed", warnings


def generate_pdf_page_text_preview(
    project_dir: Path,
    project_id: str,
    *,
    source_file: str | None = None,
    page_number: int | None = None,
) -> dict[str, Any]:
    safe_source_file = _safe_source_file(source_file) if source_file else None
    if page_number is not None and page_number < 1:
        raise ValueError("page_number must be >= 1")

    entries = [
        entry
        for entry in load_literature_index(project_dir)
        if isinstance(entry, dict) and entry.get("source_type") == "pdf"
    ]
    report = _quality_report(project_dir, project_id)
    quality_by_source = _quality_by_source(report)
    latest_reviews = _latest_page_reviews(project_dir)
    pages: list[dict[str, Any]] = []

    for entry in entries:
        entry_source = str(entry.get("source_file") or "")
        if safe_source_file and entry_source != safe_source_file:
            continue
        if not entry_source:
            continue
        quality = quality_by_source.get(entry_source, {})
        page_records = entry.get("pages") if isinstance(entry.get("pages"), list) else []
        page_records = [item for item in page_records if isinstance(item, dict)]
        page_count = int(entry.get("page_count") or quality.get("page_count") or len(page_records) or 0)
        if page_number is not None and page_count and page_number > page_count:
            raise ValueError("page_number exceeds PDF page_count")
        page_range = [page_number] if page_number is not None else list(range(1, max(page_count, 1) + 1))
        for current_page_number in page_range:
            page = next(
                (
                    item
                    for item in page_records
                    if int(item.get("page_number") or 0) == current_page_number
                ),
                None,
            )
            text_preview, parse_status, warnings = _page_preview_text(
                project_dir,
                entry,
                page,
                current_page_number,
                page_count,
            )
            review = latest_reviews.get((entry_source, current_page_number))
            pages.append(
                {
                    "source_file": entry_source,
                    "literature_id": entry.get("literature_id"),
                    "page_number": current_page_number,
                    "char_count": int(page.get("char_count") or 0) if page else len(text_preview),
                    "text_preview": text_preview,
                    "parse_status": parse_status,
                    "auto_quality_signal": _auto_signal(quality, current_page_number, page),
                    "human_status": review.get("human_status") if review else "needs_manual_check",
                    "ocr_attempted": False,
                    "warnings": warnings + list(page.get("warnings") or []) if page else warnings,
                }
            )

    if safe_source_file and not pages:
        raise FileNotFoundError(f"PDF source_file not found in literature index: {safe_source_file}")

    payload = {
        "generated_at": _utc_now(),
        "relative_path": "literature/pdf_page_text_previews.json",
        "summary": {
            "pdf_count": len({page["source_file"] for page in pages}),
            "page_count": len(pages),
            "ocr_attempted": False,
        },
        "pages": pages,
        "notes": ["Preview uses existing parsed text and metadata only. No OCR was attempted."],
    }
    write_json(_preview_path(project_dir), payload)
    append_audit_event(
        project_dir,
        project_id,
        "generate_pdf_page_text_preview",
        "PDF page text preview was generated from existing parsed text without OCR.",
        {
            "preview_file": "literature/pdf_page_text_previews.json",
            "page_count": len(pages),
            "ocr_attempted": False,
        },
        source="api",
        event_category="trust",
        risk_level="low",
        entity_type="pdf_page",
        entity_id=safe_source_file or "pdf_page_text_preview",
    )
    return payload
