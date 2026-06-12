from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    ".pytest_cache",
    "__pycache__",
    ".ruff_cache",
    ".mypy_cache",
    ".runtime",
    ".playwright",
    "projects",
    "dist",
    "evidence_logs",
    "test-results",
    "playwright-report",
    "blob-report",
    "coverage",
}

EXCLUDED_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".zip",
    ".pyc",
    ".pyo",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".woff",
    ".woff2",
}

PATTERNS = [
    ("openai-style key", re.compile(r"s" r"k-[A-Za-z0-9_-]{16,}")),
    ("legacy live key", re.compile(r"s" r"k_live_[A-Za-z0-9_-]+")),
    ("empty or assigned OpenAI env", re.compile(r"OPENAI_API_KEY" + r"\s*=")),
    ("private key", re.compile(r"BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY")),
    ("postgres password url", re.compile("postgresql://" + "user:password@")),
    ("redis password url", re.compile("redis://:" + "password@")),
]


def should_scan(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    lower_parts = {part.lower() for part in relative.parts}
    if lower_parts & EXCLUDED_DIRS:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def main() -> int:
    failures: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not should_scan(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(ROOT).as_posix()
        for label, pattern in PATTERNS:
            if pattern.search(text):
                failures.append(f"{relative}: {label}")
    if failures:
        print("Static secret scan failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Static secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
