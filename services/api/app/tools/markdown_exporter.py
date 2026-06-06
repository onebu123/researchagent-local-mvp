from __future__ import annotations

from pathlib import Path

from app.tools.file_tools import write_text


def export_markdown(path: Path, content: str) -> Path:
    write_text(path, content.strip() + "\n")
    return path
