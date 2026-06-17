from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.literature_rag import build_literature_rag, read_rag_chunks, retrieve_chunks
from app.tools.paper_writer.manuscript_contract import read_json


def _as_source_passage(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": chunk.get("chunk_id"),
        "literature_id": chunk.get("literature_id"),
        "source_file": chunk.get("source_file"),
        "title": chunk.get("title"),
        "source_locator": chunk.get("source_locator"),
        "position_label": chunk.get("position_label"),
        "metadata_trust_level": chunk.get("metadata_trust_level"),
        "parser_quality_label": chunk.get("parser_quality_label"),
        "parser_quality_score": chunk.get("parser_quality_score"),
        "evidence_warning_flags": chunk.get("evidence_warning_flags", []),
        "score": chunk.get("score", 0),
        "text": chunk.get("text", ""),
    }


def ensure_rag_chunks(project_dir: Path, project_id: str) -> list[dict[str, Any]]:
    chunks = read_rag_chunks(project_dir)
    if not chunks:
        build_literature_rag(project_dir, project_id)
        chunks = read_rag_chunks(project_dir)
    return chunks


def retrieve_section_passages(
    project_dir: Path,
    project_id: str,
    query: str,
    top_k: int = 5,
    retrieval_mode: str = "local_hybrid_fts",
) -> list[dict[str, Any]]:
    try:
        retrieved = retrieve_chunks(
            project_dir,
            project_id,
            query,
            top_k=top_k,
            retrieval_mode=retrieval_mode,
        )
    except ValueError:
        retrieved = retrieve_chunks(
            project_dir,
            project_id,
            query,
            top_k=top_k,
            retrieval_mode="local_hybrid",
        )
    return [_as_source_passage(chunk) for chunk in retrieved]


def source_passage_ids(passages: list[dict[str, Any]]) -> list[str]:
    return [str(passage.get("chunk_id")) for passage in passages if passage.get("chunk_id")]


def source_locator_summary(passages: list[dict[str, Any]], limit: int = 5) -> list[str]:
    locators = []
    for passage in passages[:limit]:
        locator = passage.get("source_locator") or passage.get("source_file") or passage.get("chunk_id")
        if locator:
            locators.append(str(locator))
    return locators


def support_status_from_passages(passages: list[dict[str, Any]]) -> str:
    if not passages:
        return "unsupported"
    best_score = max(float(passage.get("score") or 0.0) for passage in passages)
    severe_flags = {
        flag
        for passage in passages
        for flag in (passage.get("evidence_warning_flags") or [])
        if isinstance(flag, str)
    }
    all_unverified = all(
        passage.get("metadata_trust_level") in {"placeholder_or_unverified", "unknown", None}
        for passage in passages
    )
    if best_score >= 0.45 and not all_unverified and not severe_flags.intersection(
        {"failed_or_empty_parse", "low_parser_quality"}
    ):
        return "supported"
    return "weakly_supported"


def available_evidence_summary(project_dir: Path, project_id: str) -> dict[str, Any]:
    chunks = ensure_rag_chunks(project_dir, project_id)
    literature_index = read_json(project_dir / "literature" / "literature_index.json", [])
    analysis = read_json(project_dir / "analysis" / "result_summary.json", {})
    figures = read_json(project_dir / "figures" / "figure_provenance.json", [])
    return {
        "literature_count": len(literature_index) if isinstance(literature_index, list) else 0,
        "rag_chunk_count": len(chunks),
        "verified_literature_count": sum(
            1
            for item in literature_index
            if isinstance(item, dict)
            and item.get("metadata_status") == "verified"
            and item.get("human_verified") is True
        )
        if isinstance(literature_index, list)
        else 0,
        "analysis_available": bool(analysis),
        "figure_count": len(figures) if isinstance(figures, list) else 0,
        "artifact_paths": [
            path
            for path in [
                "literature/literature_index.json" if (project_dir / "literature" / "literature_index.json").exists() else None,
                "literature/rag/chunks.jsonl" if (project_dir / "literature" / "rag" / "chunks.jsonl").exists() else None,
                "analysis/result_summary.json" if (project_dir / "analysis" / "result_summary.json").exists() else None,
                "figures/figure_provenance.json" if (project_dir / "figures" / "figure_provenance.json").exists() else None,
            ]
            if path
        ],
    }
