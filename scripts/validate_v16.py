from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "apps/web/components/UXConsolidationPanel.tsx",
    "apps/web/e2e/v16-ux-consolidation.spec.ts",
    "services/api/tests/test_v16_ux_static_contract.py",
    "docs/v1.6_acceptance_criteria.md",
    "docs/v1.6_acceptance_report.md",
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
    print(f"[validate_v16] {label}...", flush=True)
    env = os.environ.copy()
    env.setdefault("LLM_MODE", "mock")
    env.setdefault("LLM_API_KEY", "")
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


def assert_frontend_markers() -> None:
    panel_text = (ROOT / "apps/web/components/UXConsolidationPanel.tsx").read_text(
        encoding="utf-8"
    )
    page_text = (ROOT / "apps/web/app/page.tsx").read_text(encoding="utf-8")
    test_text = (ROOT / "apps/web/e2e/v16-ux-consolidation.spec.ts").read_text(
        encoding="utf-8"
    )

    for marker in [
        "Workspace Readiness",
        "Mock fallback active",
        "Demo remains usable without API or network",
        "Open Global Trust",
        "Review RAG Quality",
        "Open Statistical Assistant",
        "Open Workspace Export",
        "v1.6 UX consolidation",
    ]:
        assert_true(marker in panel_text or marker in test_text, f"v1.6 UI must include {marker}")

    assert_true("UXConsolidationPanel" in page_text, "dashboard must render UXConsolidationPanel")
    assert_true("dangerouslySetInnerHTML" not in panel_text, "v1.6 panel must not render raw HTML")
    assert_true("fetch(" not in panel_text, "v1.6 panel must not add direct network fetches")


def assert_docs_and_guardrails() -> None:
    combined = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in [
            "README.md",
            "AGENTS.md",
            "docs/user_guide.md",
            "docs/local_mvp_limitations.md",
            "docs/v1.6_acceptance_criteria.md",
            "docs/v1.6_acceptance_report.md",
        ]
    )
    for marker in [
        "ResearchAgent v1.6",
        "UX consolidation",
        "Workspace Readiness",
        "mock fallback",
        "python scripts/validate_v16.py",
    ]:
        assert_true(marker in combined, f"docs must include {marker}")
    for pattern in SECRET_PATTERNS:
        assert_true(not pattern.search(combined), "v1.6 docs must not contain secrets or local paths")
    lower = combined.lower()
    for marker in FORBIDDEN_POSITIVE_CLAIMS:
        assert_true(marker not in lower, f"docs must not contain positive claim marker: {marker}")


def main() -> None:
    run_command("v1.5 validation", [sys.executable, "scripts/validate_v15.py"], ROOT)
    run_command(
        "v1.6 static contract tests",
        [sys.executable, "-m", "pytest", "services/api/tests/test_v16_ux_static_contract.py"],
        ROOT,
    )
    assert_files_exist()
    assert_frontend_markers()
    assert_docs_and_guardrails()
    print("ResearchAgent v1.6 validation passed.")


if __name__ == "__main__":
    main()
