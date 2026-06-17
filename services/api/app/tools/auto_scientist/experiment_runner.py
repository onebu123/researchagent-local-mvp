from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from app.tools.audit_log import append_audit_event
from app.tools.auto_scientist.contracts import (
    EXPERIMENT_PLAN_JSON,
    RUNS_JSONL,
    SCHEMA_PREFIX,
    append_jsonl,
    ensure_auto_scientist_dirs,
    read_json,
    safe_id,
    utc_now,
    write_project_json,
    write_project_text,
)
from app.tools.auto_scientist.experiment_registry import (
    registered_experiment_templates,
    run_registered_experiment,
)
from app.tools.auto_scientist.generated_code_sandbox import (
    GENERATED_CODE_TEMPLATE,
    run_generated_code_experiment,
)


def read_experiment_plan(project_dir: Path) -> dict[str, Any]:
    payload = read_json(project_dir / EXPERIMENT_PLAN_JSON, {})
    return payload if isinstance(payload, dict) else {}


def build_experiment_plan(
    project_dir: Path,
    project_id: str,
    ideas_payload: dict[str, Any],
    max_experiments_per_idea: int = 2,
    retrieval_mode: str = "local_hybrid_fts",
    allow_generated_code_experiments: bool = False,
    generated_code_timeout_seconds: int = 5,
    generated_code_max_memory_mb: int = 128,
    generated_code_sandbox_mode: str = "subprocess",
    generated_code_docker_image: str | None = None,
    generated_code_source_mode: str = "deterministic",
    generated_code_strategy: str = "lexical_diagnostics",
    generated_code_requires_approval: bool | None = None,
    generated_code_approved: bool = False,
) -> dict[str, Any]:
    ensure_auto_scientist_dirs(project_dir)
    available = set(registered_experiment_templates(include_generated_code=allow_generated_code_experiments))
    experiments: list[dict[str, Any]] = []
    for idea in ideas_payload.get("ideas", []):
        if not isinstance(idea, dict):
            continue
        idea_id = str(idea.get("idea_id") or "idea_unknown")
        for template_index, template in enumerate(idea.get("experiment_templates", [])[: max(1, max_experiments_per_idea)], start=1):
            if template not in available:
                continue
            experiment_id = f"exp_{safe_id(idea_id)}_{template_index:02d}_{safe_id(str(template))}"
            experiments.append(
                {
                    "experiment_id": experiment_id,
                    "idea_id": idea_id,
                    "template_name": template,
                    "status": "planned",
                    "safe_execution": True,
                    "arbitrary_code_execution": False,
                    "config": {
                        "topic": ideas_payload.get("topic"),
                        "research_question": ideas_payload.get("research_question"),
                        "retrieval_mode": retrieval_mode,
                    },
                }
            )

    if allow_generated_code_experiments and ideas_payload.get("ideas"):
        idea = ideas_payload["ideas"][0] if isinstance(ideas_payload.get("ideas"), list) else {}
        idea_id = str(idea.get("idea_id") or "idea_001") if isinstance(idea, dict) else "idea_001"
        experiments.append(
            {
                "experiment_id": f"exp_{safe_id(idea_id)}_generated_code_smoke_test",
                "idea_id": idea_id,
                "template_name": GENERATED_CODE_TEMPLATE,
                "status": "planned",
                "safe_execution": True,
                "generated_code_execution": True,
                "arbitrary_code_execution": False,
                "sandbox_required": True,
                "config": {
                    "topic": ideas_payload.get("topic"),
                    "research_question": ideas_payload.get("research_question"),
                    "retrieval_mode": retrieval_mode,
                    "generated_code_timeout_seconds": generated_code_timeout_seconds,
                    "generated_code_max_memory_mb": generated_code_max_memory_mb,
                    "generated_code_sandbox_mode": generated_code_sandbox_mode,
                    "generated_code_source_mode": generated_code_source_mode,
                    "generated_code_strategy": generated_code_strategy,
                    "generated_code_approved": generated_code_approved,
                    **({"generated_code_requires_approval": generated_code_requires_approval} if generated_code_requires_approval is not None else {}),
                    **({"generated_code_docker_image": generated_code_docker_image} if generated_code_docker_image else {}),
                },
            }
        )
    payload = {
        "schema_version": f"{SCHEMA_PREFIX}.experiment_plan.v1",
        "project_id": project_id,
        "created_at": utc_now(),
        "experiment_plan_file": EXPERIMENT_PLAN_JSON,
        "safe_runner": True,
        "arbitrary_code_execution": False,
        "generated_code_experiments_enabled": allow_generated_code_experiments,
        "registered_templates": registered_experiment_templates(include_generated_code=allow_generated_code_experiments),
        "experiments": experiments,
        "retrieval_mode": retrieval_mode,
        "topic": ideas_payload.get("topic"),
        "research_question": ideas_payload.get("research_question"),
        "generated_code_sandbox_mode": generated_code_sandbox_mode if allow_generated_code_experiments else None,
        "generated_code_source_mode": generated_code_source_mode if allow_generated_code_experiments else None,
        "generated_code_strategy": generated_code_strategy if allow_generated_code_experiments else None,
        "generated_code_requires_approval": generated_code_requires_approval if allow_generated_code_experiments else None,
        "summary": {"experiment_count": len(experiments)},
    }
    write_project_json(project_dir, EXPERIMENT_PLAN_JSON, payload)
    return payload


def run_experiment_plan(
    project_dir: Path,
    project_id: str,
    experiment_plan: dict[str, Any],
    run_id: str,
    progress_callback: Callable[[str, float | None], None] | None = None,
) -> list[dict[str, Any]]:
    ensure_auto_scientist_dirs(project_dir)
    results: list[dict[str, Any]] = []
    experiments = [item for item in experiment_plan.get("experiments", []) if isinstance(item, dict)]
    total = max(len(experiments), 1)
    for index, experiment in enumerate(experiments, start=1):
        if not isinstance(experiment, dict):
            continue
        experiment_id = str(experiment.get("experiment_id") or f"exp_{len(results)+1:03d}")
        template_name = str(experiment.get("template_name") or "")
        result_dir = f"auto_scientist/experiments/{run_id}/{experiment_id}"
        if progress_callback is not None:
            progress_callback(f"auto scientist: running experiment {index}/{total}: {experiment_id}", 0.30 + (0.22 * ((index - 1) / total)))
        try:
            if template_name == GENERATED_CODE_TEMPLATE:
                result = run_generated_code_experiment(
                    project_dir,
                    project_id,
                    run_id,
                    experiment_id,
                    dict(experiment.get("config") or {}),
                )
            else:
                result = run_registered_experiment(
                    project_dir,
                    project_id,
                    template_name,
                    dict(experiment.get("config") or {}),
                )
            status = result.get("status", "completed")
            error = None
        except Exception as exc:
            result = {
                "status": "failed",
                "template_name": template_name,
                "metrics": {},
                "claims": [],
                "summary_markdown": f"# Failed experiment\n\n{exc.__class__.__name__}: {exc}\n",
                "arbitrary_code_execution": False,
                "registered_safe_template": template_name in registered_experiment_templates(include_generated_code=True),
            }
            status = "failed"
            error = exc.__class__.__name__
        output_files = []
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
            "status": status,
            "error": error,
            "metrics": result.get("metrics", {}),
            "claims": result.get("claims", []),
            "limitations": [
                "This is a registered local template or sandboxed generated-code result, not independent scientific proof.",
                "Human review is required before using any claim externally.",
            ],
        }
        if result.get("sandbox"):
            result_payload["sandbox"] = result.get("sandbox")
        for optional_field in ["source_mode", "source_hash", "approval_required", "latest_approval_decision"]:
            if optional_field in result:
                result_payload[optional_field] = result.get(optional_field)
        result_json = f"{result_dir}/experiment_result.json"
        metrics_json = f"{result_dir}/metrics.json"
        summary_md = f"{result_dir}/summary.md"
        write_project_json(project_dir, result_json, result_payload)
        write_project_json(project_dir, metrics_json, result_payload["metrics"])
        write_project_text(project_dir, summary_md, str(result.get("summary_markdown") or ""))
        output_files.extend([result_json, metrics_json, summary_md])
        for relative_path in (result.get("sandbox") or {}).get("output_files", []):
            if isinstance(relative_path, str) and relative_path not in output_files:
                output_files.append(relative_path)
        figure_svg = result.get("figure_svg")
        if figure_svg:
            figure_path = f"{result_dir}/figure.svg"
            write_project_text(project_dir, figure_path, str(figure_svg))
            output_files.append(figure_path)
        record = {
            "created_at": utc_now(),
            "run_id": run_id,
            "experiment_id": experiment_id,
            "template_name": template_name,
            "status": status,
            "safe_execution": True,
            "generated_code_execution": template_name == GENERATED_CODE_TEMPLATE,
            "arbitrary_code_execution": False,
            "output_files": output_files,
            "metric_keys": sorted(result_payload["metrics"].keys()) if isinstance(result_payload["metrics"], dict) else [],
        }
        for optional_field in ["source_mode", "source_hash", "approval_required"]:
            if optional_field in result:
                record[optional_field] = result.get(optional_field)
        append_jsonl(project_dir, RUNS_JSONL, record)
        results.append({**record, "result": result_payload})
        if progress_callback is not None:
            progress_callback(f"auto scientist: completed experiment {index}/{total}: {experiment_id}", 0.30 + (0.22 * (index / total)))
    append_audit_event(
        project_dir,
        project_id,
        "run_auto_scientist_experiments",
        "Safe local Auto Scientist experiment plan was executed.",
        {
            "run_id": run_id,
            "experiment_count": len(results),
            "failed_count": sum(1 for item in results if item.get("status") == "failed"),
            "arbitrary_code_execution": False,
        },
        source="api",
        event_category="agent",
        risk_level="medium",
        entity_type="auto_scientist",
        entity_id=run_id,
    )
    return results
