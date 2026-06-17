from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from app.tools.file_tools import ensure_dir


def fts_index_path(project_dir: Path) -> Path:
    return project_dir / "literature" / "rag" / "literature_fts.sqlite3"


def _tokens(text: str) -> list[str]:
    seen: set[str] = set()
    tokens: list[str] = []
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_'-]{2,}", text.lower()):
        cleaned = re.sub(r"[^a-z0-9_]", "", token)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            tokens.append(cleaned)
    return tokens


def _relative_index_file() -> str:
    return "literature/rag/literature_fts.sqlite3"


def _connect(project_dir: Path) -> sqlite3.Connection:
    path = fts_index_path(project_dir)
    ensure_dir(path.parent)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _has_fts5(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE temp.__fts5_probe USING fts5(value)")
        conn.execute("DROP TABLE temp.__fts5_probe")
        return True
    except sqlite3.Error:
        return False


def _write_meta(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS literature_fts_meta (key TEXT PRIMARY KEY, value TEXT)")
    for key, value in payload.items():
        conn.execute(
            "INSERT OR REPLACE INTO literature_fts_meta (key, value) VALUES (?, ?)",
            (key, json.dumps(value, ensure_ascii=False)),
        )


def _read_meta(conn: sqlite3.Connection) -> dict[str, Any]:
    try:
        rows = conn.execute("SELECT key, value FROM literature_fts_meta").fetchall()
    except sqlite3.Error:
        return {}
    meta: dict[str, Any] = {}
    for row in rows:
        try:
            meta[str(row["key"])] = json.loads(str(row["value"]))
        except json.JSONDecodeError:
            meta[str(row["key"])] = row["value"]
    return meta


def build_literature_fts_index(project_dir: Path, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a project-local SQLite retrieval index from already-created RAG chunks.

    The index is a derived artifact, so rebuilding should be idempotent even if a
    previous test or interrupted run left behind FTS shadow tables. Recreate the
    SQLite file when possible instead of relying only on DROP TABLE ordering.
    """

    index_file = fts_index_path(project_dir)
    ensure_dir(index_file.parent)
    if index_file.exists():
        try:
            index_file.unlink()
        except OSError:
            # Fall back to in-place cleanup for platforms where the file is locked.
            pass

    with _connect(project_dir) as conn:
        fts5_enabled = _has_fts5(conn)
        for table_name in [
            "literature_chunks_fts",
            "literature_chunks_fts_data",
            "literature_chunks_fts_idx",
            "literature_chunks_fts_content",
            "literature_chunks_fts_docsize",
            "literature_chunks_fts_config",
            "literature_chunks",
        ]:
            try:
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            except sqlite3.Error:
                pass
        conn.execute(
            """
            CREATE TABLE literature_chunks (
                chunk_id TEXT PRIMARY KEY,
                literature_id TEXT,
                source_file TEXT,
                title TEXT,
                text TEXT NOT NULL
            )
            """
        )
        for chunk in chunks:
            conn.execute(
                """
                INSERT OR REPLACE INTO literature_chunks
                (chunk_id, literature_id, source_file, title, text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(chunk.get("chunk_id") or ""),
                    str(chunk.get("literature_id") or ""),
                    chunk.get("source_file"),
                    chunk.get("title"),
                    str(chunk.get("text") or ""),
                ),
            )
        if fts5_enabled:
            conn.execute(
                """
                CREATE VIRTUAL TABLE literature_chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    literature_id UNINDEXED,
                    source_file UNINDEXED,
                    title,
                    text,
                    tokenize='unicode61'
                )
                """
            )
            conn.execute(
                """
                INSERT INTO literature_chunks_fts (chunk_id, literature_id, source_file, title, text)
                SELECT chunk_id, literature_id, source_file, title, text FROM literature_chunks
                """
            )
        _write_meta(
            conn,
            {
                "relative_path": _relative_index_file(),
                "index_kind": "sqlite_fts5" if fts5_enabled else "sqlite_like_fallback",
                "chunk_count": len(chunks),
                "external_services_required": False,
            },
        )
        return {
            "relative_path": _relative_index_file(),
            "index_kind": "sqlite_fts5" if fts5_enabled else "sqlite_like_fallback",
            "chunk_count": len(chunks),
            "external_services_required": False,
        }


def _fallback_like_search(
    conn: sqlite3.Connection,
    question_tokens: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT chunk_id, title, text FROM literature_chunks",
    ).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        text = f"{row['title'] or ''} {row['text'] or ''}".lower()
        matched = [token for token in question_tokens if token in text]
        if not matched:
            continue
        coverage = len(matched) / max(len(question_tokens), 1)
        results.append(
            {
                "chunk_id": row["chunk_id"],
                "fts_score": round(coverage, 4),
                "bm25_score": 0.0,
                "fts_rank": len(results) + 1,
                "fts_index_kind": "sqlite_like_fallback",
                "fts_matched_terms": matched,
            }
        )
    results.sort(key=lambda item: (-float(item["fts_score"]), str(item["chunk_id"])))
    return results[:top_k]


def search_literature_fts(project_dir: Path, question: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Search the project-local SQLite FTS index and return chunk-level retrieval signals."""

    path = fts_index_path(project_dir)
    if not path.exists():
        return []
    question_tokens = _tokens(question)
    if not question_tokens:
        return []
    top_k = max(1, min(int(top_k), 20))
    with _connect(project_dir) as conn:
        meta = _read_meta(conn)
        index_kind = str(meta.get("index_kind") or "sqlite_like_fallback")
        if index_kind != "sqlite_fts5":
            return _fallback_like_search(conn, question_tokens, top_k)
        match_query = " OR ".join(question_tokens)
        try:
            rows = conn.execute(
                """
                SELECT
                    chunk_id,
                    title,
                    text,
                    bm25(literature_chunks_fts) AS bm25_score
                FROM literature_chunks_fts
                WHERE literature_chunks_fts MATCH ?
                ORDER BY bm25(literature_chunks_fts)
                LIMIT ?
                """,
                (match_query, top_k),
            ).fetchall()
        except sqlite3.Error:
            return _fallback_like_search(conn, question_tokens, top_k)

    results: list[dict[str, Any]] = []
    for rank, row in enumerate(rows, start=1):
        text = f"{row['title'] or ''} {row['text'] or ''}".lower()
        matched = [token for token in question_tokens if token in text]
        coverage = len(matched) / max(len(question_tokens), 1)
        rank_signal = 1.0 / rank
        fts_score = round(min(1.0, (coverage * 0.75) + (rank_signal * 0.25)), 4)
        results.append(
            {
                "chunk_id": row["chunk_id"],
                "fts_score": fts_score,
                "bm25_score": round(float(row["bm25_score"] or 0.0), 6),
                "fts_rank": rank,
                "fts_index_kind": "sqlite_fts5",
                "fts_matched_terms": matched,
            }
        )
    return results
