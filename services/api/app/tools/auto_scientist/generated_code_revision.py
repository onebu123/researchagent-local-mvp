from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.auto_scientist.contracts import (
    CODE_REVISION_ROUNDS_JSONL,
    CODE_REVIEW_ROUNDS_JSONL,
    SCHEMA_PREFIX,
    append_jsonl,
    read_jsonl,
    safe_id,
    utc_now,
)
from app.tools.auto_scientist.generated_code_review import review_generated_code_result
from app.tools.auto_scientist.generated_code_sandbox import (
    generate_deterministic_experiment_source,
    run_generated_code_experiment,
)

REVISABLE_STATUSES = {
    "failed",
    "timeout",
    "rejected_by_static_scan",
    "docker_unavailable",
    "pending_human_approval",
    "rejected_by_human_approval",
}


def read_generated_code_revision_rounds(project_dir: Path) -> list[dict[str, Any]]:
    return read_jsonl(project_dir, CODE_REVISION_ROUNDS_JSONL)


def _result_payload(result_record: dict[str, Any]) -> dict[str, Any]:
    payload = result_record.get("result")
    return payload if isinstance(payload, dict) else {}


def _safe_revision_source(config: dict[str, Any], original_result: dict[str, Any], round_index: int, review: dict[str, Any] | None = None) -> str:
    revised_config = dict(config)
    strategy = "lexical_diagnostics"
    if review and review.get("failure_class") == "timeout":
        strategy = "lexical_diagnostics"
    elif review and review.get("failure_class") == "sandbox_unavailable":
        strategy = "retrieval_ablation"
    elif review and review.get("failure_class") == "approval_gate":
        strategy = "lexical_diagnostics"
    revised_config["generated_code_strategy"] = strategy
    revised_config["research_question"] = (
        str(config.get("research_question") or "What can the local evidence support?")
        + f" Revision round {round_index}: produce conservative diagnostics only."
    )[:1000]
    source = generate_deterministic_experiment_source(revised_config)
    failure_class = str((review or {}).get("failure_class") or "unclassified")
    return (
        "# Auto-generated safe reviewer revision of a failed or blocked generated-code experiment.\n"
        f"# Failure class: {failure_class}.\n"
        "# This revision intentionally falls back to a deterministic bounded diagnostic script.\n"
        + source
    )


def _is_generated_code_candidate(result_record: dict[str, Any]) -> bool:
    return result_record.get("generated_code_execution") is True or result_record.get("template_name") == "generated_code_smoke_test"


def run_generated_code_revision_loop(
    project_dir: Path,
    project_id: str,
    run_id: str,
    results: list[dict[str, Any]],
    max_rounds: int = 1,
    generated_code_timeout_seconds: int = 5,
    generated_code_max_memory_mb: int = 512,
    generated_code_sandbox_mode: str = "subprocess",
    generated_code_docker_image: str | None = None,
    generated_code_strategy: str = "lexical_diagnostics",
) -> dict[str, Any]:
    """Run conservative reviewer->code revision->rerun rounds for generated-code failures.

    This is not a free-form autonomous code repair system. The first MVP repair
    strategy replaces failed/proposed generated code with a deterministic safe
    diagnostic script and reruns it through the same sandbox/result contract.
    """
    max_rounds = max(0, min(int(max_rounds), 3))
    revised_results: list[dict[str, Any]] = []
    revision_records: list[dict[str, Any]] = []
    candidates = [
        item for item in results
        if isinstance(item, dict)
        and _is_generated_code_candidate(item)
        and str(item.get("status") or "") in REVISABLE_STATUSES
    ]
    if max_rounds <= 0 or not candidates:
        return {
            "schema_version": f"{SCHEMA_PREFIX}.generated_code_revision_summary.v1",
            "project_id": project_id,
            "run_id": run_id,
            "enabled": max_rounds > 0,
            "candidate_count": len(candidates),
            "revision_count": 0,
            "revision_results": [],
            "revision_rounds_file": CODE_REVISION_ROUNDS_JSONL,
            "code_review_rounds_file": "auto_scientist/code_review_rounds.jsonl",
        }

    for round_index in range(1, max_rounds + 1):
        round_candidates = candidates if round_index == 1 else [
            item for item in revised_results
            if str(item.get("status") or "") in REVISABLE_STATUSES
        ]
        if not round_candidates:
            break
        for original in round_candidates:
            experiment_id = str(original.get("experiment_id") or f"generated_code_exp_{round_index}")
            review = review_generated_code_result(project_dir, project_id, run_id, original, round_index=round_index)
            # Mirror the diagnosis from the reviewer helper so the revision loop
            # remains traceable even if previous test/demo workflows reset the
            # derived code-review read model.  Duplicate review records are safe:
            # they are append-only audit artifacts keyed by run/round/experiment.
            mirrored_review = {**review, "mirror_source": "generated_code_revision_loop"}
            append_jsonl(project_dir, CODE_REVIEW_ROUNDS_JSONL, mirrored_review)
            revision_sandbox_mode = generated_code_sandbox_mode
            if review.get("recommended_revision_strategy") == "switch_to_subprocess_safe_diagnostic":
                revision_sandbox_mode = "subprocess"
            config = {
                "topic": "generated-code experiment revision",
                "research_question": "Can a revised safe diagnostic script complete over local evidence?",
                "parent_experiment_id": experiment_id,
                "generated_code_timeout_seconds": generated_code_timeout_seconds,
                "generated_code_max_memory_mb": generated_code_max_memory_mb,
                "generated_code_sandbox_mode": revision_sandbox_mode,
                "generated_code_source_mode": "deterministic",
                "generated_code_strategy": "retrieval_ablation" if review.get("failure_class") == "sandbox_unavailable" else generated_code_strategy,
                "generated_code_approved": True,
                "generated_source": _safe_revision_source({}, original, round_index, review),
            }
            if generated_code_docker_image and revision_sandbox_mode == "docker":
                config["generated_code_docker_image"] = generated_code_docker_image
            revised_experiment_id = f"rev_r{round_index}_{safe_id(experiment_id)}"
            result = run_generated_code_experiment(
                project_dir,
                project_id,
                run_id,
                revised_experiment_id,
                config,
            )
            result_record = {
                "schema_version": f"{SCHEMA_PREFIX}.generated_code_revision_result.v1",
                "project_id": project_id,
                "run_id": run_id,
                "round_index": round_index,
                "parent_experiment_id": experiment_id,
                "experiment_id": revised_experiment_id,
                "template_name": "generated_code_revision",
                "status": result.get("status"),
                "generated_code_execution": True,
                "arbitrary_code_execution": False,
                "result": result,
                "output_files": (result.get("sandbox") or {}).get("output_files", []) if isinstance(result.get("sandbox"), dict) else [],
                "created_at": utc_now(),
            }
            revised_results.append(result_record)
            revision_record = {
                "schema_version": f"{SCHEMA_PREFIX}.generated_code_revision_round.v1",
                "project_id": project_id,
                "run_id": run_id,
                "round_index": round_index,
                "parent_experiment_id": experiment_id,
                "revision_experiment_id": revised_experiment_id,
                "parent_status": original.get("status"),
                "revision_status": result.get("status"),
                "repair_strategy": review.get("recommended_revision_strategy", "deterministic_safe_diagnostic_fallback"),
                "review_failure_class": review.get("failure_class"),
                "code_review": review,
                "human_review_required": True,
                "created_at": utc_now(),
            }
            revision_records.append(revision_record)
            append_jsonl(project_dir, CODE_REVISION_ROUNDS_JSONL, revision_record)

    append_audit_event(
        project_dir,
        project_id,
        "run_generated_code_revision_loop",
        "Generated-code revision loop completed for Auto Scientist sandbox results.",
        {
            "run_id": run_id,
            "candidate_count": len(candidates),
            "revision_count": len(revision_records),
            "revision_rounds_file": CODE_REVISION_ROUNDS_JSONL,
        },
        source="api",
        event_category="agent",
        risk_level="medium",
        entity_type="auto_scientist",
        entity_id=run_id,
    )
    return {
        "schema_version": f"{SCHEMA_PREFIX}.generated_code_revision_summary.v1",
        "project_id": project_id,
        "run_id": run_id,
        "enabled": True,
        "candidate_count": len(candidates),
        "revision_count": len(revision_records),
        "revision_results": revised_results,
        "revision_rounds_file": CODE_REVISION_ROUNDS_JSONL,
        "code_review_rounds_file": "auto_scientist/code_review_rounds.jsonl",
    }
