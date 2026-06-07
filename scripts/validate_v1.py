from __future__ import annotations

import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.services.storage_service import storage_service
from app.services.workflow_service import workflow_service
from app.tools.audit_export import export_audit_log
from app.tools.pdf_quality_report import generate_pdf_quality_report
from app.tools.readiness_report import generate_v1_readiness_report
from main import app
from scripts.seed_demo import main as seed_demo

REQUIRED_FILES = [
    "README.md",
    "scripts/export_project_zip.py",
    "scripts/start_local_dev.py",
    "scripts/reset_demo.py",
    "scripts/validate_v1.py",
    "services/api/app/tools/project_export.py",
    "services/api/app/api/export.py",
    "services/api/tests/test_v1_project_export.py",
    "services/api/tests/test_v1_release_readiness.py",
    "services/api/tests/test_v1_no_secret_export.py",
    "apps/web/components/ProjectExportPanel.tsx",
    "apps/web/components/ReleaseReadinessPanel.tsx",
    "apps/web/components/LocalMVPOverviewPanel.tsx",
    "apps/web/e2e/v1-local-mvp.spec.ts",
    "docs/user_guide.md",
    "docs/demo_walkthrough.md",
    "docs/local_mvp_limitations.md",
    "docs/github_release_checklist.md",
    "docs/v1.0_acceptance_report.md",
    "docs/github_upload_status.md",
]
REQUIRED_ZIP_ENTRIES = [
    "README_EXPORT.md",
    "manuscript/draft.md",
    "provenance/evidence.json",
    "reviews/review_report.json",
    "trust/trust_summary.json",
    "trust/v1_readiness_report.json",
    "analysis/result_summary.json",
    "figures/figure_provenance.json",
    "literature/literature_index.json",
    "literature/pdf_quality_report.json",
    "audit/exports/audit_export_001.json",
    "runs/run_history.json",
]
FORBIDDEN_ZIP_PARTS = {
    ".env",
    ".runtime",
    "__pycache__",
    ".pytest_cache",
    ".next",
    "node_modules",
    "test-results",
    "playwright-report",
}
SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"OPENAI_API_KEY\s*[:=]", re.IGNORECASE),
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY"),
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_quietly(func) -> object:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        return func()


def run_command(label: str, command: list[str], cwd: Path) -> None:
    print(f"[validate_v1] {label}...", flush=True)
    env = os.environ.copy()
    env.setdefault("NODE_OPTIONS", "--max-old-space-size=8192 --max-semi-space-size=512")
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


def reset_demo_project_storage() -> None:
    project_dir = storage_service.project_dir("demo_project").resolve()
    expected_dir = (ROOT / "projects" / "demo_project").resolve()
    assert_true(project_dir == expected_dir, "refuse to reset unexpected demo project path")
    if project_dir.exists():
        shutil.rmtree(project_dir)


def assert_release_commands() -> None:
    npm_executable = shutil.which("npm") or shutil.which("npm.cmd")
    npx_executable = shutil.which("npx") or shutil.which("npx.cmd")
    assert_true(npm_executable is not None, "npm executable must be available")
    assert_true(npx_executable is not None, "npx executable must be available")
    run_command("Python compileall", [sys.executable, "-m", "compileall", "services/api", "scripts"], ROOT)
    run_command("backend pytest", [sys.executable, "-m", "pytest", "services/api/tests"], ROOT)
    run_command("frontend typecheck", [npm_executable, "run", "typecheck"], ROOT / "apps" / "web")
    run_command("frontend build", [npm_executable, "run", "build"], ROOT / "apps" / "web")
    run_command("frontend audit", [npm_executable, "audit"], ROOT / "apps" / "web")
    run_command("frontend Playwright", [npx_executable, "playwright", "test"], ROOT / "apps" / "web")


def assert_files_and_docs() -> None:
    for relative_path in REQUIRED_FILES:
        assert_true((ROOT / relative_path).exists(), f"{relative_path} must exist")

    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    for marker in ["ResearchAgent v1.0", "Local MVP", "python scripts/validate_v1.py"]:
        assert_true(marker in readme_text, f"README must include {marker}")

    gitignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for marker in [".env", ".env.*", "node_modules/", ".runtime/", "projects/*/exports/"]:
        assert_true(marker in gitignore_text, f".gitignore must include {marker}")

    github_status = (ROOT / "docs" / "github_upload_status.md").read_text(encoding="utf-8")
    assert_true("GitHub" in github_status, "github_upload_status.md must describe GitHub status")


def assert_demo_workflow() -> None:
    run_quietly(seed_demo)
    response = run_quietly(lambda: workflow_service.run_workflow("demo_project"))
    assert_true(response.workflow_status == "completed", "demo workflow must complete")
    project_dir = storage_service.project_dir("demo_project")
    run_quietly(lambda: generate_pdf_quality_report(project_dir, "demo_project"))
    run_quietly(lambda: generate_v1_readiness_report(project_dir, "demo_project"))
    run_quietly(lambda: export_audit_log(project_dir, "demo_project"))


def assert_zip_safety(relative_path: str) -> None:
    project_dir = storage_service.project_dir("demo_project")
    zip_path = project_dir / relative_path
    assert_true(zip_path.exists(), "project zip must exist")
    assert_true(project_dir.resolve() in zip_path.resolve().parents, "zip must stay inside project")
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        for required in REQUIRED_ZIP_ENTRIES:
            assert_true(required in names, f"zip must include {required}")
        for name in names:
            parts = set(Path(name).parts)
            assert_true(not name.startswith("/") and not re.search(r"^[A-Za-z]:", name), f"absolute zip path rejected: {name}")
            assert_true(".." not in parts, f"path traversal rejected: {name}")
            assert_true(not (FORBIDDEN_ZIP_PARTS & {part.lower() for part in parts}), f"forbidden path in zip: {name}")
            if Path(name).suffix.lower() in {".json", ".jsonl", ".md", ".txt", ".csv", ".svg", ".log"}:
                text = archive.read(name).decode("utf-8", errors="replace")
                assert_true(not any(pattern.search(text) for pattern in SECRET_PATTERNS), f"secret pattern in zip entry: {name}")
                assert_true(not re.search(r"[A-Za-z]:[\\/]", text), f"absolute Windows path in zip entry: {name}")


def assert_export_api() -> None:
    client = TestClient(app)
    missing = client.get("/api/projects/missing_project/export/zip")
    assert_true(missing.status_code == 404, "missing project export GET must return 404")

    response = client.post("/api/projects/demo_project/export/zip")
    assert_true(response.status_code == 200, "project zip export POST must return 200")
    payload = response.json()
    assert_true(payload["available"] is True, "project zip export must be available")
    assert_true(payload["relative_path"].startswith("exports/"), "project zip must use exports/ relative path")
    assert_true(payload["relative_path"].endswith(".zip"), "project export path must be zip")
    assert_zip_safety(payload["relative_path"])

    latest = client.get("/api/projects/demo_project/export/zip")
    assert_true(latest.status_code == 200, "project zip export GET must return 200")
    latest_payload = latest.json()
    assert_true(latest_payload["available"] is True, "latest export must be available")
    assert_true(latest_payload["relative_path"] == payload["relative_path"], "GET must return latest export path")


def assert_frontend_markers() -> None:
    frontend_files = [
        ROOT / "apps" / "web" / "app" / "page.tsx",
        ROOT / "apps" / "web" / "components" / "LocalMVPOverviewPanel.tsx",
        ROOT / "apps" / "web" / "components" / "ProjectExportPanel.tsx",
        ROOT / "apps" / "web" / "components" / "ReleaseReadinessPanel.tsx",
    ]
    page_text = "\n".join(path.read_text(encoding="utf-8") for path in frontend_files)
    for marker in [
        "Local MVP Overview",
        "Project Export",
        "Release Readiness",
        "Overview",
        "Manuscript",
        "Evidence",
        "Literature",
        "Analysis",
        "Audit-Export",
    ]:
        assert_true(marker in page_text, f"dashboard must include {marker}")
    api_text = (ROOT / "apps" / "web" / "lib" / "api.ts").read_text(encoding="utf-8")
    for marker in ["createProjectExport", "getProjectExport", "mockProjectExport"]:
        assert_true(marker in api_text, f"frontend API must include {marker}")


def main() -> None:
    assert_release_commands()
    reset_demo_project_storage()
    assert_demo_workflow()
    assert_files_and_docs()
    assert_export_api()
    assert_frontend_markers()
    print("ResearchAgent v1.0 Local MVP validation passed.")


if __name__ == "__main__":
    main()
