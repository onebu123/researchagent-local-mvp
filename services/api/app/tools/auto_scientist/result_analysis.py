from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.auto_scientist.contracts import ANALYSIS_JSON, REPORT_MD, SCHEMA_PREFIX, utc_now, write_project_json, write_project_text


def _support_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"supported": 0, "weakly_supported": 0, "unsupported": 0, "needs_human_review": 0}
    for item in results:
        result = item.get("result") or {}
        for claim in result.get("claims", []) if isinstance(result, dict) else []:
            if not isinstance(claim, dict):
                continue
            status = str(claim.get("support_status") or "needs_human_review")
            if status in counts:
                counts[status] += 1
            else:
                counts["needs_human_review"] += 1
    return counts


def analyze_experiment_results(
    project_dir: Path,
    project_id: str,
    run_id: str,
    ideas_payload: dict[str, Any],
    experiment_plan: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for item in results:
        status = str(item.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    support_counts = _support_counts(results)
    generated_code_count = sum(1 for item in results if item.get("generated_code_execution") is True)
    sandbox_failures = sum(1 for item in results if item.get("generated_code_execution") is True and item.get("status") != "completed")
    best_experiment = None
    for item in results:
        if item.get("status") == "completed":
            best_experiment = {
                "experiment_id": item.get("experiment_id"),
                "template_name": item.get("template_name"),
                "output_files": item.get("output_files", []),
            }
            break
    analysis = {
        "schema_version": f"{SCHEMA_PREFIX}.analysis.v1",
        "project_id": project_id,
        "run_id": run_id,
        "created_at": utc_now(),
        "analysis_file": ANALYSIS_JSON,
        "topic": ideas_payload.get("topic"),
        "research_question": ideas_payload.get("research_question"),
        "experiment_count": len(results),
        "status_counts": status_counts,
        "claim_support_counts": support_counts,
        "best_experiment": best_experiment,
        "safe_execution": True,
        "generated_code_experiment_count": generated_code_count,
        "sandbox_failure_count": sandbox_failures,
        "arbitrary_code_execution": False,
        "sandboxed_generated_code": generated_code_count > 0,
        "interpretation": (
            "The safe local experiment templates produced project-level evidence diagnostics. "
            "These diagnostics can support a cautious manuscript draft, but they are not independent scientific proof."
        ),
        "human_review_required": True,
    }
    write_project_json(project_dir, ANALYSIS_JSON, analysis)
    report = [
        "# Auto Scientist Report",
        "",
        f"Run ID: `{run_id}`",
        "",
        "This report summarizes safe local registered experiment templates. It is not peer review or scientific proof.",
        "",
        "## Experiment Status",
        "",
    ]
    for key, value in sorted(status_counts.items()):
        report.append(f"- {key}: {value}")
    report.extend(["", "## Claim Support Counts", ""])
    for key, value in sorted(support_counts.items()):
        report.append(f"- {key}: {value}")
    report.extend(["", "## Generated-Code Sandbox", "", f"- Sandboxed generated-code experiments: {generated_code_count}", f"- Sandbox failures: {sandbox_failures}", "", "## Limitations", "", "- Human review is required.", "- Arbitrary unscanned code execution is not allowed; generated code, when enabled, is statically scanned and run with local resource limits."])
    write_project_text(project_dir, REPORT_MD, "\n".join(report) + "\n")
    return analysis
