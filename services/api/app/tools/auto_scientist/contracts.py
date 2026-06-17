from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.file_tools import ensure_dir, write_json, write_text

SCHEMA_PREFIX = "researchagent.auto_scientist"
AUTO_SCIENTIST_DIR = "auto_scientist"
IDEAS_JSON = "auto_scientist/ideas.json"
EXPERIMENT_PLAN_JSON = "auto_scientist/experiment_plan.json"
RUNS_JSONL = "auto_scientist/runs.jsonl"
LATEST_RUN_JSON = "auto_scientist/latest_run.json"
ANALYSIS_JSON = "auto_scientist/analysis.json"
REVIEW_JSON = "auto_scientist/scientist_review.json"
REVIEW_MD = "auto_scientist/scientist_review.md"
REPORT_MD = "auto_scientist/auto_scientist_report.md"
EXPERIMENT_TREE_JSON = "auto_scientist/experiment_tree.json"
EXPERIMENT_TREE_MD = "auto_scientist/experiment_tree.md"
EXPERIMENT_TREE_FAILURES_JSONL = "auto_scientist/experiment_tree_failures.jsonl"
GENERATED_CODE_APPROVALS_JSONL = "auto_scientist/generated_code_approvals.jsonl"
CODE_REVISION_ROUNDS_JSONL = "auto_scientist/code_revision_rounds.jsonl"
CODE_REVIEW_ROUNDS_JSONL = "auto_scientist/code_review_rounds.jsonl"
DOCKER_IMAGE_POLICY_JSON = "auto_scientist/docker_image_policy.json"
MANUSCRIPT_CLAIM_BINDINGS_JSON = "auto_scientist/manuscript_claim_bindings.json"
MANUSCRIPT_CLAIM_BINDINGS_MD = "auto_scientist/manuscript_claim_bindings.md"
LATEST_MANUSCRIPT_CLAIM_BINDING_JSON = "auto_scientist/latest_manuscript_claim_binding.json"

SAFETY_LIMITATIONS = [
    "Auto Scientist MVP runs only registered safe local experiment templates.",
    "It does not execute arbitrary LLM-generated code by default; generated-code experiments require explicit opt-in and sandbox policy gates.",
    "LLM/provided generated-code experiments can require a recorded human approval before sandbox execution.",
    "Docker sandbox mode uses a local image allowlist and never pulls images automatically.",
    "It does not invent experiments, p-values, statistical significance, causal effects, DOI values, or verified references.",
    "All manuscripts and reviews are draft artifacts requiring human scientific review.",
]

REGISTERED_EXPERIMENT_NOTICE = (
    "Safe experiment runner: registered local templates only; arbitrary_code_execution=false."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_auto_scientist_dirs(project_dir: Path) -> None:
    ensure_dir(project_dir / AUTO_SCIENTIST_DIR)
    ensure_dir(project_dir / AUTO_SCIENTIST_DIR / "experiments")
    ensure_dir(project_dir / AUTO_SCIENTIST_DIR / "figures")


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_project_json(project_dir: Path, relative_path: str, payload: Any) -> None:
    write_json(project_dir / relative_path, payload)


def write_project_text(project_dir: Path, relative_path: str, content: str) -> None:
    write_text(project_dir / relative_path, content)


def append_jsonl(project_dir: Path, relative_path: str, record: dict[str, Any]) -> None:
    path = project_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(project_dir: Path, relative_path: str) -> list[dict[str, Any]]:
    path = project_dir / relative_path
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


def safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value.lower()).strip("_")
    return cleaned or "item"
