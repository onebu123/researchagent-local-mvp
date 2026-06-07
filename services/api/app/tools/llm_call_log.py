from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir
from app.tools.llm_client import LLMResponse

SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"(api[_-]?key|authorization|bearer|token|secret)\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
]
ABSOLUTE_PATH_PATTERN = re.compile(r"([A-Za-z]:[\\/][^\s\"']+|/(?:home|Users|var|tmp|mnt)/[^\s\"']+)")


def llm_call_log_path(project_dir: Path) -> Path:
    return project_dir / "llm" / "llm_calls.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _redact(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("<secret_removed>", redacted)
    return ABSOLUTE_PATH_PATTERN.sub("<absolute_path_removed>", redacted)


def _preview(value: str, limit: int = 160) -> str:
    compact = " ".join(_redact(value).split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."


def summarize_messages(messages: list[dict[str, str]]) -> dict[str, Any]:
    canonical = json.dumps(messages, ensure_ascii=False, sort_keys=True)
    chars = sum(len(str(message.get("content", ""))) for message in messages)
    role_counts: dict[str, int] = {}
    message_summaries: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role", "unknown"))
        content = str(message.get("content", ""))
        role_counts[role] = role_counts.get(role, 0) + 1
        message_summaries.append(
            {
                "role": role,
                "char_count": len(content),
                "sha256": _hash_text(content),
            }
        )
    return {
        "message_count": len(messages),
        "char_count": chars,
        "sha256": _hash_text(canonical),
        "role_counts": role_counts,
        "messages": message_summaries[:4],
        "truncated": len(message_summaries) > 4,
    }


def summarize_text(value: str) -> dict[str, Any]:
    return {
        "char_count": len(value),
        "sha256": _hash_text(value),
        "preview": _preview(value),
    }


def _sanitize_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize_metadata(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_metadata(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_metadata(item) for item in value]
    if isinstance(value, str):
        return _redact(value)
    return value


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


def read_llm_calls(project_dir: Path, limit: int = 100) -> list[dict[str, Any]]:
    records = _read_jsonl(llm_call_log_path(project_dir))
    return records[-max(limit, 0) :] if limit else records


def append_llm_call(
    project_dir: Path,
    project_id: str,
    operation: str,
    messages: list[dict[str, str]],
    response: LLMResponse,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = llm_call_log_path(project_dir)
    existing = _read_jsonl(path)
    record = {
        "call_id": f"llm_call_{len(existing) + 1:04d}",
        "created_at": _utc_now(),
        "project_id": project_id,
        "operation": operation,
        "provider": response.provider,
        "model": response.model,
        "mode": response.mode,
        "prompt_version": response.prompt_version,
        "status": response.status,
        "request_summary": summarize_messages(messages),
        "response_summary": summarize_text(response.content),
        "usage": {
            "prompt_tokens": response.usage.get("prompt_tokens"),
            "completion_tokens": response.usage.get("completion_tokens"),
            "total_tokens": response.usage.get("total_tokens"),
            "estimated_cost_usd": None,
        },
        "error": response.error,
        "attempts": response.attempts,
        "metadata": _sanitize_metadata(metadata or {}),
    }
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    append_audit_event(
        project_dir,
        project_id,
        "llm_call_logged",
        "LLM call metadata was recorded without API key or full prompt content.",
        {
            "call_id": record["call_id"],
            "operation": operation,
            "mode": response.mode,
            "provider": response.provider,
            "model": response.model,
            "prompt_version": response.prompt_version,
            "status": response.status,
        },
        source="api",
        event_category="system",
        risk_level="low",
        entity_type="project",
        entity_id=project_id,
    )
    return record
