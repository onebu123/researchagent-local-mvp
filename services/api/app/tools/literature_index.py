from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.tools.file_tools import ensure_dir, relative_posix, write_json
from app.tools.pdf_parser import parse_pdf


LITERATURE_SUFFIXES = {".pdf", ".md", ".markdown", ".txt"}
GENERATED_NAMES = {
    "key_findings.json",
    "literature_index.json",
    "literature_review.md",
    "novelty_report.json",
}
EDITABLE_FIELDS = {
    "title",
    "authors",
    "year",
    "doi",
    "journal",
    "metadata_status",
    "human_verified",
    "reference_verification_status",
    "reference_verification_id",
}


def literature_index_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "literature_index.json"


def _source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    return "txt"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_title_from_text(path: Path, text: str) -> tuple[str, str]:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned.startswith("#"):
            title = cleaned.lstrip("#").strip()
            if title:
                return title[:180], "extracted"
        if cleaned:
            return cleaned[:180], "extracted"
    return path.stem.replace("_", " "), "placeholder"


def _is_placeholder(path: Path, text: str, metadata_status: str) -> str:
    lowered = f"{path.name}\n{text[:2000]}".lower()
    if any(marker in lowered for marker in ["placeholder", "demo", "not a verified reference"]):
        return "placeholder"
    return metadata_status


def _literature_files(literature_dir: Path) -> list[Path]:
    if not literature_dir.exists():
        return []
    files: list[Path] = []
    for path in sorted(literature_dir.iterdir()):
        if path.name in GENERATED_NAMES or path.name == "parsed":
            continue
        if path.is_file() and path.suffix.lower() in LITERATURE_SUFFIXES:
            files.append(path)
    return files


def _existing_by_source(project_dir: Path) -> dict[str, dict[str, Any]]:
    path = literature_index_path(project_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for entry in data:
        if isinstance(entry, dict) and isinstance(entry.get("source_file"), str):
            result[entry["source_file"]] = entry
    return result


def _merge_existing(entry: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
    if not existing:
        return entry
    for field in EDITABLE_FIELDS:
        if field in existing:
            entry[field] = existing[field]
    return entry


def _quality_defaults() -> dict[str, Any]:
    return {
        "quality_score": 1.0,
        "quality_label": "good",
        "needs_manual_review": False,
    }


def _pdf_entry(path: Path, project_dir: Path, literature_id: str) -> dict[str, Any]:
    metadata = parse_pdf(path, project_dir)
    parsed_path = project_dir / metadata["parsed_text_file"]
    parsed_text = _read_text(parsed_path) if parsed_path.exists() else ""
    title, status = _extract_title_from_text(path, parsed_text)
    status = _is_placeholder(path, parsed_text, status)
    if metadata["parse_status"] != "success":
        status = "placeholder"
    return {
        "literature_id": literature_id,
        "source_file": relative_posix(path, project_dir),
        "title": title or path.stem.replace("_", " "),
        "authors": [],
        "year": None,
        "doi": None,
        "journal": None,
        "source_type": "pdf",
        "parsed_text_file": metadata["parsed_text_file"],
        "parse_metadata_file": metadata["metadata_file"],
        "parse_status": metadata["parse_status"],
        "metadata_status": status,
        "human_verified": False,
        "warnings": metadata.get("warnings", []),
        "page_count": metadata.get("page_count", 0),
        "empty_page_count": metadata.get("empty_page_count", 0),
        "pages": metadata.get("pages", []),
        "quality_score": metadata.get("quality_score", 0.0),
        "quality_label": metadata.get("quality_label", "failed"),
        "needs_manual_review": metadata.get("needs_manual_review", True),
    }


def _text_entry(path: Path, project_dir: Path, literature_id: str) -> dict[str, Any]:
    text = _read_text(path)
    title, status = _extract_title_from_text(path, text)
    status = _is_placeholder(path, text, status)
    return {
        "literature_id": literature_id,
        "source_file": relative_posix(path, project_dir),
        "title": title or path.stem.replace("_", " "),
        "authors": [],
        "year": None,
        "doi": None,
        "journal": None,
        "source_type": _source_type(path),
        "parsed_text_file": relative_posix(path, project_dir),
        "parse_metadata_file": None,
        "parse_status": "success",
        "metadata_status": status,
        "human_verified": False,
        "warnings": [],
        "page_count": None,
        "empty_page_count": None,
        "pages": [],
        **_quality_defaults(),
    }


def build_literature_index(project_dir: Path) -> list[dict[str, Any]]:
    literature_dir = ensure_dir(project_dir / "literature")
    existing = _existing_by_source(project_dir)
    entries: list[dict[str, Any]] = []
    for index, path in enumerate(_literature_files(literature_dir), start=1):
        literature_id = f"lit_{index:03d}"
        if path.suffix.lower() == ".pdf":
            entry = _pdf_entry(path, project_dir, literature_id)
        else:
            entry = _text_entry(path, project_dir, literature_id)
        entries.append(_merge_existing(entry, existing.get(entry["source_file"])))
    write_json(literature_index_path(project_dir), entries)
    return entries


def load_literature_index(project_dir: Path) -> list[dict[str, Any]]:
    path = literature_index_path(project_dir)
    if not path.exists():
        return build_literature_index(project_dir)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return build_literature_index(project_dir)
    return data


def read_indexed_literature_texts(project_dir: Path) -> list[tuple[dict[str, Any], str]]:
    entries = load_literature_index(project_dir)
    result: list[tuple[dict[str, Any], str]] = []
    for entry in entries:
        parsed_text_file = entry.get("parsed_text_file")
        if not parsed_text_file:
            continue
        path = project_dir / str(parsed_text_file)
        if path.exists() and path.is_file():
            result.append((entry, _read_text(path)))
    return result
