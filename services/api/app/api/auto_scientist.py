from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas import (
    AutoScientistExperimentClaimBindingRequest,
    AutoScientistExperimentTreeRerunRequest,
    AutoScientistExperimentTreeSelectRequest,
    AutoScientistGeneratedCodeApprovalRequest,
    AutoScientistGeneratedCodeRerunRequest,
    AutoScientistIdeaRequest,
    AutoScientistPaperRewriteRequest,
    AutoScientistPaperCitationBindingRequest,
    AutoScientistPaperCompileRequest,
    AutoScientistRunRequest,
    AutoScientistTreeRevisionApplyRequest,
    AutoScientistTreeRevisionPlanRequest,
)
from app.services.project_service import ProjectNotFoundError, project_service
from app.services.storage_service import storage_service
from app.tools.auto_scientist.idea_generator import generate_scientist_ideas, read_scientist_ideas
from app.tools.auto_scientist.scientist_loop import read_auto_scientist_status, run_auto_scientist
from app.tools.auto_scientist.contracts import RUNS_JSONL, read_jsonl
from app.tools.auto_scientist.experiment_claim_binding import (
    generate_experiment_claim_bindings,
    read_experiment_claim_bindings,
)
from app.tools.auto_scientist.paper_citation_binding import (
    generate_paper_citation_bindings,
    read_paper_citation_bindings,
)
from app.tools.auto_scientist.paper_compile import (
    compile_auto_scientist_paper,
    read_paper_compile_report,
)
from app.tools.auto_scientist.generated_code_approval import (
    list_generated_code_proposals,
    read_generated_code_approvals,
    record_generated_code_approval,
    rerun_generated_code_proposal,
)
from app.tools.auto_scientist.experiment_tree_ops import (
    list_experiment_tree_nodes,
    read_experiment_tree,
    rerun_experiment_tree_node,
    rewrite_auto_scientist_paper_from_tree,
    select_experiment_tree_node,
)
from app.tools.auto_scientist.tree_revision_loop import (
    apply_tree_revision_patches,
    generate_tree_revision_plan,
    read_tree_revision_plan,
)

router = APIRouter()


def _project(project_id: str):
    try:
        return project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _project_dir(project_id: str):
    _project(project_id)
    return storage_service.project_dir(project_id)


def _handle_tool_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="auto scientist operation failed")


@router.post("/projects/{project_id}/auto-scientist/ideas")
def create_auto_scientist_ideas(
    project_id: str,
    payload: AutoScientistIdeaRequest | None = None,
) -> dict[str, Any]:
    project = _project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    request_payload = payload or AutoScientistIdeaRequest()
    try:
        return generate_scientist_ideas(
            project_dir,
            project_id,
            project_name=project.name,
            domain=project.domain,
            topic=request_payload.topic,
            research_question=request_payload.research_question,
            max_ideas=request_payload.max_ideas,
            reference_literature_ids=request_payload.reference_literature_ids,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/auto-scientist/ideas")
def get_auto_scientist_ideas(project_id: str) -> dict[str, Any]:
    payload = read_scientist_ideas(_project_dir(project_id))
    if not payload:
        raise HTTPException(status_code=404, detail="auto_scientist/ideas.json does not exist")
    return payload


@router.post("/projects/{project_id}/auto-scientist/run")
def create_auto_scientist_run(
    project_id: str,
    payload: AutoScientistRunRequest | None = None,
) -> dict[str, Any]:
    request_payload = payload or AutoScientistRunRequest()
    try:
        return run_auto_scientist(
            project_id,
            topic=request_payload.topic,
            research_question=request_payload.research_question,
            max_ideas=request_payload.max_ideas,
            max_experiments_per_idea=request_payload.max_experiments_per_idea,
            paper_type=request_payload.paper_type,
            retrieval_mode=request_payload.retrieval_mode,
            write_paper=request_payload.write_paper,
            export_latex=request_payload.export_latex,
            allow_generated_code_experiments=request_payload.allow_generated_code_experiments,
            generated_code_timeout_seconds=request_payload.generated_code_timeout_seconds,
            generated_code_max_memory_mb=request_payload.generated_code_max_memory_mb,
            generated_code_sandbox_mode=request_payload.generated_code_sandbox_mode,
            generated_code_docker_image=request_payload.generated_code_docker_image,
            generated_code_source_mode=request_payload.generated_code_source_mode,
            generated_code_strategy=request_payload.generated_code_strategy,
            generated_code_requires_approval=request_payload.generated_code_requires_approval,
            generated_code_approved=request_payload.generated_code_approved,
            enable_generated_code_revision_loop=request_payload.enable_generated_code_revision_loop,
            generated_code_revision_rounds=request_payload.generated_code_revision_rounds,
            enable_experiment_tree_search=request_payload.enable_experiment_tree_search,
            experiment_tree_max_depth=request_payload.experiment_tree_max_depth,
            experiment_tree_branching_factor=request_payload.experiment_tree_branching_factor,
            reference_literature_ids=request_payload.reference_literature_ids,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/auto-scientist/status")
def get_auto_scientist_status(project_id: str) -> dict[str, Any]:
    try:
        return read_auto_scientist_status(project_id)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/auto-scientist/runs")
def get_auto_scientist_runs(project_id: str) -> list[dict[str, Any]]:
    try:
        return read_jsonl(_project_dir(project_id), RUNS_JSONL)
    except Exception as exc:
        raise _handle_tool_error(exc) from exc




@router.get("/projects/{project_id}/auto-scientist/experiment-claim-bindings")
def get_auto_scientist_experiment_claim_bindings(project_id: str) -> dict[str, Any]:
    try:
        project_dir = _project_dir(project_id)
        payload = read_experiment_claim_bindings(project_dir)
        if not payload:
            # Build lazily from existing Auto Scientist manuscripts/results when the
            # read model has not been materialized yet. This keeps the GET endpoint
            # useful after older runs while preserving 404 for projects without the
            # required manuscript artifacts.
            payload = generate_experiment_claim_bindings(project_dir, project_id)
        if not payload:
            raise HTTPException(status_code=404, detail="auto_scientist/experiment_claim_bindings.json does not exist")
        return payload
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/auto-scientist/experiment-claim-bindings")
def create_auto_scientist_experiment_claim_bindings(
    project_id: str,
    payload: AutoScientistExperimentClaimBindingRequest | None = None,
) -> dict[str, Any]:
    request_payload = payload or AutoScientistExperimentClaimBindingRequest()
    try:
        return generate_experiment_claim_bindings(
            _project_dir(project_id),
            project_id,
            manuscript_relative_path=request_payload.manuscript_relative_path,
            node_id=request_payload.node_id,
            reason=request_payload.reason or "",
            top_k=request_payload.top_k,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc



@router.get("/projects/{project_id}/auto-scientist/paper-citation-bindings")
def get_auto_scientist_paper_citation_bindings(project_id: str) -> dict[str, Any]:
    try:
        project_dir = _project_dir(project_id)
        payload = read_paper_citation_bindings(project_dir)
        if not payload:
            payload = generate_paper_citation_bindings(project_dir, project_id)
        if not payload:
            raise HTTPException(status_code=404, detail="manuscript/paper_citation_bindings.json does not exist")
        return payload
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/auto-scientist/paper-citation-bindings")
def create_auto_scientist_paper_citation_bindings(
    project_id: str,
    payload: AutoScientistPaperCitationBindingRequest | None = None,
) -> dict[str, Any]:
    request_payload = payload or AutoScientistPaperCitationBindingRequest()
    try:
        return generate_paper_citation_bindings(
            _project_dir(project_id),
            project_id,
            manuscript_relative_path=request_payload.manuscript_relative_path,
            retrieval_mode=request_payload.retrieval_mode,
            top_k=request_payload.top_k,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/auto-scientist/paper-compile")
def get_auto_scientist_paper_compile_report(project_id: str) -> dict[str, Any]:
    try:
        payload = read_paper_compile_report(_project_dir(project_id))
        if not payload:
            raise HTTPException(status_code=404, detail="manuscript/latex_compile_report.json does not exist")
        return payload
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/auto-scientist/paper-compile")
def compile_auto_scientist_paper_endpoint(
    project_id: str,
    payload: AutoScientistPaperCompileRequest | None = None,
) -> dict[str, Any]:
    request_payload = payload or AutoScientistPaperCompileRequest()
    try:
        return compile_auto_scientist_paper(
            _project_dir(project_id),
            project_id,
            manuscript_tex_relative_path=request_payload.manuscript_tex_relative_path,
            engine=request_payload.engine,
            timeout_seconds=request_payload.timeout_seconds,
            generate_preview_pdf=request_payload.generate_preview_pdf,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc



@router.get("/projects/{project_id}/auto-scientist/generated-code/approvals")
def get_auto_scientist_generated_code_approvals(project_id: str) -> list[dict[str, Any]]:
    try:
        return read_generated_code_approvals(_project_dir(project_id))
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/auto-scientist/generated-code/proposals")
def get_auto_scientist_generated_code_proposals(project_id: str) -> list[dict[str, Any]]:
    try:
        return list_generated_code_proposals(_project_dir(project_id))
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/auto-scientist/generated-code/approvals")
def approve_auto_scientist_generated_code(
    project_id: str,
    payload: AutoScientistGeneratedCodeApprovalRequest,
) -> dict[str, Any]:
    try:
        return record_generated_code_approval(
            _project_dir(project_id),
            project_id,
            payload.run_id,
            payload.experiment_id,
            payload.decision,
            payload.reason or "",
            source_hash=payload.source_hash,
            reviewer="api_user",
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/auto-scientist/generated-code/rerun")
def rerun_auto_scientist_generated_code(
    project_id: str,
    payload: AutoScientistGeneratedCodeRerunRequest,
) -> dict[str, Any]:
    try:
        return rerun_generated_code_proposal(
            _project_dir(project_id),
            project_id,
            payload.run_id,
            payload.experiment_id,
            payload.source_hash,
            sandbox_mode=payload.sandbox_mode,
            docker_image=payload.docker_image,
            timeout_seconds=payload.timeout_seconds,
            max_memory_mb=payload.max_memory_mb,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/auto-scientist/experiment-tree")
def get_auto_scientist_experiment_tree(project_id: str) -> dict[str, Any]:
    try:
        payload = read_experiment_tree(_project_dir(project_id))
        if not payload:
            raise HTTPException(status_code=404, detail="auto_scientist/experiment_tree.json does not exist")
        return payload
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/auto-scientist/experiment-tree/nodes")
def get_auto_scientist_experiment_tree_nodes(project_id: str) -> dict[str, Any]:
    try:
        payload = list_experiment_tree_nodes(_project_dir(project_id))
        if not payload.get("nodes"):
            raise HTTPException(status_code=404, detail="auto_scientist/experiment_tree.json has no nodes")
        return payload
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/auto-scientist/experiment-tree/select")
def select_auto_scientist_experiment_tree_node(
    project_id: str,
    payload: AutoScientistExperimentTreeSelectRequest,
) -> dict[str, Any]:
    try:
        return select_experiment_tree_node(
            _project_dir(project_id),
            project_id,
            payload.node_id,
            reason=payload.reason or "",
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/auto-scientist/experiment-tree/rerun-node")
def rerun_auto_scientist_experiment_tree_node(
    project_id: str,
    payload: AutoScientistExperimentTreeRerunRequest,
) -> dict[str, Any]:
    try:
        return rerun_experiment_tree_node(
            _project_dir(project_id),
            project_id,
            payload.node_id,
            sandbox_mode=payload.sandbox_mode,
            docker_image=payload.docker_image,
            timeout_seconds=payload.timeout_seconds,
            max_memory_mb=payload.max_memory_mb,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/auto-scientist/experiment-tree/rewrite-paper")
def rewrite_auto_scientist_paper_from_experiment_tree(
    project_id: str,
    payload: AutoScientistPaperRewriteRequest | None = None,
) -> dict[str, Any]:
    request_payload = payload or AutoScientistPaperRewriteRequest()
    try:
        return rewrite_auto_scientist_paper_from_tree(
            _project_dir(project_id),
            project_id,
            node_id=request_payload.node_id,
            reason=request_payload.reason or "",
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.get("/projects/{project_id}/auto-scientist/experiment-tree/revision-plan")
def get_auto_scientist_tree_revision_plan(project_id: str) -> dict[str, Any]:
    try:
        payload = read_tree_revision_plan(_project_dir(project_id))
        if not payload:
            raise HTTPException(status_code=404, detail="auto_scientist/tree_revision_plan.json does not exist")
        return payload
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/auto-scientist/experiment-tree/revision-plan")
def create_auto_scientist_tree_revision_plan(
    project_id: str,
    payload: AutoScientistTreeRevisionPlanRequest | None = None,
) -> dict[str, Any]:
    request_payload = payload or AutoScientistTreeRevisionPlanRequest()
    try:
        return generate_tree_revision_plan(
            _project_dir(project_id),
            project_id,
            node_id=request_payload.node_id,
            reason=request_payload.reason or "",
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc


@router.post("/projects/{project_id}/auto-scientist/experiment-tree/apply-revision")
def apply_auto_scientist_tree_revision(
    project_id: str,
    payload: AutoScientistTreeRevisionApplyRequest | None = None,
) -> dict[str, Any]:
    request_payload = payload or AutoScientistTreeRevisionApplyRequest()
    try:
        return apply_tree_revision_patches(
            _project_dir(project_id),
            project_id,
            patch_ids=request_payload.patch_ids,
            reason=request_payload.reason or "",
            require_human_approval=request_payload.require_human_approval,
            rerun_claim_audit=request_payload.rerun_claim_audit,
            regenerate_trust_package=request_payload.regenerate_trust_package,
        )
    except Exception as exc:
        raise _handle_tool_error(exc) from exc
