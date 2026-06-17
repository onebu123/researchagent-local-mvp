from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, relative_posix, write_json, write_text
from app.tools.human_review_queue import build_human_review_queue

PACKAGE_DIR = "exports/evidence_trust_package"
PACKAGE_ZIP = "exports/evidence_trust_package/evidence_trust_package.zip"
MANIFEST = "exports/evidence_trust_package/manifest.json"
TRUST_REPORT = "trust/evidence_trust_report.md"
CANDIDATE_FILES = [
    "literature/literature_index.json",
    "literature/rag/rag_index.json",
    "literature/rag/chunks.jsonl",
    "literature/rag/rag_answers.jsonl",
    "provenance/claim_audit.json",
    "provenance/claim_audit.md",
    "provenance/source_passage_evidence.json",
    "reviews/review_report.json",
    "reviews/review_report.md",
    "manuscript/paper_plan.json",
    "manuscript/outline.json",
    "manuscript/draft_full.md",
    "manuscript/draft_full.tex",
    "manuscript/writing_audit.json",
    "manuscript/writing_rounds.jsonl",
    "manuscript/revision_plan.json",
    "manuscript/revision_plan.md",
    "manuscript/patch_suggestions.json",
    "trust/human_review_queue.json",
    "trust/human_review_decisions.jsonl",
    "trust/evidence_trust_report.md",
    "auto_scientist/ideas.json",
    "auto_scientist/reference_brief.json",
    "auto_scientist/reference_brief.md",
    "auto_scientist/experiment_plan.json",
    "auto_scientist/runs.jsonl",
    "auto_scientist/latest_run.json",
    "auto_scientist/generated_code_approvals.jsonl",
    "auto_scientist/generated_code_reruns.jsonl",
    "auto_scientist/code_revision_rounds.jsonl",
    "auto_scientist/code_review_rounds.jsonl",
    "auto_scientist/docker_image_policy.json",
    "jobs/jobs.jsonl",
    "jobs/latest_job.json",
    "auto_scientist/experiment_tree.json",
    "auto_scientist/experiment_tree.md",
    "auto_scientist/experiment_tree_selection.json",
    "auto_scientist/experiment_tree_reruns.jsonl",
    "auto_scientist/paper_rewrites.jsonl",
    "auto_scientist/latest_paper_rewrite.json",
    "auto_scientist/tree_revision_plan.json",
    "auto_scientist/tree_revision_plan.md",
    "auto_scientist/tree_revision_patches.json",
    "auto_scientist/tree_revision_applications.jsonl",
    "auto_scientist/latest_tree_revision_application.json",
    "auto_scientist/experiment_claim_bindings.json",
    "auto_scientist/experiment_claim_bindings.md",
    "auto_scientist/latest_experiment_claim_binding.json",
    "manuscript/paper_citation_bindings.json",
    "manuscript/paper_citation_bindings.md",
    "manuscript/latest_paper_citation_binding.json",
    "manuscript/auto_scientist_paper_citation_bound.md",
    "manuscript/latex_compile_report.json",
    "manuscript/latex_compile_report.md",
    "manuscript/auto_scientist_paper.pdf",
    "manuscript/auto_scientist_paper_preview.pdf",
    "auto_scientist/manuscript_claim_trace.jsonl",
    "auto_scientist/analysis.json",
    "auto_scientist/auto_scientist_report.md",
    "auto_scientist/scientist_review.json",
    "auto_scientist/scientist_review.md",
    "auto_scientist/paper_audit.json",
    "manuscript/auto_scientist_paper.md",
    "manuscript/auto_scientist_paper.tex",
    "manuscript/auto_scientist_paper_revised.md",
    "manuscript/auto_scientist_paper_revised.tex",
    "audit/audit_log.jsonl",
]
EXCLUDED_MARKERS = [".env", "node_modules", ".next", "__pycache__", ".pytest_cache", "projects/"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_project_file(project_dir: Path, relative_path: str) -> Path | None:
    normalized = relative_path.replace("\\", "/").lstrip("/")
    if ".." in normalized.split("/"):
        return None
    if any(marker in normalized for marker in EXCLUDED_MARKERS):
        return None
    path = (project_dir / normalized).resolve()
    try:
        path.relative_to(project_dir.resolve())
    except ValueError:
        return None
    if not path.exists() or not path.is_file():
        return None
    return path


def _artifact_kind(relative_path: str) -> str:
    if relative_path.startswith("literature/"):
        return "literature"
    if relative_path.startswith("provenance/"):
        return "provenance"
    if relative_path.startswith("reviews/"):
        return "review"
    if relative_path.startswith("manuscript/"):
        return "manuscript"
    if relative_path.startswith("trust/"):
        return "trust"
    if relative_path.startswith("audit/"):
        return "audit"
    if relative_path.startswith("auto_scientist/"):
        return "auto_scientist"
    return "artifact"


def _text_safety_warnings(project_dir: Path, files: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    root = project_dir.resolve().as_posix()
    secret_pattern = re.compile(r"(?:api[_-]?key|secret|token|sk-[A-Za-z0-9])", re.IGNORECASE)
    for item in files:
        path = project_dir / str(item["relative_path"])
        if not path.exists() or not path.is_file():
            continue
        if path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")[:200000]
        if root in text or re.search(r"[A-Za-z]:[\\/]", text):
            warnings.append(f"absolute path-like content detected in {item['relative_path']}")
        if secret_pattern.search(text):
            warnings.append(f"secret-like token detected in {item['relative_path']}")
    return warnings


def _trust_report(project_dir: Path, project_id: str, queue: dict[str, Any]) -> str:
    claim_audit = _read_json(project_dir / "provenance" / "claim_audit.json", {})
    summary = claim_audit.get("summary", {}) if isinstance(claim_audit, dict) else {}
    binding_payload = _read_json(project_dir / "auto_scientist" / "experiment_claim_bindings.json", {})
    binding_summary = binding_payload.get("summary", {}) if isinstance(binding_payload, dict) else {}
    citation_payload = _read_json(project_dir / "manuscript" / "paper_citation_bindings.json", {})
    citation_summary = citation_payload.get("summary", {}) if isinstance(citation_payload, dict) else {}
    compile_report = _read_json(project_dir / "manuscript" / "latex_compile_report.json", {})
    queue_summary = queue.get("summary", {}) if isinstance(queue, dict) else {}
    lines = [
        "# Evidence Trust Report",
        "",
        "> This report summarizes local evidence QA, claim audit, human-review signals, and export limitations. It is not a compliance certificate, citation-verification certificate, peer review, or scientific proof.",
        "",
        "## Evidence QA / Claim Audit",
        "",
        f"- Supported claims: {summary.get('supported', 0)}",
        f"- Weakly supported claims: {summary.get('weakly_supported', 0)}",
        f"- Unsupported claims: {summary.get('unsupported', 0)}",
        f"- Human review required: {claim_audit.get('human_review_required_count', 0) if isinstance(claim_audit, dict) else 0}",
        "",
        "## Auto Scientist Experiment Claim Bindings",
        "",
        f"- Bound manuscript claims: {binding_summary.get('bound', 0)}",
        f"- Weakly bound manuscript claims: {binding_summary.get('weak_binding', 0)}",
        f"- Unbound manuscript claims: {binding_summary.get('unbound', 0)}",
        f"- Binding review items: {binding_summary.get('human_review_required', 0)}",
        "",
        "## Paper Citation / Reference Bindings",
        "",
        f"- Citation-like sentences: {citation_summary.get('claim_like_sentences', 0)}",
        f"- Source-passage bound citations: {citation_summary.get('bound', 0)}",
        f"- Weak citation bindings: {citation_summary.get('weak_binding', 0)}",
        f"- Unbound citation claims: {citation_summary.get('unbound', 0)}",
        f"- Formal references available: {citation_summary.get('formal_reference_available', 0)}",
        f"- Citation binding review items: {citation_summary.get('human_review_required', 0)}",
        "",
        "## LaTeX / PDF Pipeline",
        "",
        f"- Compile status: {compile_report.get('compile_status', 'not_generated') if isinstance(compile_report, dict) else 'not_generated'}",
        f"- Compiled PDF: {compile_report.get('pdf_file') if isinstance(compile_report, dict) else None}",
        f"- Preview PDF: {compile_report.get('preview_pdf_file') if isinstance(compile_report, dict) else None}",
        "",
        "## Human Review Queue",
        "",
        f"- Pending review items: {queue_summary.get('pending', 0)}",
        f"- Blocking review items: {queue_summary.get('blocking', 0)}",
        f"- Warning review items: {queue_summary.get('warning', 0)}",
        "",
        "## Limitations",
        "",
        "- Local parsed literature text is the only evidence source in this package.",
        "- Unsupported answers are preserved as research-integrity signals.",
        "- Human approvals are local workflow decisions, not formal peer review or citation verification.",
        "- Package files use project-relative paths and exclude runtime caches and secrets where detected.",
    ]
    return "\n".join(lines)


def build_evidence_trust_package(project_dir: Path, project_id: str) -> dict[str, Any]:
    ensure_dir(project_dir / PACKAGE_DIR)
    queue = build_human_review_queue(project_dir, project_id)
    write_text(project_dir / TRUST_REPORT, _trust_report(project_dir, project_id, queue))
    candidate_paths = list(CANDIDATE_FILES)
    for base in [
        project_dir / "auto_scientist" / "experiments",
        project_dir / "auto_scientist" / "generated_code",
        project_dir / "jobs",
    ]:
        if base.exists():
            for path in sorted(base.rglob("*")):
                if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt", ".log", ".svg", ".py", ".pdf"}:
                    try:
                        candidate_paths.append(relative_posix(path, project_dir))
                    except ValueError:
                        continue
    files: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for relative_path in candidate_paths:
        if relative_path in seen_paths:
            continue
        seen_paths.add(relative_path)
        path = _safe_project_file(project_dir, relative_path)
        if path is None:
            continue
        files.append(
            {
                "relative_path": relative_posix(path, project_dir),
                "artifact_kind": _artifact_kind(relative_path),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    warnings = _text_safety_warnings(project_dir, files)
    manifest = {
        "package_type": "evidence_trust_package",
        "project_id": project_id,
        "generated_at": _utc_now(),
        "relative_path": MANIFEST,
        "package_file": PACKAGE_ZIP,
        "files": files,
        "warnings": warnings,
        "exclusions": [
            ".env*",
            "node_modules/",
            ".next/",
            "projects outside current project",
            "local absolute paths",
            "secret-like tokens",
            "runtime caches",
        ],
        "limitations": [
            "This is an audit handoff artifact, not a compliance certificate.",
            "Failed or pending checks remain visible and are not marked release-ready.",
        ],
    }
    write_json(project_dir / MANIFEST, manifest)
    package_path = project_dir / PACKAGE_ZIP
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in files:
            rel = str(item["relative_path"])
            path = project_dir / rel
            if not path.exists():
                warnings.append(f"candidate disappeared before packaging: {rel}")
                continue
            zf.write(path, arcname=f"evidence_trust_package/{rel}")
        zf.write(project_dir / MANIFEST, arcname="evidence_trust_package/manifest.json")
    result = {
        **manifest,
        "available": True,
        "size_bytes": package_path.stat().st_size,
        "package_sha256": _sha256_file(package_path),
    }
    write_json(project_dir / MANIFEST, result)
    append_audit_event(
        project_dir,
        project_id,
        "build_evidence_trust_package",
        "Evidence trust package was generated for local audit handoff.",
        {
            "package_file": PACKAGE_ZIP,
            "manifest_file": MANIFEST,
            "included_file_count": len(files),
            "warning_count": len(warnings),
        },
        source="api",
        event_category="trust",
        risk_level="medium" if warnings else "low",
        entity_type="trust",
        entity_id="evidence_trust_package",
    )
    return result


def latest_evidence_trust_package_info(project_dir: Path, project_id: str) -> dict[str, Any]:
    payload = _read_json(project_dir / MANIFEST, {})
    if isinstance(payload, dict) and payload:
        return payload
    return {
        "package_type": "evidence_trust_package",
        "project_id": project_id,
        "available": False,
        "relative_path": MANIFEST,
        "package_file": PACKAGE_ZIP,
        "files": [],
        "warnings": ["Evidence trust package has not been generated."],
    }
