from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSION = "v2.0.1-dev"

REQUIRED_ROOT_FILES = [
    "README.md",
    "AGENTS.md",
    ".gitignore",
    ".dockerignore",
    ".env.example",
    "docker-compose.yml",
]

INCLUDE_DIRS = ["services", "apps", "scripts", "docs"]
OPTIONAL_INCLUDE_DIRS = [".github"]

EXCLUDED_DIR_NAMES = {
    ".git",
    "node_modules",
    ".next",
    ".pytest_cache",
    "__pycache__",
    ".ruff_cache",
    ".mypy_cache",
    ".runtime",
    ".playwright",
    "test-results",
    "playwright-report",
    "blob-report",
    "coverage",
}

EXCLUDED_TOP_LEVEL = {"projects", "dist", "build", "evidence_logs"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".sqlite", ".sqlite3", ".db", ".tsbuildinfo"}

SECRET_PATTERNS = [
    re.compile(r"s" r"k-[A-Za-z0-9_-]{16,}"),
    re.compile(r"s" r"k_live_[A-Za-z0-9_-]+"),
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY"),
    re.compile(r"postgresql://" + r"[^<\s]+:" + r"[^<\s]+@"),
    re.compile(r"redis://:" + r"[^<\s]+@"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_version(version: str) -> str:
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:[-.][A-Za-z0-9_.-]+)?", version):
        raise ValueError("version must look like v2.0.1-dev")
    return version


def to_posix(relative_path: Path) -> str:
    return relative_path.as_posix()


def is_env_file(relative_path: Path) -> bool:
    name = relative_path.name
    return name == ".env" or name.startswith(".env.")


def is_excluded(relative_path: Path) -> bool:
    parts = relative_path.parts
    lower_parts = [part.lower() for part in parts]
    if not parts:
        return True
    if lower_parts[0] in EXCLUDED_TOP_LEVEL:
        return True
    if any(part in EXCLUDED_DIR_NAMES for part in lower_parts):
        return True
    if relative_path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if is_env_file(relative_path) and relative_path.name != ".env.example":
        return True
    return False


def iter_source_files(root: Path = ROOT) -> Iterable[Path]:
    for relative_name in REQUIRED_ROOT_FILES:
        path = root / relative_name
        if not path.exists():
            raise FileNotFoundError(f"required release file missing: {relative_name}")
        yield path

    for directory_name in INCLUDE_DIRS + OPTIONAL_INCLUDE_DIRS:
        directory = root / directory_name
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            relative_path = path.relative_to(root)
            if not is_excluded(relative_path):
                yield path


def scan_text_for_secrets(text: str, relative_name: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"secret-like value found in {relative_name}")


def create_source_zip(version: str, output_dir: Path, root: Path = ROOT) -> Path:
    version = validate_version(version)
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"researchagent-{version}-source.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        seen: set[str] = set()
        for path in sorted(iter_source_files(root), key=lambda item: item.relative_to(root).as_posix()):
            relative_path = path.relative_to(root)
            entry_name = to_posix(relative_path)
            if "\\" in entry_name or entry_name.startswith("/") or re.match(r"^[A-Za-z]:", entry_name):
                raise ValueError(f"unsafe zip entry path: {entry_name}")
            if entry_name in seen:
                continue
            seen.add(entry_name)
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = ""
            if text:
                scan_text_for_secrets(text, entry_name)
            archive.write(path, entry_name)

    return zip_path


def inspect_zip(zip_path: Path) -> dict[str, object]:
    with zipfile.ZipFile(zip_path) as archive:
        bad_file = archive.testzip()
        entries = archive.namelist()
    has_backslash = any("\\" in entry for entry in entries)
    forbidden_entries = [
        entry
        for entry in entries
        if is_excluded(Path(entry)) or entry.startswith("/") or re.match(r"^[A-Za-z]:", entry)
    ]
    return {
        "zip_path": zip_path.name,
        "entry_count": len(entries),
        "bad_file": bad_file,
        "has_backslash": has_backslash,
        "forbidden_entries": forbidden_entries,
    }


def run_git(command: list[str], root: Path = ROOT) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *command],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode, sanitize_text(result.stdout, root)


def sanitize_text(text: str, root: Path = ROOT) -> str:
    sanitized = text.replace(str(root), ".").replace(root.as_posix(), ".")
    sanitized = re.sub(r"s" r"k-[A-Za-z0-9_-]{16,}", "<redacted-api-key>", sanitized)
    sanitized = re.sub(r"s" r"k_live_[A-Za-z0-9_-]+", "<redacted-api-key>", sanitized)
    sanitized = re.sub(r"BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY", "BEGIN <redacted-private-key>", sanitized)
    sanitized = re.sub(r"postgresql://" + r"[^<\s]+:" + r"[^<\s]+@", "postgresql://<redacted>@", sanitized)
    sanitized = re.sub(r"redis://:" + r"[^<\s]+@", "redis://:<redacted>@", sanitized)
    return sanitized


def create_evidence_zip(
    version: str,
    output_dir: Path,
    source_zip: Path,
    root: Path = ROOT,
    evidence_dir: Path | None = None,
) -> Path:
    version = validate_version(version)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_zip = output_dir / f"researchagent-{version}-evidence.zip"
    status_code, git_status = run_git(["status", "--short"], root)
    log_code, git_log = run_git(["log", "-1", "--oneline"], root)
    source_inspection = inspect_zip(source_zip)
    dirty = bool(git_status.strip()) or status_code != 0
    release_ready = (
        not dirty
        and log_code == 0
        and source_inspection["bad_file"] is None
        and not source_inspection["has_backslash"]
        and not source_inspection["forbidden_entries"]
    )

    summary = {
        "version": version,
        "created_at": utc_now(),
        "release_ready": release_ready,
        "git_status": "dirty" if dirty else "clean",
        "source_zip": source_inspection,
        "evidence_note": (
            "Command logs are included when scripts/collect_evidence.py has been run. "
            "This package never treats failed commands or dirty git status as release-ready evidence."
        ),
    }

    summary_md = [
        f"# ResearchAgent {version} Evidence Summary",
        "",
        f"- Created at: {summary['created_at']}",
        f"- Release ready: {str(release_ready).lower()}",
        f"- Git status: {summary['git_status']}",
        f"- Source zip integrity: {'pass' if source_inspection['bad_file'] is None else 'fail'}",
        f"- Source zip POSIX paths: {'pass' if not source_inspection['has_backslash'] else 'fail'}",
        f"- Forbidden entries: {len(source_inspection['forbidden_entries'])}",
        "",
        "This evidence package is a local audit artifact. It is not a production, compliance, or peer review certificate.",
        "",
    ]
    if dirty:
        summary_md.append("Dirty git status was detected. Do not describe this evidence as release-ready.")

    with zipfile.ZipFile(evidence_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("evidence_summary.md", "\n".join(summary_md))
        archive.writestr("package_manifest.json", json.dumps(summary, indent=2, ensure_ascii=False))
        archive.writestr("git_status_short.txt", git_status)
        archive.writestr("git_log_1.txt", git_log)
        archive.writestr("source_zip_integrity.json", json.dumps(source_inspection, indent=2))
        if evidence_dir and evidence_dir.exists():
            for path in sorted(evidence_dir.rglob("*")):
                if path.is_file() and not is_excluded(path.relative_to(evidence_dir)):
                    entry = Path("command_logs") / path.relative_to(evidence_dir)
                    archive.write(path, entry.as_posix())

    return evidence_zip


def package_release(version: str, output_dir: Path, root: Path = ROOT) -> dict[str, str]:
    source_zip = create_source_zip(version, output_dir, root=root)
    evidence_zip = create_evidence_zip(version, output_dir, source_zip, root=root)
    return {
        "source_zip": source_zip.name,
        "evidence_zip": evidence_zip.name,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create ResearchAgent source and evidence packages.")
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--output-dir", default="dist")
    args = parser.parse_args(argv)

    output_dir = (ROOT / args.output_dir).resolve()
    result = package_release(args.version, output_dir)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
