from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from package_release import ROOT, create_evidence_zip, create_source_zip, sanitize_text


COMMANDS = [
    {
        "label": "compileall",
        "command": [sys.executable, "-m", "compileall", "services/api", "scripts"],
        "cwd": ROOT,
        "critical": True,
    },
    {
        "label": "pytest",
        "command": [sys.executable, "-m", "pytest", "services/api/tests", "-q"],
        "cwd": ROOT,
        "critical": True,
    },
    {
        "label": "run_demo",
        "command": [sys.executable, "scripts/run_demo.py"],
        "cwd": ROOT,
        "critical": True,
    },
    {
        "label": "validate_v2",
        "command": [sys.executable, "scripts/validate_v2.py"],
        "cwd": ROOT,
        "critical": True,
    },
    {
        "label": "web_typecheck",
        "command": ["npm", "run", "typecheck"],
        "cwd": ROOT / "apps" / "web",
        "critical": True,
    },
    {
        "label": "web_build",
        "command": ["npm", "run", "build"],
        "cwd": ROOT / "apps" / "web",
        "critical": True,
    },
    {
        "label": "playwright",
        "command": ["npx", "playwright", "test"],
        "cwd": ROOT / "apps" / "web",
        "critical": True,
    },
    {
        "label": "git_status_short",
        "command": ["git", "status", "--short"],
        "cwd": ROOT,
        "critical": True,
    },
    {
        "label": "git_log_1",
        "command": ["git", "log", "-1", "--oneline"],
        "cwd": ROOT,
        "critical": True,
    },
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_command(record: dict[str, object], evidence_dir: Path) -> dict[str, object]:
    label = str(record["label"])
    result = subprocess.run(
        record["command"],
        cwd=record["cwd"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = sanitize_text(result.stdout)
    (evidence_dir / f"{label}.log").write_text(output, encoding="utf-8")
    return {
        "label": label,
        "returncode": result.returncode,
        "critical": bool(record["critical"]),
        "log": f"{label}.log",
    }


def check_zip_integrity(evidence_dir: Path) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    failed = False
    for zip_path in sorted((ROOT / "dist").glob("*.zip")):
        with zipfile.ZipFile(zip_path) as archive:
            bad_file = archive.testzip()
            names = archive.namelist()
        has_backslash = any("\\" in name for name in names)
        record = {
            "zip": zip_path.name,
            "bad_file": bad_file,
            "entry_count": len(names),
            "has_backslash": has_backslash,
        }
        entries.append(record)
        failed = failed or bad_file is not None or has_backslash
    payload = {"checked": entries, "failed": failed}
    (evidence_dir / "zip_integrity.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"label": "zip_integrity", "returncode": 1 if failed else 0, "critical": True, "log": "zip_integrity.json"}


def collect_release_evidence(version: str, output_dir: Path) -> int:
    evidence_dir = ROOT / "evidence_logs" / utc_stamp()
    evidence_dir.mkdir(parents=True, exist_ok=True)

    command_results = [run_command(record, evidence_dir) for record in COMMANDS]
    command_results.append(check_zip_integrity(evidence_dir))

    git_status = (evidence_dir / "git_status_short.log").read_text(encoding="utf-8")
    critical_failures = [
        item for item in command_results if item["critical"] and int(item["returncode"]) != 0
    ]
    dirty_git = bool(git_status.strip())

    summary = {
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "release_ready": not critical_failures and not dirty_git,
        "dirty_git": dirty_git,
        "commands": command_results,
    }
    (evidence_dir / "evidence_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    lines = [
        f"# ResearchAgent {version} Evidence Summary",
        "",
        f"- Release ready: {str(summary['release_ready']).lower()}",
        f"- Dirty git status: {str(dirty_git).lower()}",
        f"- Critical failures: {len(critical_failures)}",
        "",
    ]
    if dirty_git:
        lines.append("Dirty git status was detected. This evidence must not be described as release-ready.")
    for item in command_results:
        status = "pass" if int(item["returncode"]) == 0 else "fail"
        lines.append(f"- {item['label']}: {status} ({item['log']})")
    (evidence_dir / "evidence_summary.md").write_text("\n".join(lines), encoding="utf-8")

    source_zip = create_source_zip(version, output_dir)
    create_evidence_zip(version, output_dir, source_zip, evidence_dir=evidence_dir)
    return 1 if critical_failures or dirty_git else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect ResearchAgent release evidence.")
    parser.add_argument("--version", default="v3.0.0-rc1")
    parser.add_argument("--output-dir", default="dist")
    args = parser.parse_args(argv)
    return collect_release_evidence(args.version, ROOT / args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
