from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.auto_scientist.contracts import (
    EXPERIMENT_TREE_FAILURES_JSONL,
    EXPERIMENT_TREE_JSON,
    EXPERIMENT_TREE_MD,
    SCHEMA_PREFIX,
    append_jsonl,
    safe_id,
    utc_now,
    write_project_json,
    write_project_text,
)
from app.tools.auto_scientist.experiment_registry import registered_experiment_templates
from app.tools.auto_scientist.experiment_runner import run_experiment_plan
from app.tools.auto_scientist.generated_code_sandbox import GENERATED_CODE_TEMPLATE

SUPPORT_SCORES = {
    "supported": 1.0,
    "weakly_supported": 0.45,
    "partial": 0.35,
    "needs_human_review": 0.2,
    "unsupported": 0.0,
}


def _numeric_metric_score(metrics: Any) -> float:
    if not isinstance(metrics, dict):
        return 0.0
    values: list[float] = []
    for key in [
        "top_source_score",
        "question_evidence_overlap_ratio",
        "support_status_accuracy",
        "unsupported_refusal_rate",
        "answer_has_source_passage_rate",
    ]:
        value = metrics.get(key)
        if isinstance(value, (int, float)):
            values.append(float(value))
    # Nested totals/profiles should not dominate; this is a selection heuristic.
    totals = metrics.get("totals")
    if isinstance(totals, dict):
        for key in ["profiled_file_count", "total_rows_profiled"]:
            value = totals.get(key)
            if isinstance(value, (int, float)) and value > 0:
                values.append(min(float(value) / 10.0, 1.0))
    return round(sum(values) / max(len(values), 1), 4) if values else 0.0


def _claim_support_score(claims: Any) -> float:
    if not isinstance(claims, list) or not claims:
        return 0.0
    claim_scores: list[float] = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        claim_scores.append(SUPPORT_SCORES.get(str(claim.get("support_status") or "needs_human_review"), 0.2))
    return round(sum(claim_scores) / max(len(claim_scores), 1), 4) if claim_scores else 0.0


def score_experiment_breakdown(record: dict[str, Any]) -> dict[str, Any]:
    """Expose the local selection heuristic as auditable components."""
    status = str(record.get("status") or "")
    if status == "completed":
        status_component = 1.0
    elif status in {"skipped", "weakly_supported"}:
        status_component = 0.2
    else:
        status_component = -0.4

    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    metrics = result.get("metrics") if isinstance(result, dict) else {}
    metric_component = _numeric_metric_score(metrics)
    claims = result.get("claims") if isinstance(result, dict) and isinstance(result.get("claims"), list) else []
    claim_support_component = _claim_support_score(claims)

    sandbox_component = 0.0
    if record.get("generated_code_execution") is True:
        sandbox = result.get("sandbox") if isinstance(result, dict) else {}
        if isinstance(sandbox, dict) and sandbox.get("enabled") is True:
            sandbox_component = 0.15
        elif isinstance(sandbox, dict) and sandbox.get("docker_available") is False:
            sandbox_component = -0.1

    total = round(status_component + metric_component + claim_support_component + sandbox_component, 4)
    return {
        "status_component": status_component,
        "metric_component": metric_component,
        "claim_support_component": claim_support_component,
        "sandbox_component": sandbox_component,
        "total": total,
        "heuristic_note": "Local product heuristic for workflow ordering only; not scientific quality, proof, or peer review.",
    }


def score_experiment_result(record: dict[str, Any]) -> float:
    """Rank local experiment candidates for deterministic tree search.

    This is a conservative product heuristic, not a scientific measure. It is
    used only to choose which safe local experiment to refine next.
    """
    return float(score_experiment_breakdown(record)["total"])


def _artifact_kind(relative_path: str) -> str:
    if relative_path.endswith("experiment_result.json"):
        return "experiment_result"
    if relative_path.endswith("metrics.json"):
        return "metrics"
    if relative_path.endswith("summary.md"):
        return "summary"
    if relative_path.endswith(".svg"):
        return "figure"
    if relative_path.endswith(".py"):
        return "generated_source"
    if relative_path.endswith(".log"):
        return "log"
    return "artifact"


def _artifact_refs(record: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for relative_path in record.get("output_files", []):
        if not isinstance(relative_path, str) or not relative_path:
            continue
        refs.append({"relative_path": relative_path, "artifact_kind": _artifact_kind(relative_path)})
    return refs


def _failure_reason_from_result(record: dict[str, Any]) -> str:
    status = str(record.get("status") or "unknown")
    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    error = record.get("error") or (result.get("error") if isinstance(result, dict) else None)
    if status in {"completed", "skipped", "weakly_supported"} and not error:
        return ""
    parts = [f"status={status}"]
    if error:
        parts.append(f"error={error}")
    summary = result.get("summary_markdown") if isinstance(result, dict) else None
    if isinstance(summary, str) and summary.strip():
        parts.append(summary.strip().splitlines()[0][:160])
    return "; ".join(parts)


TREE_SELECTION_TIE_BREAKER_FIELDS = [
    "score desc",
    "status rank desc",
    "non-failure desc",
    "depth asc",
    "non-generated-code desc",
    "template_name asc",
    "node_id asc",
]


def _status_rank(status: Any) -> int:
    return {"completed": 3, "weakly_supported": 2, "skipped": 2, "needs_human_review": 1}.get(str(status or ""), 0)


def _ranked_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [node for node in nodes if isinstance(node, dict)],
        key=lambda node: (
            -float(node.get("score") or 0.0),
            -_status_rank(node.get("status")),
            0 if not node.get("failure_reason") else 1,
            int(node.get("depth") or 0),
            1 if node.get("generated_code_execution") else 0,
            str(node.get("template_name") or ""),
            str(node.get("node_id") or ""),
        ),
    )


def select_best_node(nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    ranked = _ranked_nodes(nodes)
    return ranked[0] if ranked else None


def refresh_tree_selection_metadata(tree: dict[str, Any]) -> None:
    nodes = tree.get("nodes") if isinstance(tree.get("nodes"), list) else []
    ranked = _ranked_nodes(nodes)
    selected = ranked[0] if ranked else None
    selected_id = str(selected.get("node_id")) if isinstance(selected, dict) else ""
    for rank, node in enumerate(ranked, start=1):
        node["selection_rank"] = rank
        node["selection_rationale"] = (
            f"Rank {rank} by deterministic tie-breaker: score={node.get('score')}, "
            f"status={node.get('status')}, failure_reason={'none' if not node.get('failure_reason') else node.get('failure_reason')}, "
            f"depth={node.get('depth')}, generated_code_execution={bool(node.get('generated_code_execution'))}, "
            f"template={node.get('template_name')}, node_id={node.get('node_id')}. "
            "This is a local product heuristic, not scientific quality scoring."
        )
        if node.get("node_id") == selected_id:
            node["selection_rationale"] = "Selected best node. " + node["selection_rationale"]
    tree["best_node"] = selected
    tree["best_node_selection"] = {
        "strategy": "deterministic_score_status_failure_depth_template_node_id",
        "tie_breaker_fields": TREE_SELECTION_TIE_BREAKER_FIELDS,
        "ranked_node_ids": [str(node.get("node_id")) for node in ranked],
        "selected_node_id": selected_id or None,
        "candidate_summary_markdown_file": EXPERIMENT_TREE_MD,
        "rationale": (
            "Best-node selection sorts by explicit deterministic fields and remains a local workflow heuristic; "
            "it is not scientific proof, peer review, citation verification, or publication readiness."
        ),
    }


def _failure_record(project_id: str, run_id: str, node: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": f"{SCHEMA_PREFIX}.experiment_tree_failure.v1",
        "project_id": project_id,
        "run_id": run_id,
        "created_at": utc_now(),
        "node_id": node.get("node_id"),
        "parent_node_id": node.get("parent_node_id"),
        "experiment_id": node.get("experiment_id"),
        "template_name": node.get("template_name"),
        "status": node.get("status"),
        "failure_reason": node.get("failure_reason"),
        "score": node.get("score"),
        "score_breakdown": node.get("score_breakdown"),
        "artifact_refs": node.get("artifact_refs", []),
        "limitations": [
            "Failure isolation marks this node only; sibling nodes and tree metadata remain reviewable.",
            "Failure records are local engineering diagnostics, not scientific evidence.",
        ],
    }


def render_experiment_tree_markdown(tree: dict[str, Any]) -> str:
    best_node = tree.get("selected_best_node") or tree.get("best_node") or {}
    selection = tree.get("best_node_selection") if isinstance(tree.get("best_node_selection"), dict) else {}
    lines = [
        "# Auto Scientist Experiment Tree",
        "",
        "This tree search expands safe local experiment candidates. Scores are heuristic and not scientific proof.",
        "",
        f"- Run ID: `{tree.get('run_id', 'unknown')}`",
        f"- Nodes: {len(tree.get('nodes', []) if isinstance(tree.get('nodes'), list) else [])}",
        f"- Edges: {len(tree.get('edges', []) if isinstance(tree.get('edges'), list) else [])}",
        f"- Best node: `{best_node.get('node_id', 'none') if isinstance(best_node, dict) else 'none'}`",
        f"- Failure log: `{tree.get('failure_log_file') or EXPERIMENT_TREE_FAILURES_JSONL}`",
        "",
        "## Best Node Candidate Summary",
        "",
        f"- Strategy: {selection.get('strategy') or 'deterministic_score_status_failure_depth_template_node_id'}",
        f"- Tie breaker: {', '.join(selection.get('tie_breaker_fields', TREE_SELECTION_TIE_BREAKER_FIELDS))}",
        f"- Rationale: {selection.get('rationale') or 'Local heuristic ranking only.'}",
    ]
    if tree.get("selected_best_node_id"):
        lines.extend(
            [
                f"- Human-selected best node: `{tree.get('selected_best_node_id')}`",
                f"- Selection reason: {tree.get('selected_reason') or 'not provided'}",
            ]
        )
    lines.extend(["", "## Nodes", ""])
    for node in _ranked_nodes(tree.get("nodes", []) if isinstance(tree.get("nodes"), list) else []):
        failure = node.get("failure_reason") or "none"
        breakdown = node.get("score_breakdown") if isinstance(node.get("score_breakdown"), dict) else {}
        lines.append(
            f"- `{node.get('node_id')}` rank={node.get('selection_rank')} depth={node.get('depth')} "
            f"template={node.get('template_name')} status={node.get('status')} score={node.get('score')} "
            f"breakdown(status={breakdown.get('status_component')}, metrics={breakdown.get('metric_component')}, "
            f"claims={breakdown.get('claim_support_component')}, sandbox={breakdown.get('sandbox_component')}) "
            f"failure={failure}; rationale={node.get('selection_rationale')}"
        )
    return "\n".join(str(line) for line in lines) + "\n"


def _node_from_result(result: dict[str, Any], depth: int, parent_node_id: str | None) -> dict[str, Any]:
    experiment_id = str(result.get("experiment_id") or f"experiment_{depth}")
    node_id = f"node_d{depth}_{safe_id(experiment_id)}"
    result_payload = result.get("result") if isinstance(result.get("result"), dict) else {}
    claims = result_payload.get("claims") if isinstance(result_payload, dict) and isinstance(result_payload.get("claims"), list) else []
    metrics = result_payload.get("metrics") if isinstance(result_payload, dict) and isinstance(result_payload.get("metrics"), dict) else {}
    score_breakdown = score_experiment_breakdown(result)
    return {
        "node_id": node_id,
        "parent_node_id": parent_node_id,
        "depth": depth,
        "experiment_id": experiment_id,
        "template_name": result.get("template_name"),
        "status": result.get("status"),
        "score": score_breakdown["total"],
        "score_breakdown": score_breakdown,
        "failure_reason": _failure_reason_from_result(result),
        "selection_rationale": "Pending deterministic best-node comparison.",
        "artifact_refs": _artifact_refs(result),
        "generated_code_execution": bool(result.get("generated_code_execution")),
        "output_files": result.get("output_files", []),
        "metric_keys": sorted(metrics.keys()) if isinstance(metrics, dict) else [],
        "claim_count": len(claims),
        "support_status_counts": {
            status: sum(1 for claim in claims if isinstance(claim, dict) and str(claim.get("support_status") or "needs_human_review") == status)
            for status in sorted({str(claim.get("support_status") or "needs_human_review") for claim in claims if isinstance(claim, dict)})
        },
        "source_hash": result.get("source_hash"),
        "approval_required": result.get("approval_required"),
    }


def _unique_templates(templates: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in templates:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _child_experiments(
    parent_node: dict[str, Any],
    base_plan: dict[str, Any],
    depth: int,
    branching_factor: int,
    allow_generated_code_experiments: bool,
    generated_code_sandbox_mode: str,
    generated_code_timeout_seconds: int,
    generated_code_max_memory_mb: int,
    generated_code_docker_image: str | None,
    generated_code_strategy: str = "lexical_diagnostics",
) -> list[dict[str, Any]]:
    available = set(registered_experiment_templates(include_generated_code=allow_generated_code_experiments))
    preferred = _unique_templates(
        [
            str(parent_node.get("template_name") or ""),
            "rag_retrieval_eval",
            "claim_audit_eval",
            "evidence_inventory",
            GENERATED_CODE_TEMPLATE if allow_generated_code_experiments else "",
            "writing_safety_eval",
        ]
    )
    topic = base_plan.get("topic")
    research_question = base_plan.get("research_question")
    # Existing plans store topic/RQ under per-experiment config; recover from first experiment if needed.
    for item in base_plan.get("experiments", []):
        if not isinstance(item, dict):
            continue
        cfg = item.get("config") if isinstance(item.get("config"), dict) else {}
        topic = topic or cfg.get("topic")
        research_question = research_question or cfg.get("research_question")
        if topic or research_question:
            break
    experiments: list[dict[str, Any]] = []
    for index, template_name in enumerate([item for item in preferred if item in available][: max(1, branching_factor)], start=1):
        experiment_id = f"tree_d{depth}_{index:02d}_{safe_id(template_name)}"
        config = {
            "topic": topic,
            "research_question": research_question,
            "retrieval_mode": base_plan.get("retrieval_mode") or "local_hybrid_fts",
            "parent_experiment_id": parent_node.get("experiment_id"),
            "parent_node_id": parent_node.get("node_id"),
            "tree_depth": depth,
            "tree_candidate_index": index,
        }
        if template_name == GENERATED_CODE_TEMPLATE:
            config.update(
                {
                    "generated_code_timeout_seconds": generated_code_timeout_seconds,
                    "generated_code_max_memory_mb": generated_code_max_memory_mb,
                    "generated_code_sandbox_mode": generated_code_sandbox_mode,
                    "generated_code_strategy": generated_code_strategy,
                }
            )
            if generated_code_docker_image:
                config["generated_code_docker_image"] = generated_code_docker_image
        experiments.append(
            {
                "experiment_id": experiment_id,
                "idea_id": parent_node.get("experiment_id") or "tree_parent",
                "template_name": template_name,
                "status": "planned",
                "safe_execution": True,
                "generated_code_execution": template_name == GENERATED_CODE_TEMPLATE,
                "arbitrary_code_execution": False,
                "tree_search_candidate": True,
                "parent_node_id": parent_node.get("node_id"),
                "config": config,
            }
        )
    return experiments


def _isolated_failure_result(
    project_id: str,
    run_id: str,
    experiment: dict[str, Any],
    exc: Exception,
) -> dict[str, Any]:
    experiment_id = str(experiment.get("experiment_id") or "tree_child")
    template_name = str(experiment.get("template_name") or "")
    result_payload = {
        "schema_version": f"{SCHEMA_PREFIX}.experiment_result.v1",
        "project_id": project_id,
        "run_id": run_id,
        "experiment_id": experiment_id,
        "idea_id": experiment.get("idea_id"),
        "template_name": template_name,
        "created_at": utc_now(),
        "safe_execution": True,
        "generated_code_execution": template_name == GENERATED_CODE_TEMPLATE,
        "arbitrary_code_execution": False,
        "status": "failed",
        "error": exc.__class__.__name__,
        "metrics": {},
        "claims": [],
        "summary_markdown": f"# Isolated tree child failure\n\n{exc.__class__.__name__}: {exc}\n",
        "limitations": [
            "This child failure was isolated so sibling tree nodes remain reviewable.",
            "Failure status is an engineering diagnostic, not scientific evidence.",
        ],
    }
    return {
        "created_at": utc_now(),
        "run_id": run_id,
        "experiment_id": experiment_id,
        "template_name": template_name,
        "status": "failed",
        "error": exc.__class__.__name__,
        "safe_execution": True,
        "generated_code_execution": template_name == GENERATED_CODE_TEMPLATE,
        "arbitrary_code_execution": False,
        "output_files": [],
        "metric_keys": [],
        "tree_failure_isolated": True,
        "result": result_payload,
    }


def run_experiment_tree_search(
    project_dir: Path,
    project_id: str,
    base_plan: dict[str, Any],
    run_id: str,
    initial_results: list[dict[str, Any]],
    max_depth: int = 1,
    branching_factor: int = 2,
    allow_generated_code_experiments: bool = False,
    generated_code_sandbox_mode: str = "subprocess",
    generated_code_timeout_seconds: int = 5,
    generated_code_max_memory_mb: int = 512,
    generated_code_docker_image: str | None = None,
    generated_code_strategy: str = "lexical_diagnostics",
) -> dict[str, Any]:
    max_depth = max(0, min(int(max_depth), 3))
    branching_factor = max(1, min(int(branching_factor), 4))
    nodes = [_node_from_result(item, 0, None) for item in initial_results]
    edges: list[dict[str, str]] = []
    tree_results: list[dict[str, Any]] = []
    failure_records: list[dict[str, Any]] = []
    current_frontier = nodes[:]
    for node in nodes:
        if node.get("failure_reason"):
            failure_records.append(_failure_record(project_id, run_id, node))

    for depth in range(1, max_depth + 1):
        if not current_frontier:
            break
        parent = select_best_node(current_frontier)
        if not parent:
            break
        experiments = _child_experiments(
            parent,
            base_plan,
            depth,
            branching_factor,
            allow_generated_code_experiments,
            generated_code_sandbox_mode,
            generated_code_timeout_seconds,
            generated_code_max_memory_mb,
            generated_code_docker_image,
            generated_code_strategy,
        )
        if not experiments:
            break
        child_plan = {
            "schema_version": f"{SCHEMA_PREFIX}.experiment_tree_child_plan.v1",
            "project_id": project_id,
            "created_at": utc_now(),
            "run_id": run_id,
            "tree_depth": depth,
            "parent_node_id": parent.get("node_id"),
            "safe_runner": True,
            "arbitrary_code_execution": False,
            "experiments": experiments,
        }
        try:
            child_results = run_experiment_plan(project_dir, project_id, child_plan, run_id=run_id)
        except Exception as exc:
            child_results = [_isolated_failure_result(project_id, run_id, experiment, exc) for experiment in experiments]
        tree_results.extend(child_results)
        current_frontier = []
        for result in child_results:
            node = _node_from_result(result, depth, str(parent.get("node_id")))
            nodes.append(node)
            current_frontier.append(node)
            edges.append({"from": str(parent.get("node_id")), "to": node["node_id"]})
            if node.get("failure_reason"):
                failure_records.append(_failure_record(project_id, run_id, node))

    payload = {
        "schema_version": f"{SCHEMA_PREFIX}.experiment_tree.v1",
        "project_id": project_id,
        "run_id": run_id,
        "created_at": utc_now(),
        "experiment_tree_file": EXPERIMENT_TREE_JSON,
        "tree_search_enabled": True,
        "strategy": "deterministic_best_score_expansion",
        "max_depth": max_depth,
        "branching_factor": branching_factor,
        "generated_code_strategy": generated_code_strategy if allow_generated_code_experiments else None,
        "topic": base_plan.get("topic"),
        "research_question": base_plan.get("research_question"),
        "retrieval_mode": base_plan.get("retrieval_mode") or "local_hybrid_fts",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "child_experiment_count": len(tree_results),
        "failure_log_file": EXPERIMENT_TREE_FAILURES_JSONL,
        "failure_count": len(failure_records),
        "tree_experiment_results": tree_results,
        "limitations": [
            "Tree search score is a local product heuristic, not scientific validity.",
            "Only registered safe templates or explicitly sandboxed generated-code experiments are expanded.",
            "Failed child nodes are isolated as reviewable nodes; sibling results remain available.",
            "Human review is required before using any result externally.",
        ],
    }
    refresh_tree_selection_metadata(payload)
    best_node = payload.get("best_node") if isinstance(payload.get("best_node"), dict) else None
    write_project_json(project_dir, EXPERIMENT_TREE_JSON, payload)
    write_project_text(project_dir, EXPERIMENT_TREE_MD, render_experiment_tree_markdown(payload))
    if failure_records:
        for record in failure_records:
            append_jsonl(project_dir, EXPERIMENT_TREE_FAILURES_JSONL, record)
    else:
        write_project_text(project_dir, EXPERIMENT_TREE_FAILURES_JSONL, "")
    append_audit_event(
        project_dir,
        project_id,
        "run_auto_scientist_experiment_tree_search",
        "Auto Scientist deterministic experiment tree search completed.",
        {
            "run_id": run_id,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "best_node": (best_node or {}).get("node_id"),
            "child_experiment_count": len(tree_results),
            "failure_count": len(failure_records),
        },
        source="api",
        event_category="agent",
        risk_level="medium",
        entity_type="auto_scientist",
        entity_id=run_id,
    )
    return payload
