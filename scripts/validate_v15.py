from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.services.storage_service import storage_service
from main import app


REQUIRED_FILES = [
    "services/api/app/tools/workspace_export.py",
    "services/api/tests/test_v15_workspace_export.py",
    "services/api/tests/test_v15_docx_latex_export.py",
    "services/api/tests/test_v15_no_secret_export.py",
    "services/api/tests/test_v15_no_peer_review_claims.py",
    "apps/web/components/WorkspaceExportPanel.tsx",
    "apps/web/e2e/v15-workspace-export.spec.ts",
    "docs/v1.5_acceptance_criteria.md",
    "docs/v1.5_acceptance_report.md",
]

REQUIRED_DEMO_FILES = [
    "exports/workspace/research_workspace_export.docx",
    "exports/workspace/research_workspace_export.tex",
    "exports/workspace/trust_report.md",
    "exports/workspace/trust_report.json",
    "exports/workspace/workspace_export_manifest.json",
]

SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"OPENAI_API_KEY\s*[:=]", re.IGNORECASE),
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY"),
    re.compile(r"(^|[\s\"'`(])[A-Za-z]:[\\/][^\s\"')]+"),
]

FORBIDDEN_POSITIVE_CLAIMS = [
    "is peer-review-ready",
    "are peer-review-ready",
    "peer-review ready",
    "is production-ready",
    "are production-ready",
    "production ready",
    "is compliance-ready",
    "are compliance-ready",
    "compliance ready",
    "scientifically proven",
    "statistically significant",
    "causal effect",
    "caused by",
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_command(label: str, command: list[str], cwd: Path) -> None:
    print(f"[validate_v15] {label}...", flush=True)
    env = os.environ.copy()
    env.setdefault("LLM_MODE", "mock")
    env.setdefault("LLM_API_KEY", "")
    result = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if result.returncode != 0:
        raise AssertionError(f"{label} failed with exit code {result.returncode}\n{result.stdout}")


def project_file(relative_path: str) -> Path:
    return storage_service.project_dir("demo_project") / relative_path


def read_json(relative_path: str) -> dict:
    payload = json.loads(project_file(relative_path).read_text(encoding="utf-8"))
    assert_true(isinstance(payload, dict), f"{relative_path} must contain a JSON object")
    return payload


def assert_files_exist() -> None:
    for relative_path in REQUIRED_FILES:
        assert_true((ROOT / relative_path).exists(), f"{relative_path} must exist")


def assert_demo_outputs() -> None:
    client = TestClient(app)
    response = client.post("/api/projects/demo_project/export/workspace")
    assert_true(response.status_code == 200, "workspace export API must generate successfully")
    manifest = response.json()
    assert_true(manifest["available"] is True, "workspace export must be available")
    assert_true(
        manifest["relative_path"] == "exports/workspace/workspace_export_manifest.json",
        "workspace export manifest path must be stable",
    )
    assert_true(
        manifest["safety"]["project_relative_paths_only"] is True,
        "workspace export must use project-relative paths",
    )
    assert_true(
        manifest["safety"]["secret_scan_passed"] is True,
        "workspace export text artifacts must pass secret scan",
    )

    for relative_path in REQUIRED_DEMO_FILES:
        assert_true(project_file(relative_path).exists(), f"demo output missing: {relative_path}")

    artifact_paths = {item["relative_path"] for item in manifest["artifacts"]}
    for relative_path in REQUIRED_DEMO_FILES:
        assert_true(relative_path in artifact_paths, f"manifest missing artifact: {relative_path}")

    trust = read_json("exports/workspace/trust_report.json")
    assert_true(trust["scope"] == "local_mvp_workspace_export", "trust report scope must be local")
    assert_true(
        trust["source_files"]["manuscript_draft"] == "manuscript/draft.md",
        "trust report must use relative manuscript path",
    )
    assert_true(
        trust["audit"]["hash_chain"]["valid"] is True,
        "workspace trust report must include valid audit hash chain",
    )

    latex_text = project_file("exports/workspace/research_workspace_export.tex").read_text(
        encoding="utf-8"
    )
    assert_true("\\documentclass" in latex_text, "LaTeX export must be source text")
    assert_true("demo\\_project" in latex_text, "LaTeX export must escape underscores")

    markdown = project_file("exports/workspace/trust_report.md").read_text(encoding="utf-8")
    assert_true("ResearchAgent Workspace Trust Report" in markdown, "trust markdown missing title")
    assert_true(
        "not a production compliance archive" in markdown,
        "trust markdown must include local MVP caveat",
    )


def assert_api_contracts() -> None:
    client = TestClient(app)
    latest = client.get("/api/projects/demo_project/export/workspace")
    assert_true(latest.status_code == 200, "workspace export GET API must return 200")
    assert_true(latest.json()["available"] is True, "workspace export GET must return latest manifest")

    missing = client.post("/api/projects/not_existing/export/workspace")
    assert_true(missing.status_code == 404, "missing project must return 404")


def assert_frontend_markers() -> None:
    page_text = (ROOT / "apps" / "web" / "app" / "page.tsx").read_text(encoding="utf-8")
    api_text = (ROOT / "apps" / "web" / "lib" / "api.ts").read_text(encoding="utf-8")
    type_text = (ROOT / "apps" / "web" / "lib" / "types.ts").read_text(encoding="utf-8")
    panel_text = (ROOT / "apps" / "web" / "components" / "WorkspaceExportPanel.tsx").read_text(
        encoding="utf-8"
    )
    for marker in ["Workspace Export", "handleOpenWorkspaceExport", "handleCreateWorkspaceExport"]:
        assert_true(marker in page_text or marker in panel_text, f"frontend must include {marker}")
    for marker in ["getWorkspaceExport", "createWorkspaceExport", "mockWorkspaceExport"]:
        assert_true(marker in api_text, f"frontend API must include {marker}")
    assert_true("WorkspaceExportManifest" in type_text, "frontend types must include workspace export manifest")


def assert_docs_and_safety_markers() -> None:
    combined = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in [
            "README.md",
            "AGENTS.md",
            "docs/user_guide.md",
            "docs/local_mvp_limitations.md",
            "docs/v1.5_acceptance_criteria.md",
            "docs/v1.5_acceptance_report.md",
        ]
    )
    for marker in [
        "ResearchAgent v1.5",
        "Workspace Export",
        "research_workspace_export.docx",
        "research_workspace_export.tex",
        "trust_report.json",
        "workspace_export_manifest.json",
        "local MVP",
    ]:
        assert_true(marker in combined, f"docs must include {marker}")
    for pattern in SECRET_PATTERNS:
        assert_true(not pattern.search(combined), "docs must not contain secrets or absolute local paths")
    lower = combined.lower()
    for marker in FORBIDDEN_POSITIVE_CLAIMS:
        assert_true(marker not in lower, f"docs must not contain positive claim marker: {marker}")


def assert_generated_artifact_safety() -> None:
    combined = "\n".join(
        project_file(relative_path).read_text(encoding="utf-8")
        for relative_path in [
            "exports/workspace/research_workspace_export.tex",
            "exports/workspace/trust_report.md",
            "exports/workspace/trust_report.json",
            "exports/workspace/workspace_export_manifest.json",
        ]
    )
    for pattern in SECRET_PATTERNS:
        assert_true(not pattern.search(combined), "workspace export must not leak secrets or absolute paths")
    lower = combined.lower()
    for marker in FORBIDDEN_POSITIVE_CLAIMS:
        assert_true(
            marker not in lower,
            f"workspace export must not contain positive claim marker: {marker}",
        )


def main() -> None:
    run_command("v1.4 validation", [sys.executable, "scripts/validate_v14.py"], ROOT)
    assert_files_exist()
    assert_demo_outputs()
    assert_api_contracts()
    assert_frontend_markers()
    assert_docs_and_safety_markers()
    assert_generated_artifact_safety()
    print("ResearchAgent v1.5 validation passed.")


if __name__ == "__main__":
    main()
