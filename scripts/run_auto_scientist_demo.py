from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.database import initialize_database
from app.schemas import ProjectCreate
from app.services.project_service import project_service
from app.services.storage_service import storage_service
from app.tools.auto_scientist.experiment_tree_ops import (
    list_experiment_tree_nodes,
    rewrite_auto_scientist_paper_from_tree,
    select_experiment_tree_node,
)
from app.tools.auto_scientist.scientist_loop import run_auto_scientist
from app.tools.auto_scientist.tree_revision_loop import generate_tree_revision_plan
from app.tools.evidence_trust_package import build_evidence_trust_package
from app.tools.human_review_queue import build_human_review_queue
from app.tools.job_manager import read_project_job_events, run_project_job
from app.tools.literature_rag import ask_literature_rag, build_literature_rag
from scripts.seed_demo import write_demo_csv, write_demo_literature, write_simple_demo_pdf

DEFAULT_PROJECT_ID = "demo_auto_scientist"
DEFAULT_TOPIC = "local evidence QA for materials research"
DEFAULT_RESEARCH_QUESTION = (
    "Can local evidence QA and safe experiments support cautious manuscript drafting?"
)

REQUIRED_DEMO_ARTIFACTS = [
    "literature/literature_index.json",
    "literature/rag/chunks.jsonl",
    "literature/rag/rag_answers.jsonl",
    "auto_scientist/ideas.json",
    "auto_scientist/experiment_plan.json",
    "auto_scientist/runs.jsonl",
    "auto_scientist/latest_run.json",
    "auto_scientist/analysis.json",
    "auto_scientist/auto_scientist_report.md",
    "auto_scientist/scientist_review.json",
    "manuscript/auto_scientist_paper.md",
    "manuscript/auto_scientist_paper.tex",
    "auto_scientist/experiment_tree.json",
    "auto_scientist/experiment_claim_bindings.json",
    "manuscript/paper_citation_bindings.json",
    "manuscript/latex_compile_report.json",
    "trust/human_review_queue.json",
    "exports/evidence_trust_package/manifest.json",
]

OPTIONAL_DEMO_ARTIFACTS = [
    "auto_scientist/experiment_tree_selection.json",
    "auto_scientist/paper_rewrites.jsonl",
    "auto_scientist/tree_revision_plan.json",
    "auto_scientist/tree_revision_patches.json",
    "manuscript/auto_scientist_paper_citation_bound.md",
    "manuscript/auto_scientist_paper_preview.pdf",
]


def _safe_reset_project(project_id: str) -> Path:
    project_dir = storage_service.project_dir(project_id).resolve()
    projects_root = (ROOT / "projects").resolve()
    try:
        project_dir.relative_to(projects_root)
    except ValueError as exc:
        raise RuntimeError(f"refuse to reset project outside local projects root: {project_dir}") from exc
    if project_dir.exists():
        shutil.rmtree(project_dir)
    return project_dir


def seed_auto_scientist_demo_project(project_id: str, reset: bool = True) -> Path:
    initialize_database()
    if reset:
        _safe_reset_project(project_id)
    payload = ProjectCreate(
        name="Auto Scientist Local Demo",
        domain="materials",
        language="en",
        output_format="markdown",
    )
    project_service.create_project(payload, project_id=project_id, overwrite=True)
    project_dir = storage_service.ensure_project_structure(project_id)
    write_demo_literature(project_dir)
    write_simple_demo_pdf(project_dir)
    write_demo_csv(project_dir)
    return project_dir


def _latest_tree_node_id(project_dir: Path) -> str | None:
    nodes_payload = list_experiment_tree_nodes(project_dir)
    nodes = [item for item in nodes_payload.get("nodes", []) if isinstance(item, dict)]
    if not nodes:
        return None
    best = max(nodes, key=lambda item: float(item.get("score") or 0.0))
    return str(best.get("node_id")) if best.get("node_id") else None


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _read_jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())


def _artifact_record(project_dir: Path, relative_path: str) -> dict[str, Any]:
    path = project_dir / relative_path
    return {
        "relative_path": relative_path,
        "exists": path.exists() and path.is_file(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
    }


def build_auto_scientist_demo_report(
    project_dir: Path,
    project_id: str,
    *,
    job_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    latest_run = _read_json(project_dir / "auto_scientist" / "latest_run.json", {})
    queue = _read_json(project_dir / "trust" / "human_review_queue.json", {})
    trust_manifest = _read_json(project_dir / "exports" / "evidence_trust_package" / "manifest.json", {})
    claim_bindings = _read_json(project_dir / "auto_scientist" / "experiment_claim_bindings.json", {})
    citation_bindings = _read_json(project_dir / "manuscript" / "paper_citation_bindings.json", {})
    compile_report = _read_json(project_dir / "manuscript" / "latex_compile_report.json", {})
    tree_revision = _read_json(project_dir / "auto_scientist" / "tree_revision_plan.json", {})
    job_events = {}
    if job_record and isinstance(job_record.get("job_id"), str):
        try:
            job_events = read_project_job_events(project_id, str(job_record["job_id"]), limit=1000)
        except Exception as exc:  # keep demo report generation robust
            job_events = {"error": exc.__class__.__name__}

    required = [_artifact_record(project_dir, item) for item in REQUIRED_DEMO_ARTIFACTS]
    optional = [_artifact_record(project_dir, item) for item in OPTIONAL_DEMO_ARTIFACTS]
    missing_required = [item["relative_path"] for item in required if not item["exists"]]
    generated_code_outputs = list((project_dir / "auto_scientist" / "generated_code").glob("**/sandbox_result.json"))
    report = {
        "schema_version": "researchagent.auto_scientist_demo_report.v1",
        "project_id": project_id,
        "project_dir_name": project_dir.name,
        "passed": not missing_required,
        "missing_required_artifacts": missing_required,
        "required_artifacts": required,
        "optional_artifacts": optional,
        "summary": {
            "run_id": latest_run.get("run_id") if isinstance(latest_run, dict) else None,
            "run_status": latest_run.get("status") if isinstance(latest_run, dict) else None,
            "generated_code_experiments_enabled": bool(latest_run.get("generated_code_experiments_enabled")) if isinstance(latest_run, dict) else False,
            "generated_code_sandbox_mode": latest_run.get("generated_code_sandbox_mode") if isinstance(latest_run, dict) else None,
            "experiment_tree_search_enabled": bool(latest_run.get("experiment_tree_search_enabled")) if isinstance(latest_run, dict) else False,
            "experiment_count": _read_jsonl_count(project_dir / "auto_scientist" / "runs.jsonl"),
            "generated_code_sandbox_result_count": len(generated_code_outputs),
            "job_status": job_record.get("status") if isinstance(job_record, dict) else None,
            "job_event_count": len(job_events.get("events", [])) if isinstance(job_events, dict) else 0,
            "human_review_pending": (queue.get("summary") or {}).get("pending") if isinstance(queue, dict) else None,
            "trust_package_file_count": len(trust_manifest.get("files", [])) if isinstance(trust_manifest, dict) else 0,
            "experiment_claim_binding_summary": claim_bindings.get("summary") if isinstance(claim_bindings, dict) else None,
            "paper_citation_binding_summary": citation_bindings.get("summary") if isinstance(citation_bindings, dict) else None,
            "latex_compile_status": compile_report.get("compile_status") if isinstance(compile_report, dict) else None,
            "tree_revision_patch_count": len(tree_revision.get("patch_suggestions", [])) if isinstance(tree_revision, dict) else 0,
        },
        "job": job_record or {},
        "job_events": job_events,
        "limitations": [
            "This is a deterministic local Auto Scientist demo, not a scientific discovery benchmark.",
            "Generated-code experiments remain sandboxed and review-gated by policy; artifacts require human review.",
            "Citation binding and PDF preview generation do not guarantee publication readiness, citation verification, or peer review.",
        ],
    }
    return report


def _markdown_report(report: dict[str, Any]) -> str:
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    missing = report.get("missing_required_artifacts", []) if isinstance(report.get("missing_required_artifacts"), list) else []
    lines = [
        "# Auto Scientist End-to-End Demo Report",
        "",
        "> This is a local deterministic handoff report. It is not a scientific-discovery benchmark, peer review, citation-verification certificate, or publication-readiness certificate.",
        "",
        "## Status",
        "",
        f"- Passed required artifact checks: {bool(report.get('passed'))}",
        f"- Missing required artifacts: {len(missing)}",
        f"- Run status: {summary.get('run_status')}",
        f"- Job status: {summary.get('job_status')}",
        f"- Job event count: {summary.get('job_event_count')}",
        f"- Experiments recorded: {summary.get('experiment_count')}",
        f"- Generated-code sandbox results: {summary.get('generated_code_sandbox_result_count')}",
        f"- Trust package file count: {summary.get('trust_package_file_count')}",
        "",
        "## Binding and Compilation",
        "",
        f"- Experiment claim binding summary: `{json.dumps(summary.get('experiment_claim_binding_summary'), ensure_ascii=False)}`",
        f"- Paper citation binding summary: `{json.dumps(summary.get('paper_citation_binding_summary'), ensure_ascii=False)}`",
        f"- LaTeX/PDF compile status: {summary.get('latex_compile_status')}",
        f"- Tree revision patch count: {summary.get('tree_revision_patch_count')}",
        "",
        "## Missing Required Artifacts",
        "",
    ]
    if missing:
        lines.extend(f"- `{item}`" for item in missing)
    else:
        lines.append("- None.")
    lines.extend([
        "",
        "## Limitations",
        "",
    ])
    for item in report.get("limitations", []):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def run_demo(args: argparse.Namespace) -> dict[str, Any]:
    project_dir = seed_auto_scientist_demo_project(args.project_id, reset=not args.no_reset)
    build_literature_rag(project_dir, args.project_id)
    ask_literature_rag(
        project_dir,
        args.project_id,
        "What local evidence is available for cautious manuscript drafting?",
        retrieval_mode="local_hybrid_fts",
    )

    def runner(update):
        update("auto scientist demo: starting local run", 0.05)
        result = run_auto_scientist(
            args.project_id,
            topic=args.topic,
            research_question=args.research_question,
            max_ideas=args.max_ideas,
            max_experiments_per_idea=args.max_experiments_per_idea,
            paper_type="research_article",
            retrieval_mode="local_hybrid_fts",
            write_paper=True,
            export_latex=True,
            allow_generated_code_experiments=args.generated_code,
            generated_code_timeout_seconds=args.generated_code_timeout_seconds,
            generated_code_max_memory_mb=args.generated_code_max_memory_mb,
            generated_code_sandbox_mode="subprocess",
            generated_code_source_mode="deterministic",
            generated_code_strategy=args.generated_code_strategy,
            generated_code_requires_approval=False,
            generated_code_approved=True,
            enable_generated_code_revision_loop=args.generated_code,
            generated_code_revision_rounds=1,
            enable_experiment_tree_search=args.tree_search,
            experiment_tree_max_depth=args.experiment_tree_max_depth,
            experiment_tree_branching_factor=args.experiment_tree_branching_factor,
            progress_callback=update,
        )
        update("auto scientist demo: local run completed", 0.90)
        return result

    job = run_project_job(
        args.project_id,
        "auto_scientist_demo",
        {
            "topic": args.topic,
            "research_question": args.research_question,
            "generated_code": args.generated_code,
            "tree_search": args.tree_search,
        },
        runner,
    )

    node_id = _latest_tree_node_id(project_dir)
    if node_id:
        select_experiment_tree_node(
            project_dir,
            args.project_id,
            node_id,
            reason="Selected by deterministic end-to-end demo for downstream paper rewrite and revision planning.",
            reviewer="auto_scientist_demo",
        )
        rewrite_auto_scientist_paper_from_tree(
            project_dir,
            args.project_id,
            node_id=node_id,
            reason="End-to-end demo rewrite from selected local experiment tree node.",
        )
        generate_tree_revision_plan(
            project_dir,
            args.project_id,
            reason="End-to-end demo revision plan from selected experiment tree node.",
        )

    queue = build_human_review_queue(project_dir, args.project_id)
    package = build_evidence_trust_package(project_dir, args.project_id)
    report = build_auto_scientist_demo_report(project_dir, args.project_id, job_record=job)
    report["human_review_queue"] = {"summary": queue.get("summary"), "relative_path": queue.get("relative_path")}
    report["evidence_trust_package"] = {
        "package_file": package.get("package_file"),
        "manifest_file": package.get("manifest_file"),
        "file_count": len(package.get("files", [])) if isinstance(package.get("files"), list) else None,
    }
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path = output_path.with_suffix(".md")
    md_path.write_text(_markdown_report(report), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a deterministic local Auto Scientist end-to-end demo.")
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--topic", default=DEFAULT_TOPIC)
    parser.add_argument("--research-question", default=DEFAULT_RESEARCH_QUESTION)
    parser.add_argument("--output", default=str(ROOT / "reports" / "auto_scientist_demo_report.json"))
    parser.add_argument("--no-reset", action="store_true", help="Do not reset the target demo project directory before seeding.")
    parser.add_argument("--max-ideas", type=int, default=2)
    parser.add_argument("--max-experiments-per-idea", type=int, default=1)
    parser.add_argument("--generated-code", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--generated-code-strategy", default="retrieval_ablation")
    parser.add_argument("--generated-code-timeout-seconds", type=int, default=5)
    parser.add_argument("--generated-code-max-memory-mb", type=int, default=128)
    parser.add_argument("--tree-search", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--experiment-tree-max-depth", type=int, default=1)
    parser.add_argument("--experiment-tree-branching-factor", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_demo(args)
    output = Path(args.output).resolve()
    print(f"Auto Scientist demo report: {output}")
    print(f"Auto Scientist demo markdown: {output.with_suffix('.md')}")
    print(f"Passed required artifact checks: {report.get('passed')}")
    missing = report.get("missing_required_artifacts") or []
    if missing:
        raise SystemExit(f"Missing required Auto Scientist demo artifacts: {missing}")


if __name__ == "__main__":
    main()
