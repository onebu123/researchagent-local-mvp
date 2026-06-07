from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "services/api/app/tools/production_scaffold.py",
    "services/api/app/workers/research_worker.py",
    "services/api/app/workers/__init__.py",
    "services/api/tests/test_v2_production_scaffold.py",
    "services/api/tests/test_v2_static_contract.py",
    "services/api/tests/test_v2_validate_audit_fallback.py",
    "apps/web/components/ProductionScaffoldPanel.tsx",
    "apps/web/e2e/v2-production-scaffold.spec.ts",
    "services/api/Dockerfile",
    "apps/web/Dockerfile",
    ".dockerignore",
    "docs/deployment_v2.md",
    "docs/v2.0_acceptance_criteria.md",
    "docs/v2.0_acceptance_report.md",
]

SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"OPENAI_API_KEY\s*[:=]", re.IGNORECASE),
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY"),
    re.compile(r"postgresql://[^<\s]+:[^<\s]+@"),
    re.compile(r"redis://:[^<\s]+@"),
    re.compile(r"(^|[\s\"'`(])[A-Za-z]:[\\/][^\s\"')]+"),
]

FORBIDDEN_POSITIVE_CLAIMS = [
    "is peer-review-ready",
    "are peer-review-ready",
    "is production-ready",
    "are production-ready",
    "is compliance-ready",
    "are compliance-ready",
    "scientifically proven",
    "statistically significant",
    "causal effect",
    "caused by",
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_command(label: str, command: list[str], cwd: Path) -> None:
    print(f"[validate_v2] {label}...", flush=True)
    env = os.environ.copy()
    env.setdefault("LLM_MODE", "mock")
    env.setdefault("LLM_API_KEY", "")
    env.setdefault("DATABASE_BACKEND", "sqlite")
    env.setdefault("QUEUE_MODE", "inline")
    env.setdefault("AUTH_MODE", "disabled")
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


def assert_files_exist() -> None:
    for relative_path in REQUIRED_FILES:
        assert_true((ROOT / relative_path).exists(), f"{relative_path} must exist")


def assert_api_scaffold() -> None:
    system_text = (ROOT / "services/api/app/api/system.py").read_text(encoding="utf-8")
    config_text = (ROOT / "services/api/app/config.py").read_text(encoding="utf-8")
    scaffold_text = (ROOT / "services/api/app/tools/production_scaffold.py").read_text(
        encoding="utf-8"
    )
    worker_text = (ROOT / "services/api/app/workers/research_worker.py").read_text(
        encoding="utf-8"
    )

    for marker in [
        "/system/production-scaffold",
        "get_production_scaffold_report",
        "DATABASE_BACKEND",
        "QUEUE_MODE",
        "AUTH_MODE",
        "run_worker_smoke",
    ]:
        combined = "\n".join([system_text, config_text, scaffold_text, worker_text])
        assert_true(marker in combined, f"v2 API scaffold must include {marker}")

    assert_true("DATABASE_URL" not in scaffold_text, "scaffold report must not expose DATABASE_URL")
    assert_true("AUTH_SHARED_SECRET" not in scaffold_text, "scaffold report must not expose auth secret")


def assert_frontend_scaffold() -> None:
    panel_text = (ROOT / "apps/web/components/ProductionScaffoldPanel.tsx").read_text(
        encoding="utf-8"
    )
    page_text = (ROOT / "apps/web/app/page.tsx").read_text(encoding="utf-8")
    api_text = (ROOT / "apps/web/lib/api.ts").read_text(encoding="utf-8")
    test_text = (ROOT / "apps/web/e2e/v2-production-scaffold.spec.ts").read_text(
        encoding="utf-8"
    )
    combined = "\n".join([panel_text, page_text, api_text, test_text])

    for marker in [
        "Research Workspace Scaffold",
        "getProductionScaffold",
        "mockProductionScaffold",
        "python scripts/validate_v2.py",
        "v2.0 Research Workspace scaffold",
    ]:
        assert_true(marker in combined, f"v2 frontend scaffold must include {marker}")
    assert_true("dangerouslySetInnerHTML" not in panel_text, "v2 panel must not render raw HTML")
    assert_true("localStorage" not in panel_text, "v2 panel must not add localStorage state")


def assert_docs_and_docker() -> None:
    project_docs = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in [
            "README.md",
            "AGENTS.md",
            "docs/user_guide.md",
            "docs/local_mvp_limitations.md",
        ]
    )
    v2_docs = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in [
            "docs/deployment_v2.md",
            "docs/v2.0_acceptance_criteria.md",
            "docs/v2.0_acceptance_report.md",
        ]
    )
    docker = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in [
            "docker-compose.yml",
            "services/api/Dockerfile",
            "apps/web/Dockerfile",
            ".dockerignore",
            ".env.example",
        ]
    )
    combined = project_docs + "\n" + v2_docs + "\n" + docker

    for marker in [
        "ResearchAgent v2.0",
        "Research Workspace scaffold",
        "optional PostgreSQL",
        "QUEUE_MODE=inline",
        "AUTH_MODE=disabled",
        "python scripts/validate_v2.py",
        "docs/deployment_v2.md",
    ]:
        assert_true(marker in combined, f"v2 docs/docker must include {marker}")
    for pattern in SECRET_PATTERNS:
        assert_true(
            not pattern.search(v2_docs + "\n" + docker),
            "v2 docs/docker must not contain secrets or local paths",
        )
    lower = (v2_docs + "\n" + docker).lower()
    for marker in FORBIDDEN_POSITIVE_CLAIMS:
        assert_true(marker not in lower, f"v2 docs/docker must not contain positive claim marker: {marker}")


def main() -> None:
    run_command("v1.6 validation", [sys.executable, "scripts/validate_v16.py"], ROOT)
    run_command(
        "v2 scaffold tests",
        [
            sys.executable,
            "-m",
            "pytest",
            "services/api/tests/test_v2_production_scaffold.py",
            "services/api/tests/test_v2_static_contract.py",
            "services/api/tests/test_v2_validate_audit_fallback.py",
        ],
        ROOT,
    )
    run_command(
        "v2 worker smoke",
        [sys.executable, "-m", "app.workers.research_worker"],
        ROOT / "services" / "api",
    )
    assert_files_exist()
    assert_api_scaffold()
    assert_frontend_scaffold()
    assert_docs_and_docker()
    print("ResearchAgent v2.0 validation passed.")


if __name__ == "__main__":
    main()
