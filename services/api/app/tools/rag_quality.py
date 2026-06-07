from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import write_json
from app.tools.literature_rag import build_literature_rag, rag_dir, read_rag_chunks, retrieve_chunks


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def chunk_quality_report_path(project_dir: Path) -> Path:
    return rag_dir(project_dir) / "chunk_quality_report.json"


def retrieval_eval_set_path(project_dir: Path) -> Path:
    return rag_dir(project_dir) / "retrieval_eval_set.json"


def retrieval_eval_report_path(project_dir: Path) -> Path:
    return rag_dir(project_dir) / "retrieval_eval_report.json"


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", text.lower())


def _lexical_diversity(text: str) -> float:
    words = _words(text)
    if not words:
        return 0.0
    return round(len(set(words)) / len(words), 4)


def _quality_status(score: float) -> str:
    if score >= 0.8:
        return "ok"
    if score >= 0.55:
        return "needs_review"
    return "poor"


def _chunk_quality(chunk: dict[str, Any]) -> dict[str, Any]:
    text = str(chunk.get("text") or "")
    token_count = len(chunk.get("tokens") or [])
    lexical_diversity = _lexical_diversity(text)
    warnings: list[str] = []
    if not text.strip():
        warnings.append("chunk text is empty")
    if len(text.strip()) < 120:
        warnings.append("chunk text is short")
    if token_count < 8:
        warnings.append("chunk has few searchable tokens")
    if lexical_diversity < 0.35:
        warnings.append("chunk lexical diversity is low")
    if chunk.get("metadata_status") == "placeholder":
        warnings.append("placeholder metadata reduces retrieval trust")

    score = 1.0
    score -= 0.3 if not text.strip() else 0.0
    score -= 0.15 if len(text.strip()) < 120 else 0.0
    score -= 0.15 if token_count < 8 else 0.0
    score -= 0.15 if lexical_diversity < 0.35 else 0.0
    score -= 0.2 if chunk.get("metadata_status") == "placeholder" else 0.0
    score = max(round(score, 4), 0.0)

    return {
        "chunk_id": chunk.get("chunk_id"),
        "literature_id": chunk.get("literature_id"),
        "source_file": chunk.get("source_file"),
        "title": chunk.get("title"),
        "metadata_status": chunk.get("metadata_status"),
        "human_verified": bool(chunk.get("human_verified")),
        "character_count": len(text),
        "token_count": token_count,
        "lexical_diversity": lexical_diversity,
        "quality_score": score,
        "quality_status": _quality_status(score),
        "warnings": warnings,
    }


def generate_chunk_quality_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    chunks = read_rag_chunks(project_dir)
    if not chunks:
        build_literature_rag(project_dir, project_id)
        chunks = read_rag_chunks(project_dir)

    items = [_chunk_quality(chunk) for chunk in chunks]
    summary = {
        "total_chunks": len(items),
        "ok": sum(1 for item in items if item["quality_status"] == "ok"),
        "needs_review": sum(1 for item in items if item["quality_status"] == "needs_review"),
        "poor": sum(1 for item in items if item["quality_status"] == "poor"),
        "placeholder_metadata": sum(1 for item in items if item["metadata_status"] == "placeholder"),
        "average_quality_score": round(
            sum(float(item["quality_score"]) for item in items) / len(items), 4
        )
        if items
        else 0.0,
    }
    report = {
        "generated_at": _utc_now(),
        "relative_path": "literature/rag/chunk_quality_report.json",
        "chunks_file": "literature/rag/chunks.jsonl",
        "summary": summary,
        "items": items,
        "limitations": [
            "Chunk quality is a local heuristic for retrieval review, not a scientific quality claim.",
            "Placeholder metadata requires human review before citation use.",
        ],
    }
    write_json(chunk_quality_report_path(project_dir), report)
    append_audit_event(
        project_dir,
        project_id,
        "generate_rag_chunk_quality",
        "RAG chunk quality report was generated from local parsed literature text.",
        {
            "report_file": "literature/rag/chunk_quality_report.json",
            "chunk_count": len(items),
            "poor_chunks": summary["poor"],
        },
        source="api",
        event_category="literature",
        risk_level="low",
        entity_type="literature",
        entity_id="rag_quality",
    )
    return report


def read_chunk_quality_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    path = chunk_quality_report_path(project_dir)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return generate_chunk_quality_report(project_dir, project_id)


def generate_retrieval_eval_set(project_dir: Path, project_id: str) -> dict[str, Any]:
    chunks = read_rag_chunks(project_dir)
    if not chunks:
        build_literature_rag(project_dir, project_id)
        chunks = read_rag_chunks(project_dir)

    cases: list[dict[str, Any]] = []
    seen_literature: set[str] = set()
    for chunk in chunks:
        literature_id = str(chunk.get("literature_id") or "")
        if not literature_id or literature_id in seen_literature:
            continue
        terms = list(chunk.get("tokens") or [])[:6]
        if not terms:
            continue
        seen_literature.add(literature_id)
        cases.append(
            {
                "case_id": f"rag_eval_{len(cases) + 1:04d}",
                "query": " ".join(terms),
                "expected_literature_id": literature_id,
                "expected_chunk_id": chunk.get("chunk_id"),
                "source": "local_chunk_tokens",
                "notes": [
                    "This eval case is generated from local parsed text and checks retrieval behavior only."
                ],
            }
        )
        if len(cases) >= 5:
            break

    payload = {
        "generated_at": _utc_now(),
        "relative_path": "literature/rag/retrieval_eval_set.json",
        "retrieval_mode": "local_hybrid",
        "cases": cases,
        "limitations": [
            "Eval cases are local smoke checks and do not represent benchmark-grade retrieval quality."
        ],
    }
    write_json(retrieval_eval_set_path(project_dir), payload)
    return payload


def read_retrieval_eval_set(project_dir: Path, project_id: str) -> dict[str, Any]:
    path = retrieval_eval_set_path(project_dir)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return generate_retrieval_eval_set(project_dir, project_id)


def generate_retrieval_eval_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    eval_set = read_retrieval_eval_set(project_dir, project_id)
    cases = eval_set.get("cases") if isinstance(eval_set, dict) else []
    results: list[dict[str, Any]] = []
    reciprocal_ranks: list[float] = []

    for case in cases if isinstance(cases, list) else []:
        query = str(case.get("query") or "")
        expected_chunk_id = str(case.get("expected_chunk_id") or "")
        expected_literature_id = str(case.get("expected_literature_id") or "")
        retrieved = retrieve_chunks(project_dir, project_id, query, top_k=5, retrieval_mode="local_hybrid")
        retrieved_ids = [str(item.get("chunk_id") or "") for item in retrieved]
        retrieved_literature_ids = [str(item.get("literature_id") or "") for item in retrieved]
        rank = retrieved_ids.index(expected_chunk_id) + 1 if expected_chunk_id in retrieved_ids else None
        literature_rank = (
            retrieved_literature_ids.index(expected_literature_id) + 1
            if expected_literature_id in retrieved_literature_ids
            else None
        )
        effective_rank = rank or literature_rank
        reciprocal_ranks.append(1.0 / effective_rank if effective_rank else 0.0)
        results.append(
            {
                "case_id": case.get("case_id"),
                "query": query,
                "expected_chunk_id": expected_chunk_id,
                "expected_literature_id": expected_literature_id,
                "top_chunk_ids": retrieved_ids,
                "top_literature_ids": retrieved_literature_ids,
                "hit_at_1": bool(effective_rank == 1),
                "hit_at_3": bool(effective_rank and effective_rank <= 3),
                "rank": effective_rank,
                "top_score": retrieved[0].get("score") if retrieved else 0,
                "top_score_breakdown": {
                    "keyword_score": retrieved[0].get("keyword_score", 0) if retrieved else 0,
                    "ngram_score": retrieved[0].get("ngram_score", 0) if retrieved else 0,
                    "metadata_trust_score": retrieved[0].get("metadata_trust_score", 0) if retrieved else 0,
                    "quality_score": retrieved[0].get("quality_score", 0) if retrieved else 0,
                },
            }
        )

    total = len(results)
    metrics = {
        "total_cases": total,
        "hit_at_1": round(sum(1 for result in results if result["hit_at_1"]) / total, 4)
        if total
        else 0.0,
        "hit_at_3": round(sum(1 for result in results if result["hit_at_3"]) / total, 4)
        if total
        else 0.0,
        "mean_reciprocal_rank": round(sum(reciprocal_ranks) / total, 4) if total else 0.0,
    }
    report = {
        "generated_at": _utc_now(),
        "relative_path": "literature/rag/retrieval_eval_report.json",
        "eval_set_file": "literature/rag/retrieval_eval_set.json",
        "retrieval_mode": "local_hybrid",
        "metrics": metrics,
        "results": results,
        "limitations": [
            "Retrieval evaluation uses local deterministic smoke cases only.",
            "Metrics do not prove scientific correctness or production retrieval quality.",
        ],
    }
    write_json(retrieval_eval_report_path(project_dir), report)
    append_audit_event(
        project_dir,
        project_id,
        "evaluate_rag_retrieval",
        "Local hybrid retrieval evaluation was generated.",
        {
            "report_file": "literature/rag/retrieval_eval_report.json",
            "total_cases": total,
            "hit_at_3": metrics["hit_at_3"],
        },
        source="api",
        event_category="literature",
        risk_level="low",
        entity_type="literature",
        entity_id="rag_evaluation",
    )
    return report


def read_retrieval_eval_report(project_dir: Path, project_id: str) -> dict[str, Any]:
    path = retrieval_eval_report_path(project_dir)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return generate_retrieval_eval_report(project_dir, project_id)
