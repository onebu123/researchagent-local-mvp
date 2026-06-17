from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "demo_project"
PROJECT_DIR = ROOT / "projects" / PROJECT_ID
REPORTS_DIR = ROOT / "reports"
REPORT_JSON = REPORTS_DIR / "verification_report.json"
REPORT_MD = REPORTS_DIR / "verification_report.md"
VERSION = "v3.0.0-rc1"

REQUIRED_ARTIFACTS = [
    "projects/demo_project/literature/literature_index.json",
    "projects/demo_project/literature/rag/chunks.jsonl",
    "projects/demo_project/literature/rag/rag_answers.jsonl",
    "projects/demo_project/analysis/result_summary.json",
    "projects/demo_project/analysis/analysis_provenance.json",
    "projects/demo_project/figures/figure_provenance.json",
    "projects/demo_project/provenance/evidence.json",
    "projects/demo_project/provenance/claim_alignment.json",
    "projects/demo_project/manuscript/draft.md",
    "projects/demo_project/manuscript/readable.md",
    "projects/demo_project/manuscript/refined.md",
    "projects/demo_project/reviews/review_report.json",
    "projects/demo_project/runs/run_history.json",
]

JSON_ARTIFACTS = {
    "projects/demo_project/literature/literature_index.json",
    "projects/demo_project/analysis/result_summary.json",
    "projects/demo_project/analysis/analysis_provenance.json",
    "projects/demo_project/figures/figure_provenance.json",
    "projects/demo_project/provenance/evidence.json",
    "projects/demo_project/provenance/claim_alignment.json",
    "projects/demo_project/reviews/review_report.json",
    "projects/demo_project/runs/run_history.json",
}

JSONL_ARTIFACTS = {
    "projects/demo_project/literature/rag/chunks.jsonl",
    "projects/demo_project/literature/rag/rag_answers.jsonl",
}

SAFETY_SCAN_FILES = [
    "projects/demo_project/literature/literature_index.json",
    "projects/demo_project/literature/rag/rag_answers.jsonl",
    "projects/demo_project/analysis/result_summary.json",
    "projects/demo_project/analysis/analysis_provenance.json",
    "projects/demo_project/figures/figure_provenance.json",
    "projects/demo_project/provenance/evidence.json",
    "projects/demo_project/provenance/claim_alignment.json",
    "projects/demo_project/manuscript/draft.md",
    "projects/demo_project/manuscript/readable.md",
    "projects/demo_project/manuscript/refined.md",
]

SECRET_PATTERNS = [
    (re.compile(r"s" r"k-[A-Za-z0-9_-]{16,}"), "<redacted-api-key>"),
    (re.compile(r"s" r"k_live_[A-Za-z0-9_-]+"), "<redacted-api-key>"),
    (re.compile(r"(OPENAI_API_KEY|LLM_API_KEY)\s*=\s*[^\s]+", re.IGNORECASE), r"\1=<redacted>"),
    (re.compile(r"BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY"), "BEGIN <redacted-private-key>"),
    (re.compile(r"postgresql://[^<\s]+:[^<\s]+@"), "postgresql://<redacted>@"),
    (re.compile(r"redis://:[^<\s]+@"), "redis://:<redacted>@"),
]

RISK_PATTERNS = [
    ("unsupported_p_value", re.compile(r"\bp\s*(?:<|<=|=)\s*0\.0?5\b", re.IGNORECASE)),
    ("unsupported_p_value", re.compile(r"\bp\s*=\s*0\.03\b", re.IGNORECASE)),
    ("unsupported_statistical_significance", re.compile(r"\bstatistically significant\b", re.IGNORECASE)),
    ("unsupported_causal_effect", re.compile(r"\bcausal effect\b", re.IGNORECASE)),
    ("unsupported_causal_claim", re.compile(r"\bcaused by\b", re.IGNORECASE)),
    ("unsupported_proof_claim", re.compile(r"\bproved?\b|\bproves\b", re.IGNORECASE)),
    ("unsupported_demonstrated_claim", re.compile(r"\bdemonstrated that\b", re.IGNORECASE)),
]

NEGATION_MARKERS = [
    "no ",
    "not ",
    "without ",
    "does not ",
    "do not ",
    "must not ",
    "cannot ",
    "unsupported",
    "unverified",
    "not verified",
    "not a verified reference",
    "requires human review",
    "requires manual verification",
]

ZIP_FORBIDDEN_PREFIXES = [
    "projects/",
    "node_modules/",
    ".next/",
    "__pycache__/",
]

ZIP_FORBIDDEN_PARTS = [
    "/node_modules/",
    "/.next/",
    "/__pycache__/",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def sanitize_text(text: str) -> str:
    sanitized = text.replace(str(ROOT), ".").replace(ROOT.as_posix(), ".")
    sanitized = sanitized.replace(str(ROOT.parent), "<workspace-parent>")
    sanitized = sanitized.replace(ROOT.parent.as_posix(), "<workspace-parent>")
    sanitized = re.sub(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/][^\s\"'<>]+", "<absolute-path>", sanitized)
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def command_name(name: str) -> str:
    if os.name == "nt" and name in {"npm", "npx"}:
        return f"{name}.cmd"
    return name


def base_env() -> dict[str, str]:
    env = os.environ.copy()
    env["APP_ENV"] = "local"
    env["PROJECTS_ROOT"] = "./projects"
    env["DATABASE_BACKEND"] = "sqlite"
    env["QUEUE_MODE"] = "inline"
    env["AUTH_MODE"] = "disabled"
    env["LLM_MODE"] = "mock"
    env["LLM_API_KEY"] = ""
    env["OPENAI_API_KEY"] = ""
    env["NEXT_PUBLIC_API_BASE_URL"] = "http://127.0.0.1:8000"
    env.setdefault("NODE_OPTIONS", "--max-old-space-size=8192 --max-semi-space-size=512")
    env.setdefault("PYTHONUTF8", "1")
    return env


def run_command(label: str, display: list[str], actual: list[str], cwd: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "label": label,
        "command": " ".join(display),
        "cwd": rel(cwd),
        "passed": False,
        "exit_code": None,
        "failure_reason": "",
        "output_tail": "",
    }
    try:
        completed = subprocess.run(
            actual,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=base_env(),
        )
    except FileNotFoundError as exc:
        result["exit_code"] = 127
        result["failure_reason"] = sanitize_text(str(exc))
        result["output_tail"] = result["failure_reason"]
        return result

    output = sanitize_text(completed.stdout or "")
    result["exit_code"] = completed.returncode
    result["passed"] = completed.returncode == 0
    result["output_tail"] = output[-5000:]
    if completed.returncode != 0:
        result["failure_reason"] = f"exit code {completed.returncode}"
    return result


def read_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # noqa: BLE001
        return None, sanitize_text(str(exc))


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], str | None]:
    records: list[dict[str, Any]] = []
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                return records, f"line {line_number} is not a JSON object"
            records.append(value)
    except Exception as exc:  # noqa: BLE001
        return records, sanitize_text(str(exc))
    return records, None


def check_artifacts() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    parsed: dict[str, Any] = {}
    for relative in REQUIRED_ARTIFACTS:
        path = ROOT / relative
        record: dict[str, Any] = {
            "path": relative,
            "exists": path.exists(),
            "json_parse": None,
            "jsonl_records": None,
            "passed": False,
            "failure_reason": "",
        }
        if not path.exists():
            record["failure_reason"] = "missing artifact"
            checks.append(record)
            continue
        if relative in JSON_ARTIFACTS:
            payload, error = read_json(path)
            record["json_parse"] = error is None
            if error:
                record["failure_reason"] = error
            else:
                parsed[relative] = payload
        elif relative in JSONL_ARTIFACTS:
            payload, error = read_jsonl(path)
            record["json_parse"] = error is None
            record["jsonl_records"] = len(payload)
            if error:
                record["failure_reason"] = error
            else:
                parsed[relative] = payload
        record["passed"] = bool(record["exists"]) and not record["failure_reason"]
        checks.append(record)
    return checks, parsed


def iter_revision_diffs(value: Any) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "revision_diff" and isinstance(item, dict):
                diffs.append(item)
            else:
                diffs.extend(iter_revision_diffs(item))
    elif isinstance(value, list):
        for item in value:
            diffs.extend(iter_revision_diffs(item))
    return diffs


def check_review_report(parsed: dict[str, Any]) -> dict[str, Any]:
    relative = "projects/demo_project/reviews/review_report.json"
    report = parsed.get(relative)
    result = {"passed": True, "issues": []}
    issues: list[str] = result["issues"]
    if not isinstance(report, dict):
        issues.append("review_report.json is missing or not a JSON object")
    else:
        if "sentence_issues" not in report:
            issues.append("missing sentence_issues")
        if "reviewed_manuscript_file" not in report:
            issues.append("missing reviewed_manuscript_file")
        for diff in iter_revision_diffs(report):
            if diff.get("requires_human_approval") is not True:
                issues.append("revision_diff missing requires_human_approval=true")
    result["passed"] = not issues
    return result


def answer_text(record: dict[str, Any]) -> str:
    for key in ["answer", "response", "content", "text"]:
        value = record.get(key)
        if isinstance(value, str):
            return value
    return json.dumps(record, ensure_ascii=False)


def check_rag_answers(parsed: dict[str, Any]) -> dict[str, Any]:
    relative = "projects/demo_project/literature/rag/rag_answers.jsonl"
    records = parsed.get(relative)
    result = {"passed": True, "record_count": 0, "issues": []}
    issues: list[str] = result["issues"]
    if not isinstance(records, list):
        issues.append("rag_answers.jsonl is missing or invalid")
        result["passed"] = False
        return result
    result["record_count"] = len(records)
    if not records:
        issues.append("rag_answers.jsonl has no records")
    for index, record in enumerate(records, start=1):
        source_passages = record.get("source_passages")
        unsupported_notes = record.get("unsupported_notes")
        if not source_passages and not unsupported_notes:
            issues.append(f"record {index} has neither source_passages nor unsupported_notes")
        lower_answer = answer_text(record).lower()
        llm_mode = str(record.get("llm_mode") or "").lower()
        unverified_sources = [
            passage
            for passage in source_passages or []
            if isinstance(passage, dict)
            and (not passage.get("human_verified") or passage.get("metadata_status") != "verified")
        ]
        if (llm_mode == "mock" or unverified_sources) and any(
            marker in lower_answer
            for marker in [
                "verified scientific evidence",
                "verified evidence",
                "verified reference",
                "scientifically proven",
            ]
        ):
            issues.append(f"record {index} presents mock/demo output as verified evidence")
    result["passed"] = not issues
    return result


def text_is_negated(text: str, match_start: int) -> bool:
    window = text[max(0, match_start - 80) : match_start + 140].lower()
    return any(marker in window for marker in NEGATION_MARKERS)


def check_safety_text() -> dict[str, Any]:
    result = {"passed": True, "issues": []}
    issues: list[dict[str, str]] = result["issues"]
    for relative in SAFETY_SCAN_FILES:
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for risk_type, pattern in RISK_PATTERNS:
            for match in pattern.finditer(text):
                if text_is_negated(text, match.start()):
                    continue
                issues.append(
                    {
                        "path": relative,
                        "risk_type": risk_type,
                        "matched_text": sanitize_text(match.group(0)),
                    }
                )
    result["passed"] = not issues
    return result


def meaningful_metadata(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "unknown", "placeholder", "not provided", "n/a"}
    if isinstance(value, list):
        return any(meaningful_metadata(item) for item in value)
    return bool(value)


def check_literature_metadata(parsed: dict[str, Any]) -> dict[str, Any]:
    relative = "projects/demo_project/literature/literature_index.json"
    entries = parsed.get(relative)
    result = {"passed": True, "issues": []}
    issues: list[dict[str, str]] = result["issues"]
    if not isinstance(entries, list):
        issues.append({"path": relative, "field": "index", "reason": "invalid literature index"})
        result["passed"] = False
        return result
    restricted_fields = ["doi", "authors", "journal", "year", "page_range", "bibliographic_pages"]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        verified = entry.get("metadata_status") == "verified" and entry.get("human_verified") is True
        if verified:
            continue
        source_file = str(entry.get("source_file") or "unknown")
        for field in restricted_fields:
            if meaningful_metadata(entry.get(field)):
                issues.append(
                    {
                        "path": relative,
                        "source_file": source_file,
                        "field": field,
                        "reason": "unverified literature metadata must not be presented as factual",
                    }
                )
    result["passed"] = not issues
    return result


def zip_entry_forbidden(entry: str) -> str | None:
    if "\\" in entry:
        return "entry contains backslash"
    normalized = entry.lstrip("/")
    if normalized == ".env" or (normalized.startswith(".env.") and normalized != ".env.example"):
        return "entry contains .env"
    for prefix in ZIP_FORBIDDEN_PREFIXES:
        if normalized.startswith(prefix):
            return f"entry starts with {prefix}"
    for part in ZIP_FORBIDDEN_PARTS:
        if part in normalized:
            return f"entry contains {part}"
    return None


def inspect_zip(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "passed": False,
        "entry_count": 0,
        "bad_file": None,
        "forbidden_entries": [],
        "contains_env_example": False,
        "failure_reason": "",
    }
    if not path.exists():
        result["failure_reason"] = "zip file missing"
        return result
    try:
        with zipfile.ZipFile(path) as archive:
            result["bad_file"] = archive.testzip()
            entries = archive.namelist()
    except zipfile.BadZipFile as exc:
        result["failure_reason"] = sanitize_text(str(exc))
        return result
    forbidden = []
    for entry in entries:
        reason = zip_entry_forbidden(entry)
        if reason:
            forbidden.append({"entry": entry, "reason": reason})
    result["entry_count"] = len(entries)
    result["forbidden_entries"] = forbidden
    result["contains_env_example"] = ".env.example" in entries
    result["passed"] = result["bad_file"] is None and not forbidden
    if path.name.endswith("-source.zip") and not result["contains_env_example"]:
        result["passed"] = False
        result["failure_reason"] = ".env.example missing from source zip"
    return result


def package_checks(command_results: list[dict[str, Any]]) -> dict[str, Any]:
    script = ROOT / "scripts" / "package_release.py"
    result: dict[str, Any] = {
        "package_script_exists": script.exists(),
        "command": None,
        "zips": [],
        "passed": True,
    }
    if not script.exists():
        return result
    command = run_command(
        "release package",
        ["python", "scripts/package_release.py", "--version", VERSION, "--output-dir", "dist"],
        [sys.executable, "scripts/package_release.py", "--version", VERSION, "--output-dir", "dist"],
        ROOT,
    )
    command_results.append(command)
    result["command"] = command
    zip_paths = sorted((ROOT / "dist").glob(f"researchagent-{VERSION}-*.zip"))
    result["zips"] = [inspect_zip(path) for path in zip_paths]
    result["passed"] = command["passed"] and bool(result["zips"]) and all(
        zip_result["passed"] for zip_result in result["zips"]
    )
    return result


def build_commands() -> list[tuple[str, list[str], list[str], Path]]:
    python = sys.executable
    return [
        (
            "compile backend and scripts",
            ["python", "-m", "compileall", "services/api", "scripts"],
            [python, "-m", "compileall", "services/api", "scripts"],
            ROOT,
        ),
        (
            "backend tests",
            ["python", "-m", "pytest", "services/api/tests", "-q"],
            [python, "-m", "pytest", "services/api/tests", "-q"],
            ROOT,
        ),
        (
            "reset demo",
            ["python", "scripts/reset_demo.py", "--yes"],
            [python, "scripts/reset_demo.py", "--yes"],
            ROOT,
        ),
        (
            "seed demo",
            ["python", "scripts/seed_demo.py"],
            [python, "scripts/seed_demo.py"],
            ROOT,
        ),
        (
            "run demo",
            ["python", "scripts/run_demo.py"],
            [python, "scripts/run_demo.py"],
            ROOT,
        ),
        (
            "v2 validation",
            ["python", "scripts/validate_v2.py"],
            [python, "scripts/validate_v2.py"],
            ROOT,
        ),
        (
            "frontend typecheck",
            ["npm", "run", "typecheck"],
            [command_name("npm"), "run", "typecheck"],
            ROOT / "apps" / "web",
        ),
        (
            "frontend build",
            ["npm", "run", "build"],
            [command_name("npm"), "run", "build"],
            ROOT / "apps" / "web",
        ),
        (
            "frontend playwright",
            ["npx", "playwright", "test"],
            [command_name("npx"), "playwright", "test"],
            ROOT / "apps" / "web",
        ),
    ]


def write_reports(report: dict[str, Any]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    command_lines = []
    for command in report["commands"]:
        status = "PASS" if command["passed"] else "FAIL"
        line = f"- {status}: `{command['command']}`"
        if command["failure_reason"]:
            line += f" ({command['failure_reason']})"
        command_lines.append(line)
    artifact_lines = []
    for artifact in report["artifacts"]:
        status = "PASS" if artifact["passed"] else "FAIL"
        line = f"- {status}: `{artifact['path']}`"
        if artifact["failure_reason"]:
            line += f" ({artifact['failure_reason']})"
        artifact_lines.append(line)
    md = [
        "# ResearchAgent Local Verification Report",
        "",
        f"- Created at: {report['created_at']}",
        f"- Final status: **{report['final_status']}**",
        f"- LLM mode: `{report['environment']['LLM_MODE']}`",
        f"- Reports: `reports/verification_report.json`, `reports/verification_report.md`",
        "",
        "## Commands",
        "",
        *command_lines,
        "",
        "## Artifacts",
        "",
        *artifact_lines,
        "",
        "## Integrity Checks",
        "",
        f"- Review report contract: {'PASS' if report['review_report']['passed'] else 'FAIL'}",
        f"- RAG answer contract: {'PASS' if report['rag_answers']['passed'] else 'FAIL'}",
        f"- Generated safety scan: {'PASS' if report['safety_scan']['passed'] else 'FAIL'}",
        f"- Literature metadata check: {'PASS' if report['literature_metadata']['passed'] else 'FAIL'}",
        f"- Release package check: {'PASS' if report['release_package']['passed'] else 'FAIL'}",
        "",
        "## Known Limitations",
        "",
        *[f"- {item}" for item in report["known_limitations"]],
        "",
    ]
    REPORT_MD.write_text("\n".join(md), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local ResearchAgent verification in mock/offline mode.")
    parser.add_argument(
        "--skip-commands",
        action="store_true",
        help="Only inspect existing artifacts and packages. Intended for debugging the verifier itself.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command_results: list[dict[str, Any]] = []
    if not args.skip_commands:
        for label, display, actual, cwd in build_commands():
            print(f"[verify_local] {label}...", flush=True)
            command_results.append(run_command(label, display, actual, cwd))

    artifact_checks, parsed = check_artifacts()
    review_check = check_review_report(parsed)
    rag_check = check_rag_answers(parsed)
    safety_check = check_safety_text()
    metadata_check = check_literature_metadata(parsed)
    release_check = package_checks(command_results)

    all_checks_passed = (
        all(command["passed"] for command in command_results)
        and all(artifact["passed"] for artifact in artifact_checks)
        and review_check["passed"]
        and rag_check["passed"]
        and safety_check["passed"]
        and metadata_check["passed"]
        and release_check["passed"]
    )
    report = {
        "created_at": utc_now(),
        "final_status": "passed" if all_checks_passed else "failed",
        "environment": {
            "APP_ENV": "local",
            "DATABASE_BACKEND": "sqlite",
            "QUEUE_MODE": "inline",
            "AUTH_MODE": "disabled",
            "LLM_MODE": "mock",
            "external_network_required": False,
            "live_llm_required": False,
        },
        "commands": command_results,
        "artifacts": artifact_checks,
        "review_report": review_check,
        "rag_answers": rag_check,
        "safety_scan": safety_check,
        "literature_metadata": metadata_check,
        "release_package": release_check,
        "known_limitations": [
            "This verifier runs the repository in mock/offline mode and does not call live LLMs or external research services.",
            "It validates demo artifact integrity; it does not certify scientific correctness, peer review readiness, or production readiness.",
            "Generated demo literature remains placeholder evidence unless explicitly human-verified elsewhere.",
        ],
    }
    write_reports(report)
    print(f"[verify_local] final status: {report['final_status']}")
    print(f"[verify_local] wrote {rel(REPORT_JSON)}")
    print(f"[verify_local] wrote {rel(REPORT_MD)}")
    return 0 if all_checks_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
