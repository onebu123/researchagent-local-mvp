from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_text_files(folder: Path, suffixes: set[str]) -> list[tuple[Path, str]]:
    if not folder.exists():
        return []
    result: list[tuple[Path, str]] = []
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() in suffixes:
            result.append((path, path.read_text(encoding="utf-8", errors="replace")))
    return result


def relative_posix(path: Path, root: Path) -> str:
    path_text = _strip_windows_extended_prefix(str(path.resolve()))
    root_text = _strip_windows_extended_prefix(str(root.resolve()))
    resolved_path = Path(path_text)
    resolved_root = Path(root_text)
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        relative = os.path.relpath(str(resolved_path), str(resolved_root))
        if relative == os.pardir or relative.startswith(os.pardir + os.sep) or os.path.isabs(relative):
            raise
        return Path(relative).as_posix()


def _strip_windows_extended_prefix(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        return "\\\\" + value[8:]
    if value.startswith("\\\\?\\"):
        return value[4:]
    return value
