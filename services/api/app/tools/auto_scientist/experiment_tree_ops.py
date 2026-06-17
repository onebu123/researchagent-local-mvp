from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.auto_scientist.contracts import (
    ANALYSIS_JSON,
    EXPERIMENT_PLAN_JSON,
    EXPERIMENT_TREE_FAILURES_JSONL,
    EXPERIMENT_TREE_JSON,
    EXPERIMENT_TREE_MD,
    IDEAS_JSON,
    LATEST_RUN_JSON,
    RUNS_JSONL,
    SCHEMA_PREFIX,
    append_jsonl,
    read_json,
    read_jsonl,
    safe_id,
    utc_now,
    write_project_json,
    write_project_text,
)
from app.tools.auto_scientist.experiment_claim_binding import (
    EXPERIMENT_CLAIM_BINDINGS_JSON,
    generate_experiment_claim_bindings,
)
from app.tools.auto_scientist.experiment_runner import run_experiment_plan
from app.tools.auto_scientist.experiment_tree_search import (
    _failure_record,
    _node_from_result,
    refresh_tree_selection_metadata,
    render_experiment_tree_markdown,
)
from app.tools.auto_scientist.generated_code_sandbox import GENERATED_CODE_TEMPLATE
from app.tools.auto_scientist.scientist_paper import generate_auto_scientist_paper

EXPERIMENT_TREE_SELECTION_JSON = "auto_scientist/experiment_tree_selection.json"
EXPERIMENT_TREE_RERUNS_JSONL = "auto_scientist/experiment_tree_reruns.jsonl"
PAPER_REWRITES_JSONL = "auto_scientist/paper_rewrites.jsonl"
LATEST_PAPER_REWRITE_JSON = "auto_scientist/latest_paper_rewrite.json"


def read_experiment_tree(project_dir: Path) -> dict[str, Any]:
    payload = read_json(project_dir / EXPERIMENT_TREE_JSON, {})
    return payload if isinstance(payload, dict) else {}


def list_experiment_tree_nodes(project_dir: Path) -> dict[str, Any]:
    tree = read_experiment_tree(project_dir)
    nodes = tree.get("nodes") if isinstance(tree.get("nodes"), list) else []
    edges = tree.get("edges") if isinstance(tree.get("edges"), list) else []
    return {
        "schema_version": f"{SCHEMA_PREFIX}.experiment_tree_nodes.v1",
        "project_id": tree.get("project_id"),
        "run_id": tree.get("run_id"),
        "experiment_tree_file": EXPERIMENT_TREE_JSON,
        "selection_file": EXPERIMENT_TREE_SELECTION_JSON,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "best_node": tree.get("best_node"),
        "selected_best_node": tree.get("selected_best_node"),
        "selected_best_node_id": tree.get("selected_best_node_id"),
        "nodes": nodes,
        "edges": edges,
        "limitations": [
            "Experiment tree node scores are local workflow heuristics, not scientific validity metrics.",
            "Selecting a best node controls manuscript emphasis but does not verify the result scientifically.",
        ],
    }


def _find_node(tree: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in tree.get("nodes", []):
        if isinstance(node, dict) and node.get("node_id") == node_id:
            return node
    raise ValueError(f"experiment tree node not found: {node_id}")


def _tree_context(tree: dict[str, Any]) -> dict[str, Any]:
    ctx = {
        "topic": tree.get("topic"),
        "research_question": tree.get("research_question"),
        "retrieval_mode": tree.get("retrieval_mode") or "local_hybrid_fts",
    }
    if not ctx["topic"] or not ctx["research_question"]:
        for result in tree.get("tree_experiment_results", []):
            if not isinstance(result, dict):
                continue
            config = result.get("config") if isinstance(result.get("config"), dict) else {}
            ctx["topic"] = ctx["topic"] or config.get("topic")
            ctx["research_question"] = ctx["research_question"] or config.get("research_question")
            if ctx["topic"] and ctx["research_question"]:
                break
    return ctx


def _render_tree_markdown(tree: dict[str, Any]) -> str:
    return render_experiment_tree_markdown(tree)


def _persist_tree(project_dir: Path, tree: dict[str, Any]) -> None:
    nodes = tree.get("nodes") if isinstance(tree.get("nodes"), list) else []
    edges = tree.get("edges") if isinstance(tree.get("edges"), list) else []
    tree["node_count"] = len(nodes)
    tree["edge_count"] = len(edges)
    tree["failure_log_file"] = tree.get("failure_log_file") or EXPERIMENT_TREE_FAILURES_JSONL
    tree["failure_count"] = sum(1 for node in nodes if isinstance(node, dict) and node.get("failure_reason"))
    refresh_tree_selection_metadata(tree)
    tree["updated_at"] = utc_now()
    write_project_json(project_dir, EXPERIMENT_TREE_JSON, tree)
    write_project_text(project_dir, EXPERIMENT_TREE_MD, _render_tree_markdown(tree))


def select_experiment_tree_node(
    project_dir: Path,
    project_id: str,
    node_id: str,
    reason: str = "",
    reviewer: str = "api_user",
) -> dict[str, Any]:
    tree = read_experiment_tree(project_dir)
    if not tree:
        raise FileNotFoundError(EXPERIMENT_TREE_JSON)
    node = _find_node(tree, node_id)
    history_payload = read_json(project_dir / EXPERIMENT_TREE_SELECTION_JSON, {})
    history = history_payload.get("history", []) if isinstance(history_payload, dict) and isinstance(history_payload.get("history"), list) else []
    record = {
        "schema_version": f"{SCHEMA_PREFIX}.experiment_tree_selection.v1",
        "project_id": project_id,
        "run_id": tree.get("run_id"),
        "created_at": utc_now(),
        "node_id": node_id,
        "selected_node": node,
        "reason": reason.strip(),
        "reviewer": reviewer,
        "human_review_required": True,
        "limitations": [
            "Selecting a best node is a local workflow decision and not proof of scientific validity.",
            "The selected node should be reviewed against source artifacts before external use.",
        ],
    }
    history.append(record)
    selection_payload = {
        "schema_version": f"{SCHEMA_PREFIX}.experiment_tree_selection_log.v1",
        "project_id": project_id,
        "experiment_tree_file": EXPERIMENT_TREE_JSON,
        "latest_selection": record,
        "history": history,
    }
    write_project_json(project_dir, EXPERIMENT_TREE_SELECTION_JSON, selection_payload)
    tree["selected_best_node_id"] = node_id
    tree["selected_best_node"] = node
    tree["selected_at"] = record["created_at"]
    tree["selected_reason"] = reason.strip()
    tree["selection_file"] = EXPERIMENT_TREE_SELECTION_JSON
    _persist_tree(project_dir, tree)
    append_audit_event(
        project_dir,
        project_id,
        "select_auto_scientist_experiment_tree_node",
        "A local user selected an Auto Scientist experiment tree node for manuscript emphasis.",
        {"node_id": node_id, "run_id": tree.get("run_id"), "reason": reason.strip()},
        source="api",
        event_category="agent",
        risk_level="medium",
        entity_type="auto_scientist_experiment_tree",
        entity_id=node_id,
    )
    return selection_payload


def rerun_experiment_tree_node(
    project_dir: Path,
    project_id: str,
    node_id: str,
    sandbox_mode: str = "subprocess",
    docker_image: str | None = None,
    timeout_seconds: int = 5,
    max_memory_mb: int = 512,
) -> dict[str, Any]:
    tree = read_experiment_tree(project_dir)
    if not tree:
        raise FileNotFoundError(EXPERIMENT_TREE_JSON)
    node = _find_node(tree, node_id)
    template_name = str(node.get("template_name") or "")
    if not template_name:
        raise ValueError(f"experiment tree node has no template_name: {node_id}")
    ctx = _tree_context(tree)
    rerun_id = f"tree_rerun_{safe_id(node_id)}_{utc_now().replace(':', '').replace('-', '').replace('.', '').replace('+', 'z')}"
    experiment_id = f"rerun_{safe_id(node_id)}"
    config = {
        "topic": ctx.get("topic"),
        "research_question": ctx.get("research_question"),
        "retrieval_mode": ctx.get("retrieval_mode") or "local_hybrid_fts",
        "tree_rerun_parent_node_id": node_id,
        "tree_rerun_source_template": template_name,
    }
    if template_name == GENERATED_CODE_TEMPLATE:
        config.update(
            {
                "generated_code_timeout_seconds": timeout_seconds,
                "generated_code_max_memory_mb": max_memory_mb,
                "generated_code_sandbox_mode": sandbox_mode,
                "generated_code_strategy": tree.get("generated_code_strategy") or "lexical_diagnostics",
                "generated_code_source_mode": "deterministic",
                "generated_code_approved": True,
            }
        )
        if sandbox_mode == "docker" and docker_image:
            config["generated_code_docker_image"] = docker_image
    plan = {
        "schema_version": f"{SCHEMA_PREFIX}.experiment_tree_rerun_plan.v1",
        "project_id": project_id,
        "created_at": utc_now(),
        "run_id": rerun_id,
        "source_tree_file": EXPERIMENT_TREE_JSON,
        "source_node_id": node_id,
        "safe_runner": True,
        "arbitrary_code_execution": False,
        "experiments": [
            {
                "experiment_id": experiment_id,
                "idea_id": node.get("experiment_id") or "tree_node",
                "template_name": template_name,
                "status": "planned",
                "safe_execution": True,
                "generated_code_execution": template_name == GENERATED_CODE_TEMPLATE,
                "arbitrary_code_execution": False,
                "tree_node_rerun": True,
                "parent_node_id": node_id,
                "config": config,
            }
        ],
    }
    results = run_experiment_plan(project_dir, project_id, plan, run_id=rerun_id)
    result = results[0] if results else {}
    rerun_node = _node_from_result(result, int(node.get("depth") or 0) + 1, node_id) if result else {}
    nodes = tree.setdefault("nodes", [])
    if isinstance(nodes, list) and rerun_node:
        nodes.append({**rerun_node, "tree_node_rerun": True, "rerun_id": rerun_id})
    edges = tree.setdefault("edges", [])
    if isinstance(edges, list) and rerun_node:
        edges.append({"from": node_id, "to": rerun_node["node_id"]})
    tree.setdefault("rerun_records", [])
    if isinstance(tree.get("rerun_records"), list):
        tree["rerun_records"].append({"rerun_id": rerun_id, "source_node_id": node_id, "rerun_node_id": rerun_node.get("node_id") if rerun_node else None})
    if rerun_node and rerun_node.get("failure_reason"):
        append_jsonl(project_dir, EXPERIMENT_TREE_FAILURES_JSONL, _failure_record(project_id, rerun_id, rerun_node))
    _persist_tree(project_dir, tree)
    record = {
        "schema_version": f"{SCHEMA_PREFIX}.experiment_tree_rerun.v1",
        "project_id": project_id,
        "created_at": utc_now(),
        "source_node_id": node_id,
        "source_node": node,
        "rerun_id": rerun_id,
        "rerun_node": rerun_node,
        "rerun_plan": plan,
        "results": results,
        "human_review_required": True,
        "limitations": [
            "Rerun results are local experiment artifacts and not scientific proof.",
            "Generated-code reruns still require source and sandbox artifact review.",
        ],
    }
    append_jsonl(project_dir, EXPERIMENT_TREE_RERUNS_JSONL, record)
    append_audit_event(
        project_dir,
        project_id,
        "rerun_auto_scientist_experiment_tree_node",
        "A local Auto Scientist experiment tree node was rerun.",
        {"node_id": node_id, "rerun_id": rerun_id, "rerun_node_id": rerun_node.get("node_id") if rerun_node else None},
        source="api",
        event_category="agent",
        risk_level="medium",
        entity_type="auto_scientist_experiment_tree",
        entity_id=node_id,
    )
    return record


def _records_for_run(project_dir: Path, run_id: str | None, tree: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in read_jsonl(project_dir, RUNS_JSONL):
        if run_id and record.get("run_id") != run_id:
            continue
        enriched = dict(record)
        result_payload: dict[str, Any] | None = None
        for output_file in record.get("output_files", []):
            if isinstance(output_file, str) and output_file.endswith("experiment_result.json"):
                payload = read_json(project_dir / output_file, {})
                if isinstance(payload, dict):
                    result_payload = payload
                    break
        if result_payload:
            enriched["result"] = result_payload
        key = str(enriched.get("experiment_id"))
        if key not in seen:
            seen.add(key)
            records.append(enriched)
    for record in tree.get("tree_experiment_results", []):
        if isinstance(record, dict):
            key = str(record.get("experiment_id"))
            if key not in seen:
                seen.add(key)
                records.append(record)
    for rerun in read_jsonl(project_dir, EXPERIMENT_TREE_RERUNS_JSONL):
        for record in rerun.get("results", []):
            if isinstance(record, dict):
                key = str(record.get("experiment_id")) + ":" + str(rerun.get("rerun_id"))
                if key not in seen:
                    seen.add(key)
                    records.append(record)
    return records


def rewrite_auto_scientist_paper_from_tree(
    project_dir: Path,
    project_id: str,
    node_id: str | None = None,
    reason: str = "",
) -> dict[str, Any]:
    tree = read_experiment_tree(project_dir)
    if not tree:
        raise FileNotFoundError(EXPERIMENT_TREE_JSON)
    if node_id:
        select_experiment_tree_node(project_dir, project_id, node_id, reason=reason or "Selected for paper rewrite.")
        tree = read_experiment_tree(project_dir)
    selected = tree.get("selected_best_node") or tree.get("best_node") or {}
    latest = read_json(project_dir / LATEST_RUN_JSON, {})
    run_id = str(tree.get("run_id") or (latest.get("run_id") if isinstance(latest, dict) else "") or "tree_rewrite")
    ideas = read_json(project_dir / IDEAS_JSON, {})
    plan = read_json(project_dir / EXPERIMENT_PLAN_JSON, {})
    analysis = read_json(project_dir / ANALYSIS_JSON, {})
    if not isinstance(ideas, dict):
        ideas = {"ideas": [], "topic": "local research project", "research_question": "What can local evidence support?"}
    if not isinstance(plan, dict):
        plan = {"experiments": []}
    if not isinstance(analysis, dict):
        analysis = {}
    results = _records_for_run(project_dir, run_id, tree)
    paper_outputs = (latest.get("paper_outputs") if isinstance(latest, dict) else {}) or {}
    rewritten = generate_auto_scientist_paper(
        project_dir,
        project_id,
        run_id,
        ideas,
        plan,
        results,
        analysis,
        paper_outputs=paper_outputs if isinstance(paper_outputs, dict) else {},
        experiment_tree=tree,
    )
    binding_payload: dict[str, Any] = {}
    try:
        binding_payload = generate_experiment_claim_bindings(project_dir, project_id, manuscript_relative_path="manuscript/auto_scientist_paper.md")
    except Exception as exc:
        binding_payload = {"error": exc.__class__.__name__, "binding_file": EXPERIMENT_CLAIM_BINDINGS_JSON}
    record = {
        "schema_version": f"{SCHEMA_PREFIX}.paper_rewrite.v1",
        "project_id": project_id,
        "run_id": run_id,
        "created_at": utc_now(),
        "selected_node_id": selected.get("node_id") if isinstance(selected, dict) else None,
        "selected_node": selected,
        "reason": reason.strip(),
        "paper_file": rewritten.get("paper_file"),
        "latex_file": rewritten.get("latex_file"),
        "audit_file": rewritten.get("audit_file"),
        "experiment_claim_bindings_file": EXPERIMENT_CLAIM_BINDINGS_JSON if not binding_payload.get("error") else None,
        "experiment_claim_bindings_summary": binding_payload.get("summary") if isinstance(binding_payload, dict) else None,
        "experiment_claim_bindings_error": binding_payload.get("error") if isinstance(binding_payload, dict) else None,
        "source_tree_file": EXPERIMENT_TREE_JSON,
        "human_review_required": True,
        "limitations": [
            "Paper rewrite emphasizes a selected local experiment node but remains AI-generated draft text.",
            "The selected node and manuscript require human scientific review before external use.",
        ],
    }
    append_jsonl(project_dir, PAPER_REWRITES_JSONL, record)
    write_project_json(project_dir, LATEST_PAPER_REWRITE_JSON, record)
    if isinstance(latest, dict):
        latest["latest_paper_rewrite_file"] = LATEST_PAPER_REWRITE_JSON
        latest["latest_paper_rewrite"] = record
        latest["experiment_claim_bindings_file"] = record.get("experiment_claim_bindings_file")
        latest["experiment_claim_bindings_summary"] = record.get("experiment_claim_bindings_summary")
        write_project_json(project_dir, LATEST_RUN_JSON, latest)
    append_audit_event(
        project_dir,
        project_id,
        "rewrite_auto_scientist_paper_from_tree",
        "Auto Scientist paper was rewritten using the selected experiment tree node.",
        {"run_id": run_id, "selected_node_id": record["selected_node_id"], "paper_file": record["paper_file"]},
        source="api",
        event_category="agent",
        risk_level="medium",
        entity_type="auto_scientist_paper",
        entity_id=run_id,
    )
    return record
