from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import storage_service
from app.tools.audit_log import append_audit_event
from app.tools.auto_scientist.contracts import (
    ANALYSIS_JSON,
    IDEAS_JSON,
    LATEST_RUN_JSON,
    REPORT_MD,
    REVIEW_JSON,
    REVIEW_MD,
    RUNS_JSONL,
    EXPERIMENT_TREE_JSON,
    SAFETY_LIMITATIONS,
    SCHEMA_PREFIX,
    ensure_auto_scientist_dirs,
    read_json,
    read_jsonl,
    utc_now,
    write_project_json,
)
from app.tools.auto_scientist.experiment_claim_binding import (
    EXPERIMENT_CLAIM_BINDINGS_JSON,
    generate_experiment_claim_bindings,
)
from app.tools.auto_scientist.experiment_runner import build_experiment_plan, read_experiment_plan, run_experiment_plan
from app.tools.auto_scientist.experiment_tree_search import run_experiment_tree_search
from app.tools.auto_scientist.generated_code_revision import run_generated_code_revision_loop
from app.tools.auto_scientist.idea_generator import generate_scientist_ideas, read_scientist_ideas
from app.tools.auto_scientist.result_analysis import analyze_experiment_results
from app.tools.auto_scientist.scientist_reviewer import run_scientist_reviewer
from app.tools.auto_scientist.scientist_paper import generate_auto_scientist_paper
from app.tools.auto_scientist.paper_citation_binding import PAPER_CITATION_BINDINGS_JSON, generate_paper_citation_bindings
from app.tools.auto_scientist.paper_compile import LATEX_COMPILE_REPORT_JSON, compile_auto_scientist_paper
from app.tools.paper_writer.latex_export import export_draft_latex
from app.tools.paper_writer.outline_builder import generate_paper_outline
from app.tools.paper_writer.paper_plan import generate_paper_plan
from app.tools.paper_writer.section_writer import generate_full_draft


def _project_context(project_id: str):
    project = project_service.require_project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    return project, project_dir


def _new_run_id() -> str:
    return "scientist_run_" + utc_now().replace(":", "").replace("-", "").replace(".", "").replace("+", "z")


def read_auto_scientist_status(project_id: str) -> dict[str, Any]:
    try:
        _project, project_dir = _project_context(project_id)
    except ProjectNotFoundError:
        raise
    latest = read_json(project_dir / LATEST_RUN_JSON, {})
    return {
        "project_id": project_id,
        "ideas": {"available": bool(read_scientist_ideas(project_dir)), "relative_path": IDEAS_JSON},
        "experiment_plan": {"available": bool(read_experiment_plan(project_dir)), "relative_path": "auto_scientist/experiment_plan.json"},
        "analysis": {"available": (project_dir / ANALYSIS_JSON).exists(), "relative_path": ANALYSIS_JSON},
        "review": {"available": (project_dir / REVIEW_JSON).exists(), "relative_path": REVIEW_JSON},
        "experiment_tree": {"available": (project_dir / EXPERIMENT_TREE_JSON).exists(), "relative_path": EXPERIMENT_TREE_JSON},
        "paper_citation_bindings": {"available": (project_dir / PAPER_CITATION_BINDINGS_JSON).exists(), "relative_path": PAPER_CITATION_BINDINGS_JSON},
        "paper_compile": {"available": (project_dir / LATEX_COMPILE_REPORT_JSON).exists(), "relative_path": LATEX_COMPILE_REPORT_JSON},
        "latest_run": latest if isinstance(latest, dict) else {},
        "run_count": len(read_jsonl(project_dir, RUNS_JSONL)),
        "generated_code_experiments_enabled": bool((latest if isinstance(latest, dict) else {}).get("generated_code_experiments_enabled")),
        "sandboxed_generated_code": bool((latest if isinstance(latest, dict) else {}).get("sandboxed_generated_code")),
        "experiment_tree_search_enabled": bool((latest if isinstance(latest, dict) else {}).get("experiment_tree_search_enabled")),
        "generated_code_revision_loop_enabled": bool((latest if isinstance(latest, dict) else {}).get("generated_code_revision_loop_enabled")),
        "limitations": SAFETY_LIMITATIONS,
    }


def run_auto_scientist(
    project_id: str,
    topic: str | None = None,
    research_question: str | None = None,
    max_ideas: int = 3,
    max_experiments_per_idea: int = 2,
    paper_type: str = "research_article",
    retrieval_mode: str = "local_hybrid_fts",
    write_paper: bool = True,
    export_latex: bool = True,
    allow_generated_code_experiments: bool = False,
    generated_code_timeout_seconds: int = 5,
    generated_code_max_memory_mb: int = 128,
    generated_code_sandbox_mode: str = "subprocess",
    generated_code_docker_image: str | None = None,
    generated_code_source_mode: str = "deterministic",
    generated_code_strategy: str = "lexical_diagnostics",
    generated_code_requires_approval: bool | None = None,
    generated_code_approved: bool = False,
    enable_generated_code_revision_loop: bool = False,
    generated_code_revision_rounds: int = 1,
    enable_experiment_tree_search: bool = False,
    experiment_tree_max_depth: int = 1,
    experiment_tree_branching_factor: int = 2,
    progress_callback: Callable[[str, float | None], None] | None = None,
) -> dict[str, Any]:
    project, project_dir = _project_context(project_id)
    ensure_auto_scientist_dirs(project_dir)
    run_id = _new_run_id()
    started_at = utc_now()

    def checkpoint(step: str, progress: float | None = None) -> None:
        if progress_callback is not None:
            progress_callback(step, progress)

    checkpoint("auto scientist: generating ideas", 0.10)
    ideas = generate_scientist_ideas(
        project_dir,
        project_id,
        project_name=project.name,
        domain=project.domain,
        topic=topic,
        research_question=research_question,
        max_ideas=max_ideas,
    )
    checkpoint("auto scientist: building experiment plan", 0.20)
    plan = build_experiment_plan(
        project_dir,
        project_id,
        ideas,
        max_experiments_per_idea=max_experiments_per_idea,
        retrieval_mode=retrieval_mode,
        allow_generated_code_experiments=allow_generated_code_experiments,
        generated_code_timeout_seconds=generated_code_timeout_seconds,
        generated_code_max_memory_mb=generated_code_max_memory_mb,
        generated_code_sandbox_mode=generated_code_sandbox_mode,
        generated_code_docker_image=generated_code_docker_image,
        generated_code_source_mode=generated_code_source_mode,
        generated_code_strategy=generated_code_strategy,
        generated_code_requires_approval=generated_code_requires_approval,
        generated_code_approved=generated_code_approved,
    )
    checkpoint("auto scientist: running experiment plan", 0.30)
    results = run_experiment_plan(project_dir, project_id, plan, run_id=run_id, progress_callback=checkpoint)
    experiment_tree: dict[str, Any] = {}
    all_results = list(results)
    if enable_experiment_tree_search:
        checkpoint("auto scientist: running experiment tree search", 0.55)
        experiment_tree = run_experiment_tree_search(
            project_dir,
            project_id,
            plan,
            run_id,
            results,
            max_depth=experiment_tree_max_depth,
            branching_factor=experiment_tree_branching_factor,
            allow_generated_code_experiments=allow_generated_code_experiments,
            generated_code_sandbox_mode=generated_code_sandbox_mode,
            generated_code_timeout_seconds=generated_code_timeout_seconds,
            generated_code_max_memory_mb=generated_code_max_memory_mb,
            generated_code_docker_image=generated_code_docker_image,
            generated_code_strategy=generated_code_strategy,
        )
        tree_results = experiment_tree.get("tree_experiment_results")
        if isinstance(tree_results, list):
            all_results.extend(item for item in tree_results if isinstance(item, dict))
    revision_summary: dict[str, Any] = {}
    if enable_generated_code_revision_loop and allow_generated_code_experiments:
        checkpoint("auto scientist: reviewing generated-code failures", 0.62)
        revision_summary = run_generated_code_revision_loop(
            project_dir,
            project_id,
            run_id,
            all_results,
            max_rounds=generated_code_revision_rounds,
            generated_code_timeout_seconds=generated_code_timeout_seconds,
            generated_code_max_memory_mb=generated_code_max_memory_mb,
            generated_code_sandbox_mode=generated_code_sandbox_mode,
            generated_code_docker_image=generated_code_docker_image,
            generated_code_strategy=generated_code_strategy,
        )
        revision_results = revision_summary.get("revision_results")
        if isinstance(revision_results, list):
            all_results.extend(item for item in revision_results if isinstance(item, dict))
    checkpoint("auto scientist: analyzing experiment results", 0.70)
    analysis = analyze_experiment_results(project_dir, project_id, run_id, ideas, plan, all_results)
    paper_outputs: dict[str, Any] = {}
    if write_paper:
        checkpoint("auto scientist: planning manuscript", 0.76)
        paper_plan = generate_paper_plan(
            project_dir,
            project_id,
            project_name=project.name,
            domain=project.domain,
            paper_type=paper_type,  # type: ignore[arg-type]
            topic=ideas.get("topic") or topic,
            research_question=ideas.get("research_question") or research_question,
            retrieval_mode=retrieval_mode,
        )
        checkpoint("auto scientist: generating manuscript outline", 0.80)
        outline = generate_paper_outline(
            project_dir,
            project_id,
            project_name=project.name,
            domain=project.domain,
            retrieval_mode=retrieval_mode,
        )
        checkpoint("auto scientist: writing manuscript draft", 0.84)
        draft = generate_full_draft(
            project_dir,
            project_id,
            project_name=project.name,
            domain=project.domain,
            retrieval_mode=retrieval_mode,
            run_claim_audit_after=True,
        )
        paper_outputs = {
            "paper_plan_file": paper_plan.get("paper_plan_file"),
            "outline_file": outline.get("outline_file"),
            "draft_file": draft.get("draft_file"),
            "writing_audit_file": draft.get("writing_audit_file"),
            "claim_audit_file": (draft.get("claim_audit") or {}).get("claim_audit_file") if isinstance(draft.get("claim_audit"), dict) else None,
        }
        if export_latex:
            checkpoint("auto scientist: exporting LaTeX", 0.88)
            latex = export_draft_latex(project_dir, project_id)
            paper_outputs["latex_file"] = latex.get("latex_file")
    autonomous_paper_outputs: dict[str, Any] = {}
    experiment_claim_bindings: dict[str, Any] = {}
    paper_citation_bindings: dict[str, Any] = {}
    paper_compile: dict[str, Any] = {}
    if write_paper:
        checkpoint("auto scientist: assembling autonomous paper", 0.91)
        autonomous_paper_outputs = generate_auto_scientist_paper(
            project_dir,
            project_id,
            run_id,
            ideas,
            plan,
            all_results,
            analysis,
            paper_outputs=paper_outputs,
            experiment_tree=experiment_tree,
        )
        checkpoint("auto scientist: binding manuscript claims to experiment results", 0.925)
        try:
            experiment_claim_bindings = generate_experiment_claim_bindings(
                project_dir,
                project_id,
                manuscript_relative_path="manuscript/auto_scientist_paper.md",
            )
        except Exception as exc:
            experiment_claim_bindings = {"error": exc.__class__.__name__, "binding_file": EXPERIMENT_CLAIM_BINDINGS_JSON}
        checkpoint("auto scientist: binding manuscript claims to source passages and references", 0.932)
        try:
            paper_citation_bindings = generate_paper_citation_bindings(
                project_dir,
                project_id,
                manuscript_relative_path="manuscript/auto_scientist_paper.md",
            )
        except Exception as exc:
            paper_citation_bindings = {"error": exc.__class__.__name__, "binding_file": PAPER_CITATION_BINDINGS_JSON}
        if export_latex:
            checkpoint("auto scientist: running paper compile pipeline", 0.936)
            try:
                paper_compile = compile_auto_scientist_paper(
                    project_dir,
                    project_id,
                    manuscript_tex_relative_path="manuscript/auto_scientist_paper.tex",
                    engine="auto",
                    generate_preview_pdf=True,
                )
            except Exception as exc:
                paper_compile = {"error": exc.__class__.__name__, "relative_path": LATEX_COMPILE_REPORT_JSON}
        else:
            paper_compile = {}
    checkpoint("auto scientist: running simulated reviewer", 0.94)
    review = run_scientist_reviewer(project_dir, project_id, run_id, analysis)
    checkpoint("auto scientist: writing final artifacts", 0.97)
    completed_at = utc_now()
    latest = {
        "schema_version": f"{SCHEMA_PREFIX}.run.v1",
        "project_id": project_id,
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": "completed",
        "mode": "safe_local_auto_scientist_mvp",
        "arbitrary_code_execution": False,
        "safe_experiment_templates_only": not allow_generated_code_experiments,
        "generated_code_experiments_enabled": allow_generated_code_experiments,
        "sandboxed_generated_code": allow_generated_code_experiments,
        "generated_code_sandbox_mode": generated_code_sandbox_mode if allow_generated_code_experiments else None,
        "generated_code_docker_image": generated_code_docker_image if allow_generated_code_experiments and generated_code_sandbox_mode == "docker" else None,
        "generated_code_source_mode": generated_code_source_mode if allow_generated_code_experiments else None,
        "generated_code_strategy": generated_code_strategy if allow_generated_code_experiments else None,
        "generated_code_requires_approval": generated_code_requires_approval if allow_generated_code_experiments else None,
        "generated_code_revision_loop_enabled": enable_generated_code_revision_loop and allow_generated_code_experiments,
        "generated_code_revision_rounds_file": "auto_scientist/code_revision_rounds.jsonl" if revision_summary else None,
        "generated_code_revision_count": revision_summary.get("revision_count", 0) if revision_summary else 0,
        "experiment_tree_search_enabled": enable_experiment_tree_search,
        "experiment_tree_file": EXPERIMENT_TREE_JSON if experiment_tree else None,
        "experiment_tree_best_node": (experiment_tree.get("best_node") if isinstance(experiment_tree, dict) else None),
        "ideas_file": IDEAS_JSON,
        "experiment_plan_file": "auto_scientist/experiment_plan.json",
        "runs_file": RUNS_JSONL,
        "analysis_file": ANALYSIS_JSON,
        "report_file": REPORT_MD,
        "review_file": REVIEW_JSON,
        "review_markdown_file": REVIEW_MD,
        "paper_outputs": paper_outputs,
        "autonomous_paper_outputs": autonomous_paper_outputs,
        "experiment_claim_bindings_file": EXPERIMENT_CLAIM_BINDINGS_JSON if experiment_claim_bindings and not experiment_claim_bindings.get("error") else None,
        "experiment_claim_bindings_summary": experiment_claim_bindings.get("summary") if isinstance(experiment_claim_bindings, dict) else None,
        "experiment_claim_bindings_error": experiment_claim_bindings.get("error") if isinstance(experiment_claim_bindings, dict) else None,
        "paper_citation_bindings_file": PAPER_CITATION_BINDINGS_JSON if paper_citation_bindings and not paper_citation_bindings.get("error") else None,
        "paper_citation_bindings_summary": paper_citation_bindings.get("summary") if isinstance(paper_citation_bindings, dict) else None,
        "paper_citation_bindings_error": paper_citation_bindings.get("error") if isinstance(paper_citation_bindings, dict) else None,
        "paper_compile_report_file": LATEX_COMPILE_REPORT_JSON if paper_compile and not paper_compile.get("error") else None,
        "paper_compile_status": paper_compile.get("compile_status") if isinstance(paper_compile, dict) else None,
        "paper_compile_error": paper_compile.get("error") if isinstance(paper_compile, dict) else None,
        "autonomous_paper_file": autonomous_paper_outputs.get("paper_file") if autonomous_paper_outputs else None,
        "autonomous_paper_latex_file": autonomous_paper_outputs.get("latex_file") if autonomous_paper_outputs else None,
        "experiment_count": len(all_results),
        "review_decision": review.get("overall_decision"),
        "limitations": SAFETY_LIMITATIONS,
    }
    write_project_json(project_dir, LATEST_RUN_JSON, latest)
    append_audit_event(
        project_dir,
        project_id,
        "run_auto_scientist",
        "Safe local Auto Scientist loop completed.",
        {
            "run_id": run_id,
            "experiment_count": len(all_results),
            "write_paper": write_paper,
            "arbitrary_code_execution": False,
            "generated_code_experiments_enabled": allow_generated_code_experiments,
            "generated_code_sandbox_mode": generated_code_sandbox_mode if allow_generated_code_experiments else None,
            "experiment_tree_search_enabled": enable_experiment_tree_search,
            "generated_code_revision_loop_enabled": enable_generated_code_revision_loop and allow_generated_code_experiments,
            "review_decision": review.get("overall_decision"),
        },
        source="api",
        event_category="agent",
        risk_level="medium",
        entity_type="auto_scientist",
        entity_id=run_id,
    )
    return {"run": latest, "ideas": ideas, "experiment_plan": plan, "experiment_results": all_results, "experiment_tree": experiment_tree, "generated_code_revision": revision_summary, "analysis": analysis, "review": review, "autonomous_paper_outputs": autonomous_paper_outputs, "experiment_claim_bindings": experiment_claim_bindings, "paper_citation_bindings": paper_citation_bindings, "paper_compile": paper_compile}
