from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.file_tools import ensure_dir, relative_posix, write_json, write_text


def _safe_stem(path: Path) -> str:
    stem = re.sub(r"[^0-9A-Za-z._-]+", "_", path.stem).strip("._")
    return stem or "document"


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return relative_posix(path, root)
    except ValueError:
        return path.name


def _decode_pdf_literal(value: str) -> str:
    replacements = {
        r"\(": "(",
        r"\)": ")",
        r"\\": "\\",
        r"\n": "\n",
        r"\r": "\r",
        r"\t": "\t",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def _ocr_stub() -> dict[str, Any]:
    return {
        "ocr_attempted": False,
        "ocr_engine": None,
        "ocr_status": "not_configured",
        "ocr_text_file": None,
    }


def _page_quality_signal(char_count: int) -> str:
    if char_count <= 0:
        return "empty"
    if char_count < 200:
        return "low"
    if char_count < 1000:
        return "medium"
    return "good"


def _page_record(page_number: int, text: str, warnings: list[str] | None = None) -> dict[str, Any]:
    char_count = len(text)
    page_warnings = list(warnings or [])
    if char_count == 0:
        page_warnings.append("No text extracted from this page.")
    return {
        "page_number": page_number,
        "char_count": char_count,
        "empty": char_count == 0,
        "warnings": page_warnings,
        "quality_signal": _page_quality_signal(char_count),
        "ocr": _ocr_stub(),
    }


def _fallback_page_records(text: str, page_count: int) -> list[dict[str, Any]]:
    if page_count <= 0 and text:
        page_count = 1
    records: list[dict[str, Any]] = []
    for page_number in range(1, page_count + 1):
        page_text = text if page_number == 1 else ""
        warnings = ["Page-level text split is unavailable in fallback parser."]
        records.append(_page_record(page_number, page_text.strip(), warnings))
    return records


def _parse_with_basic_reader(pdf_path: Path) -> tuple[str, int, list[dict[str, Any]], list[str]]:
    data = pdf_path.read_bytes()
    raw = data.decode("latin-1", errors="ignore")
    warnings = ["PyMuPDF unavailable or failed; used basic PDF literal fallback."]
    page_count = len(re.findall(r"/Type\s*/Page\b", raw))
    text_parts = [_decode_pdf_literal(match) for match in re.findall(r"\((.*?)\)\s*Tj", raw, re.S)]
    for array_body in re.findall(r"\[(.*?)\]\s*TJ", raw, re.S):
        text_parts.extend(
            _decode_pdf_literal(match) for match in re.findall(r"\((.*?)\)", array_body, re.S)
        )
    text = "\n".join(part.strip() for part in text_parts if part.strip())
    if not text:
        warnings.append("Fallback parser did not extract text.")
    return text, page_count, _fallback_page_records(text, page_count), warnings


def _parse_with_pymupdf(pdf_path: Path) -> tuple[str, int, list[dict[str, Any]], list[str]]:
    import fitz  # type: ignore[import-not-found]

    warnings: list[str] = []
    text_parts: list[str] = []
    pages: list[dict[str, Any]] = []
    with fitz.open(pdf_path) as document:
        page_count = document.page_count
        for index, page in enumerate(document, start=1):
            page_text = page.get_text("text").strip()
            if page_text:
                text_parts.append(page_text)
            pages.append(_page_record(index, page_text))
    text = "\n".join(text_parts)
    if not text:
        warnings.append("PyMuPDF did not extract text.")
    return text, page_count, pages, warnings


def _quality_result(
    parse_status: str,
    char_count: int,
    page_count: int,
    empty_page_count: int,
    extraction_method: str,
    warnings: list[str],
) -> dict[str, Any]:
    if parse_status != "success":
        return {
            "text_length": char_count,
            "empty_page_count": empty_page_count,
            "extraction_method": extraction_method,
            "warning_count": len(warnings),
            "quality_score": 0.0,
            "quality_label": "failed",
            "needs_manual_review": True,
        }

    score = 1.0
    if char_count < 200:
        score -= 0.35
    elif char_count < 1000:
        score -= 0.15

    if page_count > 0:
        empty_ratio = empty_page_count / page_count
        score -= min(0.4, empty_ratio * 0.4)

    if extraction_method == "fallback":
        score -= 0.2

    score -= min(0.3, len(warnings) * 0.08)
    score = round(max(0.0, min(1.0, score)), 3)

    if score < 0.45:
        label = "low"
    elif score < 0.75:
        label = "medium"
    else:
        label = "good"

    return {
        "text_length": char_count,
        "empty_page_count": empty_page_count,
        "extraction_method": extraction_method,
        "warning_count": len(warnings),
        "quality_score": score,
        "quality_label": label,
        "needs_manual_review": label in {"low", "failed"},
    }


def parse_pdf(pdf_path: Path, project_dir: Path) -> dict[str, Any]:
    literature_dir = pdf_path.parent
    parsed_dir = ensure_dir(literature_dir / "parsed")
    stem = _safe_stem(pdf_path)
    parsed_text_path = parsed_dir / f"{stem}.txt"
    metadata_path = parsed_dir / f"{stem}.metadata.json"
    warnings: list[str] = []
    parser_name = "unsupported"
    extraction_method = "unsupported"
    page_count = 0
    pages: list[dict[str, Any]] = []
    text = ""
    parse_status = "failed"

    if not pdf_path.exists():
        warnings.append("PDF file does not exist.")
        extraction_method = "failed"
    elif pdf_path.suffix.lower() != ".pdf":
        warnings.append("File suffix is not PDF.")
        parse_status = "unsupported"
    else:
        try:
            text, page_count, pages, warnings = _parse_with_pymupdf(pdf_path)
            parser_name = "pymupdf"
            extraction_method = "pymupdf"
            parse_status = "success" if text.strip() else "failed"
        except Exception as exc:
            try:
                text, page_count, pages, fallback_warnings = _parse_with_basic_reader(
                    pdf_path
                )
                parser_name = "basic-pdf-literal-fallback"
                extraction_method = "fallback"
                warnings = [f"PyMuPDF parse failed: {exc.__class__.__name__}.", *fallback_warnings]
                parse_status = "success" if text.strip() else "failed"
            except Exception as fallback_exc:
                parser_name = "unsupported"
                extraction_method = "failed"
                warnings = [
                    f"PyMuPDF parse failed: {exc.__class__.__name__}.",
                    f"Fallback parse failed: {fallback_exc.__class__.__name__}.",
                ]
                parse_status = "failed"

    write_text(parsed_text_path, text)
    char_count = len(text)
    empty_page_count = sum(
        1 for page in pages if isinstance(page, dict) and page.get("empty") is True
    )
    quality = _quality_result(
        parse_status,
        char_count,
        page_count,
        empty_page_count,
        extraction_method,
        warnings,
    )
    metadata = {
        "source_file": _safe_relative(pdf_path, project_dir),
        "parsed_text_file": _safe_relative(parsed_text_path, project_dir),
        "metadata_file": _safe_relative(metadata_path, project_dir),
        "parser": parser_name,
        "page_count": page_count,
        "char_count": char_count,
        "parse_status": parse_status,
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "warnings": warnings,
        "pages": pages,
        **quality,
    }
    write_json(metadata_path, metadata)
    return metadata
