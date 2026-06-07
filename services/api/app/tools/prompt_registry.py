from __future__ import annotations

from pathlib import Path
from typing import Any


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()
    raw = parts[1]
    body = parts[2].strip()
    metadata: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata, body


def _prompt_file(prompt_version: str) -> Path:
    safe = prompt_version.strip().replace("\\", "/")
    if not safe or "/" in safe or ".." in safe:
        raise ValueError("prompt_version must be a prompt file stem")
    path = PROMPT_DIR / f"{safe}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_version}")
    return path


def load_prompt(prompt_version: str) -> dict[str, Any]:
    path = _prompt_file(prompt_version)
    text = path.read_text(encoding="utf-8")
    metadata, body = _parse_frontmatter(text)
    version = metadata.get("prompt_version") or path.stem
    return {
        "prompt_version": version,
        "file_name": path.name,
        "purpose": metadata.get("purpose", ""),
        "content": body,
        "content_sha256": __import__("hashlib").sha256(body.encode("utf-8")).hexdigest(),
        "char_count": len(body),
    }


def list_prompts(include_content: bool = False) -> list[dict[str, Any]]:
    prompts: list[dict[str, Any]] = []
    for path in sorted(PROMPT_DIR.glob("*.md")):
        item = load_prompt(path.stem)
        if not include_content:
            item = {key: value for key, value in item.items() if key != "content"}
        prompts.append(item)
    return prompts
