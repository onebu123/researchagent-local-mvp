from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

VERSION = "v3.0.0-rc1"
PEP440_VERSION = "3.0.0rc1"
NPM_VERSION = "3.0.0-rc1"

REQUIRED_FILES = [
    ".env.example",
    "README.md",
    "CHANGELOG.md",
    "docs/release_v3.md",
    "docs/auto_scientist.md",
    "docs/auto_scientist_end_to_end_demo.md",
    "docs/citation_compile_pipeline.md",
    "scripts/run_auto_scientist_demo.py",
    "scripts/validate_v37.py",
    "scripts/validate_v38.py",
    "services/api/app/tools/auto_scientist/scientist_loop.py",
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
]

VERSION_SURFACES = {
    "README.md": [VERSION],
    "CHANGELOG.md": [VERSION],
    "docs/release_v3.md": [VERSION],
    "docs/roadmap.md": [VERSION],
    "docs/github_release_checklist.md": [VERSION],
    "services/api/main.py": [f'APP_VERSION = "{VERSION}"'],
    "services/api/pyproject.toml": [f'version = "{PEP440_VERSION}"', VERSION],
    "apps/web/package.json": [f'"version": "{NPM_VERSION}"'],
    "apps/web/package-lock.json": [f'"version": "{NPM_VERSION}"'],
    "apps/web/features/workspace/useWorkspaceData.ts": [VERSION],
    "apps/web/lib/api/legacy.ts": [VERSION],
    "scripts/package_release.py": [f'DEFAULT_VERSION = "{VERSION}"'],
    "scripts/collect_evidence.py": [f'default="{VERSION}"'],
    "scripts/verify_local.py": [f'VERSION = "{VERSION}"'],
    "services/api/app/tools/production_scaffold.py": [f'"version": "{VERSION}"'],
}

FORBIDDEN_CURRENT_VERSION_MARKERS = [
    "v2.0.1-dev",
    "2.0.1-dev",
    "2.0.1.dev0",
]

CI_MARKERS = [
    "Validate v38 release contract",
    "Auto Scientist demo smoke",
    "Validate v38 demo report",
    "Package release candidate",
    "python scripts/package_release.py --version v3.0.0-rc1",
]

AUTOSCIENTIST_API_MARKERS = [
    "auto-scientist/run",
    "generated-code/proposals",
    "generated-code/rerun",
    "experiment-tree/rewrite-paper",
    "experiment-tree/revision-plan",
    "experiment-claim-bindings",
    "paper-citation-bindings",
    "paper-compile",
]

JOB_API_MARKERS = [
    "jobs/auto-scientist/start",
    "events/stream",
    "jobs/{job_id}/cancel",
]

FRONTEND_MARKERS = [
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

REQUIRED_DEMO_ARTIFACTS = [
    "literature/literature_index.json",
    "literature/rag/chunks.jsonl",
    "literature/rag/rag_answers.jsonl",
    "auto_scientist/ideas.json",
    "auto_scientist/experiment_plan.json",
    "auto_scientist/latest_run.json",
    "auto_scientist/analysis.json",
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


def _read(relative_path: str) -> str:
    path = ROOT / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _missing_files(paths: list[str]) -> list[str]:
    return [path for path in paths if not (ROOT / path).exists()]


def _missing_markers(relative_path: str, markers: list[str]) -> list[str]:
    text = _read(relative_path)
    return [marker for marker in markers if marker not in text]


def _version_surface_failures() -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for relative_path, markers in VERSION_SURFACES.items():
        missing = _missing_markers(relative_path, markers)
        if missing:
            failures.append({"path": relative_path, "missing": missing})
    return failures


def _forbidden_current_version_hits() -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    roots = [
        ROOT / "README.md",
        ROOT / "CHANGELOG.md",
        ROOT / "AGENTS.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "docs",
        ROOT / "scripts",
        ROOT / "services" / "api" / "main.py",
        ROOT / "services" / "api" / "pyproject.toml",
        ROOT / "services" / "api" / "app" / "tools" / "production_scaffold.py",
        ROOT / "apps" / "web" / "package.json",
        ROOT / "apps" / "web" / "package-lock.json",
        ROOT / "apps" / "web" / "features" / "workspace" / "useWorkspaceData.ts",
        ROOT / "apps" / "web" / "lib" / "api" / "legacy.ts",
    ]
    files: list[Path] = []
    for item in roots:
        if item.is_file():
            files.append(item)
        elif item.is_dir():
            files.extend(path for path in item.rglob("*") if path.is_file() and path.suffix in {".md", ".py", ".txt"})
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        # validate_v38 intentionally names the old version markers it rejects.
        if rel == "scripts/validate_v38.py":
            continue
        for marker in FORBIDDEN_CURRENT_VERSION_MARKERS:
            if marker in text:
                # Historical archive and acceptance docs may cite old versions; product-facing docs should not.
                if rel.startswith("docs/v") or rel.startswith("docs/archive") or rel.startswith("docs/archive/"):
                    continue
                hits.append({"path": rel, "marker": marker})
    return hits


def _check_demo_report(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"checked": False, "passed": True}
    if not path.exists():
        return {"checked": True, "passed": False, "reason": f"report not found: {path}"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"checked": True, "passed": False, "reason": f"invalid JSON: {exc}"}
    missing = payload.get("missing_required_artifacts") or []
    generated = payload.get("generated_artifacts") or []
    if isinstance(generated, dict):
        generated_paths = set(generated)
    elif isinstance(generated, list):
        generated_paths = {str(item) for item in generated}
    else:
        generated_paths = set()
    missing_from_generated = [artifact for artifact in REQUIRED_DEMO_ARTIFACTS if artifact not in generated_paths and artifact in missing]
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
        "missing_from_generated": missing_from_generated,
        "missing_summary_fields": missing_summary,
        "summary": summary,
    }


def build_validation_report(demo_report: Path | None = None) -> dict[str, Any]:
    missing_files = _missing_files(REQUIRED_FILES)
    version_failures = _version_surface_failures()
    forbidden_version_hits = _forbidden_current_version_hits()
    ci_missing = _missing_markers(".github/workflows/ci.yml", CI_MARKERS)
    auto_scientist_missing = _missing_markers("services/api/app/api/auto_scientist.py", AUTOSCIENTIST_API_MARKERS)
    job_missing = _missing_markers("services/api/app/api/jobs.py", JOB_API_MARKERS)
    frontend_missing = _missing_markers("apps/web/components/AutoScientistWorkbench.tsx", FRONTEND_MARKERS)
    demo_check = _check_demo_report(demo_report)

    failures: dict[str, Any] = {
        "missing_files": missing_files,
        "version_surface_failures": version_failures,
        "forbidden_old_version_hits": forbidden_version_hits,
        "ci_markers_missing": ci_missing,
        "auto_scientist_api_markers_missing": auto_scientist_missing,
        "job_api_markers_missing": job_missing,
        "frontend_markers_missing": frontend_missing,
        "demo_report": demo_check if demo_check.get("checked") and not demo_check.get("passed") else {},
    }
    failure_count = 0
    for value in failures.values():
        if isinstance(value, list):
            failure_count += len(value)
        elif isinstance(value, dict) and value:
            failure_count += 1
    return {
        "schema_version": "researchagent.validate_v38.v1",
        "version": VERSION,
        "passed": failure_count == 0,
        "failure_count": failure_count,
        "failures": failures,
        "coverage": {
            "required_files_checked": len(REQUIRED_FILES),
            "version_surfaces_checked": len(VERSION_SURFACES),
            "ci_markers_checked": len(CI_MARKERS),
            "auto_scientist_api_markers_checked": len(AUTOSCIENTIST_API_MARKERS),
            "job_api_markers_checked": len(JOB_API_MARKERS),
            "frontend_markers_checked": len(FRONTEND_MARKERS),
            "demo_report_checked": bool(demo_report),
        },
        "limitations": [
            "validate_v38 is a release-candidate contract check; it does not replace pytest, frontend build, Playwright, Docker sandbox tests, or human scientific review.",
            "A passing demo report means expected local artifacts were generated, not that generated ideas, experiments, citations, or manuscripts are scientifically valid.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the v3.0.0-rc1 ResearchAgent release-candidate contract.")
    parser.add_argument("--demo-report", type=Path, default=None, help="Optional JSON report from scripts/run_auto_scientist_demo.py.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path for the validation report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_validation_report(args.demo_report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"validate_v38 report: {args.output}")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report.get("passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
