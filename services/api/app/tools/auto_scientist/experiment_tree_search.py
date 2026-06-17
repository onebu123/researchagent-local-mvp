from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.auto_scientist.contracts import (
    EXPERIMENT_TREE_JSON,
    EXPERIMENT_TREE_MD,
    SCHEMA_PREFIX,
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


def score_experiment_result(record: dict[str, Any]) -> float:
    """Rank local experiment candidates for deterministic tree search.

    This is a conservative product heuristic, not a scientific measure. It is
    used only to choose which safe local experiment to refine next.
    """
    score = 0.0
    status = str(record.get("status") or "")
    if status == "completed":
        score += 1.0
    elif status in {"skipped", "weakly_supported"}:
        score += 0.2
    else:
        score -= 0.4

    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    metrics = result.get("metrics") if isinstance(result, dict) else {}
    score += _numeric_metric_score(metrics)
    claims = result.get("claims") if isinstance(result, dict) and isinstance(result.get("claims"), list) else []
    if claims:
        claim_scores = []
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            claim_scores.append(SUPPORT_SCORES.get(str(claim.get("support_status") or "needs_human_review"), 0.2))
        score += sum(claim_scores) / max(len(claim_scores), 1)
    if record.get("generated_code_execution") is True:
        sandbox = result.get("sandbox") if isinstance(result, dict) else {}
        if isinstance(sandbox, dict) and sandbox.get("enabled") is True:
            score += 0.15
        elif isinstance(sandbox, dict) and sandbox.get("docker_available") is False:
            score -= 0.1
    return round(score, 4)


def _node_from_result(result: dict[str, Any], depth: int, parent_node_id: str | None) -> dict[str, Any]:
    experiment_id = str(result.get("experiment_id") or f"experiment_{depth}")
    node_id = f"node_d{depth}_{safe_id(experiment_id)}"
    result_payload = result.get("result") if isinstance(result.get("result"), dict) else {}
    claims = result_payload.get("claims") if isinstance(result_payload, dict) and isinstance(result_payload.get("claims"), list) else []
    metrics = result_payload.get("metrics") if isinstance(result_payload, dict) and isinstance(result_payload.get("metrics"), dict) else {}
    return {
        "node_id": node_id,
        "parent_node_id": parent_node_id,
        "depth": depth,
        "experiment_id": experiment_id,
        "template_name": result.get("template_name"),
        "status": result.get("status"),
        "score": score_experiment_result(result),
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
    current_frontier = nodes[:]

    for depth in range(1, max_depth + 1):
        if not current_frontier:
            break
        parent = max(current_frontier, key=lambda item: float(item.get("score") or 0.0))
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
        child_results = run_experiment_plan(project_dir, project_id, child_plan, run_id=run_id)
        tree_results.extend(child_results)
        current_frontier = []
        for result in child_results:
            node = _node_from_result(result, depth, str(parent.get("node_id")))
            nodes.append(node)
            current_frontier.append(node)
            edges.append({"from": str(parent.get("node_id")), "to": node["node_id"]})

    best_node = max(nodes, key=lambda item: float(item.get("score") or 0.0)) if nodes else None
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
        "best_node": best_node,
        "nodes": nodes,
        "edges": edges,
        "child_experiment_count": len(tree_results),
        "tree_experiment_results": tree_results,
        "limitations": [
            "Tree search score is a local product heuristic, not scientific validity.",
            "Only registered safe templates or explicitly sandboxed generated-code experiments are expanded.",
            "Human review is required before using any result externally.",
        ],
    }
    write_project_json(project_dir, EXPERIMENT_TREE_JSON, payload)
    lines = [
        "# Auto Scientist Experiment Tree",
        "",
        "This tree search expands safe local experiment candidates. Scores are heuristic and not scientific proof.",
        "",
        f"- Run ID: `{run_id}`",
        f"- Nodes: {len(nodes)}",
        f"- Edges: {len(edges)}",
        f"- Best node: `{(best_node or {}).get('node_id', 'none')}`",
        "",
        "## Nodes",
        "",
    ]
    for node in nodes:
        lines.append(
            f"- `{node['node_id']}` depth={node['depth']} template={node.get('template_name')} "
            f"status={node.get('status')} score={node.get('score')}"
        )
    write_project_text(project_dir, EXPERIMENT_TREE_MD, "\n".join(lines) + "\n")
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
        },
        source="api",
        event_category="agent",
        risk_level="medium",
        entity_type="auto_scientist",
        entity_id=run_id,
    )
    return payload
