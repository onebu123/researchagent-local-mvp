from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json
from app.tools.literature_index import read_indexed_literature_texts
from app.tools.llm_call_log import append_llm_call
from app.tools.llm_client import llm_client
from app.tools.prompt_registry import load_prompt

PROMPT_VERSION = "literature_answer_v1"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
RETRIEVAL_MODES = {"local_hybrid", "local_keyword"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def rag_dir(project_dir: Path) -> Path:
    return project_dir / "literature" / "rag"


def chunks_path(project_dir: Path) -> Path:
    return rag_dir(project_dir) / "chunks.jsonl"


def rag_index_path(project_dir: Path) -> Path:
    return rag_dir(project_dir) / "rag_index.json"


def answers_path(project_dir: Path) -> Path:
    return rag_dir(project_dir) / "rag_answers.jsonl"


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
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


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_text(text: str) -> list[tuple[int, int, str]]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    chunks: list[tuple[int, int, str]] = []
    start = 0
    while start < len(normalized):
        end = min(start + CHUNK_SIZE, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append((start, end, chunk))
        if end >= len(normalized):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", text)
        if len(token) > 2
    }


def _token_score(question_tokens: set[str], chunk: dict[str, Any]) -> float:
    chunk_tokens = set(chunk.get("tokens", []))
    if not question_tokens or not chunk_tokens:
        return 0.0
    return len(question_tokens & chunk_tokens) / max(len(question_tokens), 1)


def _ngrams(text: str, size: int = 4) -> set[str]:
    compact = re.sub(r"[^a-z0-9]+", "", text.lower())
    if len(compact) < size:
        return {compact} if compact else set()
    return {compact[index : index + size] for index in range(0, len(compact) - size + 1)}


def _ngram_score(question: str, chunk: dict[str, Any]) -> float:
    question_ngrams = _ngrams(question)
    chunk_ngrams = _ngrams(str(chunk.get("text") or ""))
    if not question_ngrams or not chunk_ngrams:
        return 0.0
    return len(question_ngrams & chunk_ngrams) / len(question_ngrams)


def _metadata_trust_score(chunk: dict[str, Any]) -> float:
    if chunk.get("metadata_status") == "verified" and bool(chunk.get("human_verified")):
        return 1.0
    if chunk.get("metadata_status") == "verified":
        return 0.7
    if chunk.get("metadata_status") == "placeholder":
        return 0.2
    return 0.4


def _lexical_diversity(chunk: dict[str, Any]) -> float:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", str(chunk.get("text") or "").lower())
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def _quality_score(chunk: dict[str, Any]) -> tuple[float, list[str]]:
    text = str(chunk.get("text") or "").strip()
    warnings: list[str] = []
    if len(text) < 120:
        warnings.append("chunk text is short")
    if _lexical_diversity(chunk) < 0.35:
        warnings.append("chunk lexical diversity is low")
    if chunk.get("metadata_status") == "placeholder":
        warnings.append("placeholder metadata reduces retrieval trust")
    score = 1.0
    score -= 0.2 if len(text) < 120 else 0.0
    score -= 0.2 if _lexical_diversity(chunk) < 0.35 else 0.0
    score -= 0.25 if chunk.get("metadata_status") == "placeholder" else 0.0
    return max(round(score, 4), 0.0), warnings


def score_chunk(question: str, chunk: dict[str, Any], retrieval_mode: str = "local_hybrid") -> dict[str, Any]:
    question_tokens = _tokens(question)
    keyword = _token_score(question_tokens, chunk)
    ngram = _ngram_score(question, chunk)
    metadata_trust = _metadata_trust_score(chunk)
    quality, warnings = _quality_score(chunk)
    if retrieval_mode == "local_keyword":
        overall = keyword
    else:
        overall = (keyword * 0.55) + (ngram * 0.25) + (metadata_trust * 0.1) + (quality * 0.1)
    matched_terms = sorted(question_tokens & set(chunk.get("tokens", [])))
    return {
        "score": round(overall, 4),
        "keyword_score": round(keyword, 4),
        "ngram_score": round(ngram, 4),
        "metadata_trust_score": round(metadata_trust, 4),
        "quality_score": round(quality, 4),
        "matched_terms": matched_terms,
        "quality_warnings": warnings,
    }


def build_literature_rag(project_dir: Path, project_id: str) -> dict[str, Any]:
    ensure_dir(rag_dir(project_dir))
    chunks: list[dict[str, Any]] = []
    for entry, text in read_indexed_literature_texts(project_dir):
        literature_id = str(entry.get("literature_id", "lit_unknown"))
        for chunk_index, (start, end, chunk_text) in enumerate(_split_text(text), start=1):
            chunk_id = f"chunk_{literature_id}_{chunk_index:04d}"
            tokens = sorted(_tokens(chunk_text))
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "literature_id": literature_id,
                    "source_file": entry.get("source_file"),
                    "parsed_text_file": entry.get("parsed_text_file"),
                    "title": entry.get("title"),
                    "source_type": entry.get("source_type"),
                    "metadata_status": entry.get("metadata_status"),
                    "human_verified": bool(entry.get("human_verified")),
                    "start_char": start,
                    "end_char": end,
                    "text": chunk_text,
                    "token_count": len(tokens),
                    "tokens": tokens,
                    "chunk_hash": _sha256(chunk_text),
                }
            )
    _write_jsonl(chunks_path(project_dir), chunks)
    prompt = load_prompt(PROMPT_VERSION)
    index = {
        "project_id": project_id,
        "created_at": _utc_now(),
        "relative_path": "literature/rag/rag_index.json",
        "chunks_file": "literature/rag/chunks.jsonl",
        "retrieval_mode": "local_hybrid",
        "supported_retrieval_modes": sorted(RETRIEVAL_MODES),
        "optional_paperqa2_enabled": False,
        "prompt_version": prompt["prompt_version"],
        "chunk_count": len(chunks),
        "literature_count": len({chunk["literature_id"] for chunk in chunks}),
        "notes": [
            "Local hybrid retrieval uses keyword overlap, character n-gram similarity, metadata trust, and chunk quality signals.",
            "No external vector database, embedding service, or PaperQA2 dependency is required.",
            "Passages are copied from local parsed literature text only.",
        ],
    }
    write_json(rag_index_path(project_dir), index)
    append_audit_event(
        project_dir,
        project_id,
        "build_literature_rag",
        "Local literature RAG index was built from parsed literature text.",
        {
            "chunk_count": len(chunks),
            "chunks_file": "literature/rag/chunks.jsonl",
            "index_file": "literature/rag/rag_index.json",
            "retrieval_mode": "local_hybrid",
        },
        source="api",
        event_category="literature",
        risk_level="low",
        entity_type="literature",
        entity_id="literature_rag",
    )
    return index


def read_rag_chunks(project_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(chunks_path(project_dir))


def read_rag_answers(project_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(answers_path(project_dir))


def _ensure_chunks(project_dir: Path, project_id: str) -> list[dict[str, Any]]:
    chunks = read_rag_chunks(project_dir)
    if chunks:
        return chunks
    build_literature_rag(project_dir, project_id)
    return read_rag_chunks(project_dir)


def retrieve_chunks(
    project_dir: Path,
    project_id: str,
    question: str,
    top_k: int = 5,
    retrieval_mode: str = "local_hybrid",
) -> list[dict[str, Any]]:
    if retrieval_mode not in RETRIEVAL_MODES:
        raise ValueError(f"unsupported retrieval_mode: {retrieval_mode}")
    chunks = _ensure_chunks(project_dir, project_id)
    scored: list[dict[str, Any]] = []
    for chunk in chunks:
        score = score_chunk(question, chunk, retrieval_mode=retrieval_mode)
        if score["score"] > 0 or score["keyword_score"] > 0 or score["ngram_score"] > 0:
            scored.append({**chunk, **score, "retrieval_mode": retrieval_mode})
    scored.sort(key=lambda item: (-float(item["score"]), str(item["chunk_id"])))
    return scored[: max(min(top_k, 10), 1)]


def _source_passages(retrieved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    passages: list[dict[str, Any]] = []
    for chunk in retrieved:
        passages.append(
            {
                "chunk_id": chunk["chunk_id"],
                "literature_id": chunk["literature_id"],
                "source_file": chunk.get("source_file"),
                "title": chunk.get("title"),
                "metadata_status": chunk.get("metadata_status"),
                "human_verified": bool(chunk.get("human_verified")),
                "score": chunk.get("score", 0),
                "score_breakdown": {
                    "keyword_score": chunk.get("keyword_score", 0),
                    "ngram_score": chunk.get("ngram_score", 0),
                    "metadata_trust_score": chunk.get("metadata_trust_score", 0),
                    "quality_score": chunk.get("quality_score", 0),
                },
                "matched_terms": chunk.get("matched_terms", []),
                "quality_warnings": chunk.get("quality_warnings", []),
                "text": chunk.get("text", ""),
            }
        )
    return passages


def ask_literature_rag(
    project_dir: Path,
    project_id: str,
    question: str,
    top_k: int = 5,
    retrieval_mode: str = "local_hybrid",
) -> dict[str, Any]:
    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("question must not be empty")
    retrieved = retrieve_chunks(
        project_dir,
        project_id,
        cleaned_question,
        top_k=top_k,
        retrieval_mode=retrieval_mode,
    )
    source_passages = _source_passages(retrieved)
    unsupported_notes: list[str] = []
    if not source_passages:
        unsupported_notes.append("No local source passage matched the question.")

    fallback = {
        "answer": (
            "Local retrieved passages mention the requested topic. Treat this as a draft "
            "literature note, not scientific proof."
            if source_passages
            else "The local literature index does not contain enough passage support to answer this question."
        ),
        "source_passages": source_passages,
        "unsupported_notes": unsupported_notes,
        "limitations": [
            "Only local parsed literature text was used.",
            "Placeholder or unverified metadata requires human review before citation.",
        ],
    }
    prompt = load_prompt(PROMPT_VERSION)
    context = [
        {
            "chunk_id": passage["chunk_id"],
            "text": passage["text"],
            "source_file": passage["source_file"],
            "metadata_status": passage["metadata_status"],
            "human_verified": passage["human_verified"],
        }
        for passage in source_passages
    ]
    messages = [
        {"role": "system", "content": prompt["content"]},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "question": cleaned_question,
                    "source_passages": context,
                    "output_schema": fallback,
                },
                ensure_ascii=False,
            ),
        },
    ]
    response = llm_client.chat_json(messages, fallback, prompt_version=PROMPT_VERSION)
    parsed = response.parsed_json if isinstance(response.parsed_json, dict) else fallback
    answer_text = str(parsed.get("answer") or fallback["answer"])
    answer_record = {
        "answer_id": f"rag_answer_{len(read_rag_answers(project_dir)) + 1:04d}",
        "created_at": _utc_now(),
        "project_id": project_id,
        "question": cleaned_question,
        "answer": answer_text,
        "source_passages": source_passages,
        "unsupported_notes": parsed.get("unsupported_notes") if source_passages else unsupported_notes,
        "limitations": parsed.get("limitations", fallback["limitations"]),
        "retrieval_mode": retrieval_mode,
        "llm_mode": response.mode,
        "prompt_version": response.prompt_version,
        "source_passage_count": len(source_passages),
        "retrieval": {
            "mode": retrieval_mode,
            "retrieval_mode": retrieval_mode,
            "top_k": top_k,
            "returned": len(source_passages),
            "quality_warnings": sorted(
                {
                    warning
                    for passage in source_passages
                    for warning in passage.get("quality_warnings", [])
                }
            ),
        },
        "llm": {
            "mode": response.mode,
            "provider": response.provider,
            "model": response.model,
            "prompt_version": response.prompt_version,
            "status": response.status,
        },
    }
    _append_jsonl(answers_path(project_dir), answer_record)
    append_llm_call(
        project_dir,
        project_id,
        "literature_rag.ask",
        messages,
        response,
        metadata={
            "answer_id": answer_record["answer_id"],
            "source_chunk_ids": [passage["chunk_id"] for passage in source_passages],
        },
    )
    append_audit_event(
        project_dir,
        project_id,
        "ask_literature_rag",
        "A local literature RAG answer draft was generated.",
        {
            "answer_id": answer_record["answer_id"],
            "source_chunk_ids": [passage["chunk_id"] for passage in source_passages],
            "unsupported": not bool(source_passages),
            "llm_mode": response.mode,
            "retrieval_mode": retrieval_mode,
        },
        source="api",
        event_category="literature",
        risk_level="low",
        entity_type="literature",
        entity_id=answer_record["answer_id"],
    )
    return answer_record
