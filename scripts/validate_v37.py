from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

REQUIRED_SOURCE_FILES = [
    "services/api/app/tools/auto_scientist/experiment_code_writer.py",
    "services/api/app/tools/auto_scientist/generated_code_sandbox.py",
    "services/api/app/tools/auto_scientist/experiment_tree_search.py",
    "services/api/app/tools/auto_scientist/experiment_tree_ops.py",
    "services/api/app/tools/auto_scientist/tree_revision_loop.py",
    "services/api/app/tools/auto_scientist/experiment_claim_binding.py",
    "services/api/app/tools/auto_scientist/paper_citation_binding.py",
    "services/api/app/tools/auto_scientist/paper_compile.py",
    "services/api/app/tools/job_manager.py",
    "services/api/app/api/auto_scientist.py",
    "services/api/app/api/jobs.py",
    "apps/web/components/AutoScientistWorkbench.tsx",
    "scripts/run_auto_scientist_demo.py",
    "scripts/validate_v37.py",
]

REQUIRED_DOCS = [
    "docs/auto_scientist.md",
    "docs/auto_scientist_end_to_end_demo.md",
    "docs/citation_compile_pipeline.md",
]

REQUIRED_TESTS = [
    "services/api/tests/test_v25_auto_scientist.py",
    "services/api/tests/test_v26_generated_code_sandbox.py",
    "services/api/tests/test_v27_docker_tree_search.py",
    "services/api/tests/test_v28_generated_code_lifecycle.py",
    "services/api/tests/test_v29_auto_scientist_codegen_jobs.py",
    "services/api/tests/test_v31_jobs_and_workbench.py",
    "services/api/tests/test_v32_job_events_and_rerun.py",
    "services/api/tests/test_v33_experiment_tree_node_workflow.py",
    "services/api/tests/test_v34_tree_revision_loop.py",
    "services/api/tests/test_v35_experiment_claim_binding.py",
    "services/api/tests/test_v36_paper_citation_compile_pipeline.py",
    "services/api/tests/test_v37_auto_scientist_demo_validation.py",
]

REQUIRED_AUTOSCIENTIST_API_MARKERS = [
    "auto-scientist/run",
    "generated-code/proposals",
    "generated-code/rerun",
    "experiment-tree/rewrite-paper",
    "experiment-tree/revision-plan",
    "experiment-claim-bindings",
    "paper-citation-bindings",
    "paper-compile",
]

REQUIRED_JOB_API_MARKERS = [
    "jobs/auto-scientist/start",
    "events/stream",
    "jobs/{job_id}/cancel",
]

REQUIRED_FRONTEND_MARKERS = [
    "Ideas",
    "Experiments",
    "Code Review",
    "Paper",
    "Trust",
    "Job event timeline",
    "Rerun approved proposal",
    "Bind claims to experiments",
    "Bind citations",
    "Compile / preview PDF",
]


def _exists(relative_path: str) -> bool:
    return (ROOT / relative_path).exists()


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8", errors="replace")


def _check_files(paths: list[str]) -> list[str]:
    return [path for path in paths if not _exists(path)]


def _check_markers(relative_path: str, markers: list[str]) -> list[str]:
    text = _read(relative_path) if _exists(relative_path) else ""
    return [marker for marker in markers if marker not in text]


def _check_demo_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"checked": False, "passed": False, "reason": f"report not found: {path}"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"checked": True, "passed": False, "reason": f"invalid JSON: {exc}"}
    missing = payload.get("missing_required_artifacts") or []
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    required_summary_fields = [
        "run_status",
        "experiment_count",
        "job_event_count",
        "trust_package_file_count",
        "latex_compile_status",
    ]
    missing_summary = [field for field in required_summary_fields if field not in summary]
    passed = bool(payload.get("passed")) and not missing and not missing_summary
    return {
        "checked": True,
        "passed": passed,
        "missing_required_artifacts": missing,
        "missing_summary_fields": missing_summary,
        "summary": summary,
    }


def build_validation_report(demo_report: Path | None = None) -> dict[str, Any]:
    source_missing = _check_files(REQUIRED_SOURCE_FILES)
    docs_missing = _check_files(REQUIRED_DOCS)
    tests_missing = _check_files(REQUIRED_TESTS)
    auto_scientist_markers_missing = _check_markers("services/api/app/api/auto_scientist.py", REQUIRED_AUTOSCIENTIST_API_MARKERS)
    job_markers_missing = _check_markers("services/api/app/api/jobs.py", REQUIRED_JOB_API_MARKERS)
    frontend_markers_missing = _check_markers("apps/web/components/AutoScientistWorkbench.tsx", REQUIRED_FRONTEND_MARKERS)
    demo_check = _check_demo_report(demo_report) if demo_report else {"checked": False, "passed": True}
    failures = {
        "source_missing": source_missing,
        "docs_missing": docs_missing,
        "tests_missing": tests_missing,
        "auto_scientist_api_markers_missing": auto_scientist_markers_missing,
        "job_api_markers_missing": job_markers_missing,
        "frontend_markers_missing": frontend_markers_missing,
        "demo_report": demo_check if demo_check.get("checked") and not demo_check.get("passed") else {},
    }
    failure_count = sum(len(value) for value in failures.values() if isinstance(value, list))
    if isinstance(failures.get("demo_report"), dict) and failures["demo_report"]:
        failure_count += 1
    return {
        "schema_version": "researchagent.validate_v37.v1",
        "passed": failure_count == 0,
        "failure_count": failure_count,
        "failures": failures,
        "coverage": {
            "source_files_checked": len(REQUIRED_SOURCE_FILES),
            "docs_checked": len(REQUIRED_DOCS),
            "tests_checked": len(REQUIRED_TESTS),
            "auto_scientist_api_markers_checked": len(REQUIRED_AUTOSCIENTIST_API_MARKERS),
            "job_api_markers_checked": len(REQUIRED_JOB_API_MARKERS),
            "frontend_markers_checked": len(REQUIRED_FRONTEND_MARKERS),
            "demo_report_checked": bool(demo_report),
        },
        "limitations": [
            "validate_v37 is a static and artifact-contract validation helper; it does not replace pytest, frontend build, E2E tests, or scientific review.",
            "A passing demo report means expected local artifacts were generated, not that the generated paper is scientifically valid.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the v37 Auto Scientist productization contract.")
    parser.add_argument("--demo-report", type=Path, default=None, help="Optional JSON report from scripts/run_auto_scientist_demo.py.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path for the validation report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_validation_report(args.demo_report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"validate_v37 report: {args.output}")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report.get("passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
