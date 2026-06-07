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
    "services/api/app/tools/statistical_assistant.py",
    "services/api/tests/test_v14_statistical_assistant.py",
    "services/api/tests/test_v14_no_inference_claims.py",
    "services/api/tests/test_v14_no_network_required.py",
    "apps/web/components/StatisticalAssistantPanel.tsx",
    "apps/web/e2e/v14-statistical-assistant.spec.ts",
    "docs/v1.4_acceptance_criteria.md",
    "docs/v1.4_acceptance_report.md",
]

REQUIRED_DEMO_FILES = [
    "analysis/result_summary.json",
    "analysis/processed_data.csv",
    "analysis/statistical_assistant_report.json",
    "analysis/statistical_assistant_notes.md",
]

SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"OPENAI_API_KEY\s*[:=]", re.IGNORECASE),
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY"),
    re.compile(r"(^|[\s\"'`(])[A-Za-z]:[\\/][^\s\"')]+"),
]

FORBIDDEN_POSITIVE_CLAIMS = [
    "statistically significant",
    "significant difference",
    "caused by",
    "causal effect",
    "causation",
    "proves",
    "confirmed hypothesis",
    "is peer-review-ready",
    "are peer-review-ready",
    "is production-ready",
    "are production-ready",
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_command(label: str, command: list[str], cwd: Path) -> None:
    print(f"[validate_v14] {label}...", flush=True)
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
    run_command("v1.4 demo", [sys.executable, "scripts/run_demo.py"], ROOT)
    for relative_path in REQUIRED_DEMO_FILES:
        assert_true(project_file(relative_path).exists(), f"demo output missing: {relative_path}")

    report = read_json("analysis/statistical_assistant_report.json")
    assert_true(report["report_id"] == "statistical_assistant_001", "report_id must be stable")
    assert_true(report["dataset"]["row_count"] > 0, "report must include row_count")
    assert_true(report["descriptive_cards"], "report must include descriptive cards")
    assert_true(report["variable_roles"], "report must include variable role suggestions")
    assert_true(report["method_suggestions"], "report must include method suggestions")
    assert_true(
        report["source_files"]["summary"] == "analysis/result_summary.json",
        "report must use relative summary path",
    )
    assert_true(
        report["source_files"]["processed_data"] == "analysis/processed_data.csv",
        "report must use relative processed data path",
    )
    combined = json.dumps(report, ensure_ascii=False).lower()
    for marker in ["does not generate p-values", "does not perform causal inference"]:
        assert_true(marker in combined, f"report guardrails must include {marker}")
    for marker in FORBIDDEN_POSITIVE_CLAIMS:
        assert_true(marker not in combined, f"report must not contain positive claim marker: {marker}")
    assert_true(str(storage_service.project_dir("demo_project")) not in combined, "report must not leak absolute path")

    notes = project_file("analysis/statistical_assistant_notes.md").read_text(encoding="utf-8").lower()
    assert_true("statistical assistant notes" in notes, "notes markdown must be generated")
    assert_true("p-values" in notes, "notes must include p-value guardrail")


def assert_api_contracts() -> None:
    client = TestClient(app)
    generated = client.post("/api/projects/demo_project/analysis/statistical-assistant/generate")
    assert_true(generated.status_code == 200, "statistical assistant generate API must return 200")
    assert_true(
        generated.json()["relative_path"] == "analysis/statistical_assistant_report.json",
        "generate API must return relative_path",
    )

    fetched = client.get("/api/projects/demo_project/analysis/statistical-assistant")
    assert_true(fetched.status_code == 200, "statistical assistant GET API must return 200")
    assert_true(fetched.json()["report_id"] == "statistical_assistant_001", "GET API must return report")

    missing = client.get("/api/projects/not_existing/analysis/statistical-assistant")
    assert_true(missing.status_code == 404, "missing project must return 404")


def assert_frontend_markers() -> None:
    page_text = (ROOT / "apps" / "web" / "app" / "page.tsx").read_text(encoding="utf-8")
    api_text = (ROOT / "apps" / "web" / "lib" / "api.ts").read_text(encoding="utf-8")
    type_text = (ROOT / "apps" / "web" / "lib" / "types.ts").read_text(encoding="utf-8")
    panel_text = (ROOT / "apps" / "web" / "components" / "StatisticalAssistantPanel.tsx").read_text(
        encoding="utf-8"
    )
    for marker in [
        "Statistical Assistant",
        "handleOpenStatisticalAssistant",
        "handleGenerateStatisticalAssistant",
    ]:
        assert_true(marker in page_text or marker in panel_text, f"frontend must include {marker}")
    for marker in ["getStatisticalAssistant", "generateStatisticalAssistant", "mockStatisticalAssistantReport"]:
        assert_true(marker in api_text, f"frontend API must include {marker}")
    assert_true("StatisticalAssistantReport" in type_text, "frontend types must include StatisticalAssistantReport")


def assert_docs_and_safety_markers() -> None:
    combined = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in [
            "README.md",
            "AGENTS.md",
            "docs/user_guide.md",
            "docs/local_mvp_limitations.md",
            "docs/v1.4_acceptance_criteria.md",
            "docs/v1.4_acceptance_report.md",
        ]
    )
    for marker in [
        "ResearchAgent v1.4",
        "Statistical Assistant",
        "statistical_assistant_report.json",
        "descriptive",
        "does not generate p-values",
        "does not perform causal inference",
    ]:
        assert_true(marker in combined, f"docs must include {marker}")
    for pattern in SECRET_PATTERNS:
        assert_true(not pattern.search(combined), "docs must not contain secrets or absolute local paths")


def main() -> None:
    run_command("v1.3 validation", [sys.executable, "scripts/validate_v13.py"], ROOT)
    assert_files_exist()
    assert_demo_outputs()
    assert_api_contracts()
    assert_frontend_markers()
    assert_docs_and_safety_markers()
    print("ResearchAgent v1.4 validation passed.")


if __name__ == "__main__":
    main()
