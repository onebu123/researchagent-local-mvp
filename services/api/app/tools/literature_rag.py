from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools import llm_client as llm_client_module
from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json
from app.tools.literature_index import read_indexed_literature_texts
from app.tools.literature_search import build_literature_fts_index, search_literature_fts
from app.tools.llm_call_log import append_llm_call
from app.tools.prompt_registry import load_prompt

PROMPT_VERSION = "literature_answer_v1"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
RETRIEVAL_MODES = {"local_hybrid", "local_keyword", "local_fts", "local_hybrid_fts"}
FTS_RETRIEVAL_MODES = {"local_fts", "local_hybrid_fts"}
MINIMUM_SUPPORT_SCORE = 0.2
STRONG_SUPPORT_SCORE = 0.45
RESTRICTED_UNSUPPORTED_TERMS = [
    "statistically significant",
    "significant",
    "p-value",
    "p values",
    "p-values",
    "causal",
    "causality",
    "proves",
    "proved",
    "demonstrated",
    "confirmed",
    "显著",
    "证明",
    "证实",
    "因果",
]


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


def _metadata_trust_level(chunk: dict[str, Any]) -> str:
    if chunk.get("metadata_status") == "verified" and bool(chunk.get("human_verified")):
        return "human_verified"
    if chunk.get("metadata_status") == "verified":
        return "verified_metadata_unreviewed"
    if chunk.get("metadata_status") in {"placeholder", "extracted"}:
        return "placeholder_or_unverified"
    return "unknown"


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


def _evidence_warning_flags(chunk: dict[str, Any], quality_warnings: list[str]) -> list[str]:
    flags: set[str] = set()
    text = str(chunk.get("text") or "").strip()
    metadata_status = str(chunk.get("metadata_status") or "")
    parse_status = str(chunk.get("parse_status") or "success")
    quality_score = chunk.get("parser_quality_score")
    if quality_score is None:
        quality_score = chunk.get("quality_score")
    quality_label = str(chunk.get("parser_quality_label") or chunk.get("quality_label") or "")

    if metadata_status == "placeholder":
        flags.add("placeholder_metadata")
    if metadata_status != "verified" or not bool(chunk.get("human_verified")):
        flags.add("unverified_metadata")
    if quality_label == "low" or (isinstance(quality_score, (int, float)) and float(quality_score) < 0.45):
        flags.add("low_parser_quality")
    if parse_status not in {"success", "ok"} or not text:
        flags.add("failed_or_empty_parse")
    if len(text) < 120:
        flags.add("short_chunk")
    if any("lexical diversity" in warning for warning in quality_warnings):
        flags.add("low_lexical_diversity")
    return sorted(flags)


def score_chunk(
    question: str,
    chunk: dict[str, Any],
    retrieval_mode: str = "local_hybrid",
    fts_match: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question_tokens = _tokens(question)
    keyword = _token_score(question_tokens, chunk)
    ngram = _ngram_score(question, chunk)
    metadata_trust = _metadata_trust_score(chunk)
    quality, warnings = _quality_score(chunk)
    fts_score = float((fts_match or {}).get("fts_score") or 0.0)
    bm25_score = float((fts_match or {}).get("bm25_score") or 0.0)
    if retrieval_mode == "local_keyword":
        overall = keyword
    elif retrieval_mode == "local_fts":
        overall = fts_score
    elif retrieval_mode == "local_hybrid_fts":
        local_hybrid = (keyword * 0.55) + (ngram * 0.25) + (metadata_trust * 0.1) + (quality * 0.1)
        overall = (local_hybrid * 0.75) + (fts_score * 0.25)
    else:
        overall = (keyword * 0.55) + (ngram * 0.25) + (metadata_trust * 0.1) + (quality * 0.1)
    matched_terms = sorted(question_tokens & set(chunk.get("tokens", [])))
    fts_matched_terms = [
        str(term)
        for term in (fts_match or {}).get("fts_matched_terms", [])
        if isinstance(term, str)
    ]
    return {
        "score": round(overall, 4),
        "keyword_score": round(keyword, 4),
        "ngram_score": round(ngram, 4),
        "fts_score": round(fts_score, 4),
        "bm25_score": round(bm25_score, 6),
        "metadata_trust_score": round(metadata_trust, 4),
        "quality_score": round(quality, 4),
        "matched_terms": sorted(set(matched_terms + fts_matched_terms)),
        "quality_warnings": warnings,
        "fts_rank": (fts_match or {}).get("fts_rank"),
        "fts_index_kind": (fts_match or {}).get("fts_index_kind"),
    }



def _source_locator(source_file: str | None, page_start: int | None, start: int, end: int) -> str:
    source = source_file or "unknown_source"
    if page_start is not None:
        return f"{source}#page={page_start}"
    return f"{source}#char={start}-{end}"


def _chunk_position_fields(entry: dict[str, Any], start: int, end: int) -> dict[str, Any]:
    source_file = entry.get("source_file")
    pages = [page for page in entry.get("pages", []) if isinstance(page, dict)]
    overlapping: list[dict[str, Any]] = []
    for page in pages:
        page_start = page.get("char_start")
        page_end = page.get("char_end")
        if not isinstance(page_start, int) or not isinstance(page_end, int):
            continue
        if page_end >= start and page_start <= end:
            overlapping.append(page)
    if overlapping:
        page_numbers = [int(page.get("page_number")) for page in overlapping if page.get("page_number")]
        if page_numbers:
            page_start = min(page_numbers)
            page_end = max(page_numbers)
            label = f"page {page_start}" if page_start == page_end else f"pages {page_start}-{page_end}"
            return {
                "page_start": page_start,
                "page_end": page_end,
                "page_quality_signals": sorted(
                    {
                        str(page.get("quality_signal"))
                        for page in overlapping
                        if page.get("quality_signal")
                    }
                ),
                "position_label": label,
                "source_locator": _source_locator(str(source_file) if source_file else None, page_start, start, end),
            }
    return {
        "page_start": None,
        "page_end": None,
        "page_quality_signals": [],
        "position_label": f"char {start}-{end}",
        "source_locator": _source_locator(str(source_file) if source_file else None, None, start, end),
    }


def _restricted_term_hits(text: str) -> list[str]:
    lowered = text.lower()
    hits: list[str] = []
    for term in RESTRICTED_UNSUPPORTED_TERMS:
        if term.isascii():
            if re.search(r"\b" + re.escape(term.lower()) + r"\b", lowered):
                hits.append(term)
        elif term in text:
            hits.append(term)
    return sorted(set(hits))


def _safe_fallback_answer(answer_support_status: str) -> str:
    if answer_support_status == "unsupported":
        return "The local literature index does not contain enough passage support to answer this question."
    if answer_support_status == "weakly_supported":
        return (
            "Local passages weakly mention the requested topic, but metadata verification or parser quality "
            "limits support strength. Treat this as a draft note that requires human review."
        )
    return "Local retrieved passages support a cautious draft answer. Treat this as a source-grounded note, not scientific proof."


def _sanitize_answer_text(answer_text: str, answer_support_status: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    cleaned = answer_text.strip() or _safe_fallback_answer(answer_support_status)
    restricted_hits = _restricted_term_hits(cleaned)
    if answer_support_status == "unsupported":
        if restricted_hits:
            notes.append(
                "LLM or fallback answer contained strong conclusion wording and was replaced by a safe unsupported response."
            )
        if "not contain enough passage support" not in cleaned.lower() and "insufficient" not in cleaned.lower():
            notes.append("Unsupported answer was replaced because it did not clearly state insufficient support.")
        return _safe_fallback_answer("unsupported"), notes
    if answer_support_status == "weakly_supported" and restricted_hits:
        notes.append(
            "Weakly supported answer contained strong conclusion wording and was replaced by a cautious response."
        )
        return _safe_fallback_answer("weakly_supported"), notes
    return cleaned, notes

def build_literature_rag(project_dir: Path, project_id: str) -> dict[str, Any]:
    ensure_dir(rag_dir(project_dir))
    chunks: list[dict[str, Any]] = []
    for entry, text in read_indexed_literature_texts(project_dir):
        literature_id = str(entry.get("literature_id", "lit_unknown"))
        for chunk_index, (start, end, chunk_text) in enumerate(_split_text(text), start=1):
            chunk_id = f"chunk_{literature_id}_{chunk_index:04d}"
            tokens = sorted(_tokens(chunk_text))
            position_fields = _chunk_position_fields(entry, start, end)
            chunk = {
                "chunk_id": chunk_id,
                "literature_id": literature_id,
                "source_file": entry.get("source_file"),
                "parsed_text_file": entry.get("parsed_text_file"),
                "title": entry.get("title"),
                "source_type": entry.get("source_type"),
                "metadata_status": entry.get("metadata_status"),
                "human_verified": bool(entry.get("human_verified")),
                "parse_status": entry.get("parse_status", "success"),
                "parser_quality_label": entry.get("quality_label"),
                "parser_quality_score": entry.get("quality_score"),
                "start_char": start,
                "end_char": end,
                **position_fields,
                "metadata_trust_level": _metadata_trust_level(entry),
                "text": chunk_text,
                "token_count": len(tokens),
                "tokens": tokens,
                "chunk_hash": _sha256(chunk_text),
            }
            _chunk_quality, chunk_quality_warnings = _quality_score(chunk)
            chunk["evidence_warning_flags"] = _evidence_warning_flags(chunk, chunk_quality_warnings)
            chunks.append(chunk)
    _write_jsonl(chunks_path(project_dir), chunks)
    fts_index = build_literature_fts_index(project_dir, chunks)
    prompt = load_prompt(PROMPT_VERSION)
    index = {
        "project_id": project_id,
        "created_at": _utc_now(),
        "relative_path": "literature/rag/rag_index.json",
        "chunks_file": "literature/rag/chunks.jsonl",
        "fts_index_file": fts_index["relative_path"],
        "fts_index_kind": fts_index["index_kind"],
        "retrieval_mode": "local_hybrid",
        "supported_retrieval_modes": sorted(RETRIEVAL_MODES),
        "optional_paperqa2_enabled": False,
        "prompt_version": prompt["prompt_version"],
        "chunk_count": len(chunks),
        "literature_count": len({chunk["literature_id"] for chunk in chunks}),
        "notes": [
            "Local hybrid retrieval uses keyword overlap, character n-gram similarity, metadata trust, and chunk quality signals.",
            "local_fts and local_hybrid_fts use a project-local SQLite FTS/BM25 retrieval signal.",
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
            "fts_index_file": fts_index["relative_path"],
            "fts_index_kind": fts_index["index_kind"],
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
    fts_matches_by_chunk: dict[str, dict[str, Any]] = {}
    if retrieval_mode in FTS_RETRIEVAL_MODES:
        try:
            build_literature_fts_index(project_dir, chunks)
            fts_matches_by_chunk = {
                str(match.get("chunk_id")): match
                for match in search_literature_fts(project_dir, question, top_k=max(top_k, 10))
                if match.get("chunk_id")
            }
        except Exception:
            # FTS is a derived local acceleration layer. If the SQLite file is
            # locked/corrupt on a local machine, preserve the Evidence Q&A path
            # by falling back to lexical hybrid retrieval instead of failing the
            # scientific workflow. local_fts returns no matches because it has no
            # lexical component by design.
            if retrieval_mode == "local_fts":
                return []
            fts_matches_by_chunk = {}
    scored: list[dict[str, Any]] = []
    for chunk in chunks:
        chunk_id = str(chunk.get("chunk_id") or "")
        if retrieval_mode == "local_fts" and chunk_id not in fts_matches_by_chunk:
            continue
        score = score_chunk(
            question,
            chunk,
            retrieval_mode=retrieval_mode,
            fts_match=fts_matches_by_chunk.get(chunk_id),
        )
        if (
            score["score"] > 0
            or score["keyword_score"] > 0
            or score["ngram_score"] > 0
            or score["fts_score"] > 0
        ):
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
                "fts_score": chunk.get("fts_score", 0),
                "bm25_score": chunk.get("bm25_score", 0),
                "retrieval_mode": chunk.get("retrieval_mode"),
                "page_start": chunk.get("page_start"),
                "page_end": chunk.get("page_end"),
                "page_quality_signals": chunk.get("page_quality_signals", []),
                "position_label": chunk.get("position_label")
                or f"char {chunk.get('start_char')}-{chunk.get('end_char')}",
                "source_locator": chunk.get("source_locator"),
                "metadata_trust_level": chunk.get("metadata_trust_level") or _metadata_trust_level(chunk),
                "parser_quality_label": chunk.get("parser_quality_label"),
                "parser_quality_score": chunk.get("parser_quality_score"),
                "evidence_warning_flags": _evidence_warning_flags(
                    chunk,
                    [str(warning) for warning in chunk.get("quality_warnings", [])],
                ),
                "score_breakdown": {
                    "keyword_score": chunk.get("keyword_score", 0),
                    "ngram_score": chunk.get("ngram_score", 0),
                    "fts_score": chunk.get("fts_score", 0),
                    "bm25_score": chunk.get("bm25_score", 0),
                    "metadata_trust_score": chunk.get("metadata_trust_score", 0),
                    "quality_score": chunk.get("quality_score", 0),
                },
                "matched_terms": chunk.get("matched_terms", []),
                "quality_warnings": chunk.get("quality_warnings", []),
                "text": chunk.get("text", ""),
            }
        )
    return passages


def _support_status(source_passages: list[dict[str, Any]]) -> tuple[str, float, float, list[str]]:
    if not source_passages:
        return (
            "unsupported",
            MINIMUM_SUPPORT_SCORE,
            0.0,
            ["The local literature index does not contain enough passage support for this question."],
        )
    top_source_score = max(float(passage.get("score") or 0.0) for passage in source_passages)
    if top_source_score < MINIMUM_SUPPORT_SCORE:
        return (
            "unsupported",
            MINIMUM_SUPPORT_SCORE,
            round(top_source_score, 4),
            ["The best local passage score is below the minimum support threshold."],
        )
    all_unverified = all(
        passage.get("metadata_trust_level") in {"placeholder_or_unverified", "unknown"}
        for passage in source_passages
    )
    any_low_quality = any(
        {"low_parser_quality", "failed_or_empty_parse"}.intersection(
            set(passage.get("evidence_warning_flags") or [])
        )
        for passage in source_passages
    )
    if top_source_score >= STRONG_SUPPORT_SCORE and not all_unverified and not any_low_quality:
        return "supported", MINIMUM_SUPPORT_SCORE, round(top_source_score, 4), []
    return (
        "weakly_supported",
        MINIMUM_SUPPORT_SCORE,
        round(top_source_score, 4),
        ["Local passages matched, but metadata verification or parser quality limits support strength."],
    )


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
    answer_support_status, minimum_support_score, top_source_score, support_notes = _support_status(
        source_passages
    )
    restricted_question_hits = _restricted_term_hits(cleaned_question)
    if restricted_question_hits and answer_support_status != "supported":
        answer_support_status = "unsupported"
        source_passages = []
        top_source_score = 0.0
        support_notes = [
            "The question asks for strong statistical, causal, proof, or p-value support that local passages do not verify."
        ]
    unsupported_notes: list[str] = []
    if answer_support_status == "unsupported":
        unsupported_notes.extend(support_notes)

    fallback = {
        "answer": (
            "Local retrieved passages mention the requested topic. Treat this as a draft "
            "literature note, not scientific proof."
            if answer_support_status != "unsupported"
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
    response = llm_client_module.llm_client.chat_json(messages, fallback, prompt_version=PROMPT_VERSION)
    parsed = response.parsed_json if isinstance(response.parsed_json, dict) else fallback
    raw_answer_text = str(parsed.get("answer") or fallback["answer"])
    answer_text, contract_notes = _sanitize_answer_text(raw_answer_text, answer_support_status)
    parsed_unsupported_notes = parsed.get("unsupported_notes")
    if not isinstance(parsed_unsupported_notes, list):
        parsed_unsupported_notes = []
    if answer_support_status in {"unsupported", "weakly_supported"}:
        parsed_unsupported_notes = list(dict.fromkeys([*parsed_unsupported_notes, *support_notes, *contract_notes]))
    parsed_limitations = parsed.get("limitations")
    if not isinstance(parsed_limitations, list):
        parsed_limitations = fallback["limitations"]
    answer_record = {
        "answer_id": f"rag_answer_{len(read_rag_answers(project_dir)) + 1:04d}",
        "created_at": _utc_now(),
        "project_id": project_id,
        "question": cleaned_question,
        "answer": answer_text,
        "answer_support_status": answer_support_status,
        "minimum_support_score": minimum_support_score,
        "top_source_score": top_source_score,
        "source_passages": source_passages,
        "unsupported_notes": parsed_unsupported_notes,
        "limitations": parsed_limitations,
        "retrieval_mode": retrieval_mode,
        "llm_mode": response.mode,
        "prompt_version": response.prompt_version,
        "source_passage_count": len(source_passages),
        "retrieval": {
            "mode": retrieval_mode,
            "retrieval_mode": retrieval_mode,
            "top_k": top_k,
            "returned": len(source_passages),
            "answer_support_status": answer_support_status,
            "minimum_support_score": minimum_support_score,
            "top_source_score": top_source_score,
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
            "answer_support_status": answer_support_status,
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
            "answer_support_status": answer_support_status,
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
