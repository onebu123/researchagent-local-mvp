from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json
from app.tools.pdf_quality_report import generate_pdf_quality_report, load_pdf_quality_report

ALLOWED_PDF_PAGE_REVIEW_STATUSES = {
    "accepted_as_readable",
    "needs_ocr",
    "ignore_page",
    "needs_manual_check",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reviews_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "pdf_page_reviews.jsonl"


def _summary_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "pdf_page_review_summary.json"


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


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _safe_source_file(source_file: str) -> str:
    cleaned = source_file.strip().replace("\\", "/")
    if not cleaned or cleaned.startswith("/") or ".." in cleaned.split("/"):
        raise ValueError("source_file must stay inside project")
    if not cleaned.startswith("literature/") or not cleaned.lower().endswith(".pdf"):
        raise ValueError("source_file must be a literature PDF")
    return cleaned


def read_pdf_page_reviews(project_dir: Path) -> list[dict[str, Any]]:
    records = _read_jsonl(_reviews_path(project_dir))
    for record in records:
        if "page_review_id" not in record and isinstance(record.get("review_id"), str):
            record["page_review_id"] = record["review_id"]
    return records


def _quality_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    try:
        return load_pdf_quality_report(project_dir)
    except FileNotFoundError:
        return generate_pdf_quality_report(project_dir, project_id)


def _find_pdf_record(report: dict[str, Any], source_file: str) -> dict[str, Any]:
    pdfs = report.get("pdfs") if isinstance(report.get("pdfs"), list) else []
    for record in pdfs:
        if isinstance(record, dict) and record.get("source_file") == source_file:
            return record
    raise FileNotFoundError(f"PDF source_file not found in quality report: {source_file}")


def _auto_quality_signal(record: dict[str, Any], page_number: int) -> str:
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


def generate_pdf_page_review_summary(project_dir: Path) -> dict[str, Any]:
    reviews = read_pdf_page_reviews(project_dir)
    latest: dict[tuple[str, int], dict[str, Any]] = {}
    counts: dict[tuple[str, int], int] = {}
    status_counts = {status: 0 for status in ALLOWED_PDF_PAGE_REVIEW_STATUSES}
    for review in reviews:
        status = review.get("human_status")
        if isinstance(status, str) and status in status_counts:
            status_counts[status] += 1
        page_number = int(review.get("page_number") or 0)
        key = (str(review.get("source_file") or ""), page_number)
        counts[key] = counts.get(key, 0) + 1
        latest[key] = review

    pages = [
        {
            "source_file": source_file,
            "page_number": page_number,
            "auto_quality_signal": record.get("auto_quality_signal"),
            "latest_human_status": record.get("human_status"),
            "latest_reason": record.get("reason"),
            "review_count": counts[(source_file, page_number)],
        }
        for (source_file, page_number), record in sorted(latest.items())
    ]
    payload = {
        "generated_at": _utc_now(),
        "relative_path": "literature/pdf_page_review_summary.json",
        "summary": {
            "total_reviews": len(reviews),
            "accepted_as_readable": status_counts["accepted_as_readable"],
            "needs_ocr": status_counts["needs_ocr"],
            "ignore_page": status_counts["ignore_page"],
            "needs_manual_check": status_counts["needs_manual_check"],
        },
        "pages": pages,
    }
    write_json(_summary_path(project_dir), payload)
    return payload


def record_pdf_page_review(
    project_dir: Path,
    project_id: str,
    source_file: str,
    page_number: int,
    human_status: str,
    reason: str,
    *,
    source: str = "api",
) -> dict[str, Any]:
    safe_source_file = _safe_source_file(source_file)
    if human_status not in ALLOWED_PDF_PAGE_REVIEW_STATUSES:
        raise ValueError("invalid PDF page human_status")
    if page_number < 1:
        raise ValueError("page_number must be >= 1")
    if not (project_dir / safe_source_file).exists():
        raise FileNotFoundError(f"PDF source_file does not exist: {safe_source_file}")
    report = _quality_report(project_dir, project_id)
    pdf_record = _find_pdf_record(report, safe_source_file)
    page_count = int(pdf_record.get("page_count") or 0)
    if page_count and page_number > page_count:
        raise ValueError("page_number exceeds PDF page_count")

    records = read_pdf_page_reviews(project_dir)
    review_id = f"pdf_page_review_{len(records) + 1:03d}"
    record = {
        "review_id": review_id,
        "page_review_id": review_id,
        "source_file": safe_source_file,
        "page_number": page_number,
        "auto_quality_signal": _auto_quality_signal(pdf_record, page_number),
        "human_status": human_status,
        "reason": reason,
        "created_at": _utc_now(),
        "source": source,
        "ocr_attempted": False,
    }
    _append_jsonl(_reviews_path(project_dir), record)
    summary = generate_pdf_page_review_summary(project_dir)
    append_audit_event(
        project_dir,
        project_id,
        "record_pdf_page_review",
        "PDF page review status was recorded without running OCR.",
        {
            "review_id": record["review_id"],
            "page_review_id": record["page_review_id"],
            "source_file": safe_source_file,
            "page_number": page_number,
            "human_status": human_status,
            "ocr_attempted": False,
        },
        source=source,
    )
    return {**record, "summary": summary}
