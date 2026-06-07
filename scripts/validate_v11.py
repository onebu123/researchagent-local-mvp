from __future__ import annotations

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
    "services/api/app/tools/llm_client.py",
    "services/api/app/tools/llm_call_log.py",
    "services/api/app/tools/prompt_registry.py",
    "services/api/app/tools/literature_rag.py",
    "services/api/app/tools/source_passage_evidence.py",
    "services/api/app/tools/literature_metadata_lookup.py",
    "services/api/app/tools/bibtex_generator.py",
    "services/api/app/tools/citation_support_checker.py",
    "services/api/app/prompts/literature_answer_v1.md",
    "services/api/app/prompts/citation_support_v1.md",
    "services/api/app/prompts/metadata_extraction_v1.md",
    "services/api/app/prompts/bibtex_generation_v1.md",
    "services/api/tests/test_v11_llm_client.py",
    "services/api/tests/test_v11_llm_call_log.py",
    "services/api/tests/test_v11_prompt_registry.py",
    "services/api/tests/test_v11_literature_rag.py",
    "services/api/tests/test_v11_source_passage_evidence.py",
    "services/api/tests/test_v11_metadata_lookup.py",
    "services/api/tests/test_v11_bibtex.py",
    "services/api/tests/test_v11_citation_support.py",
    "services/api/tests/test_v11_no_secret_logging.py",
    "apps/web/components/LLMSettingsPanel.tsx",
    "apps/web/components/LLMCallLogPanel.tsx",
    "apps/web/components/LiteratureRAGPanel.tsx",
    "apps/web/components/SourcePassageEvidencePanel.tsx",
    "apps/web/components/LiteratureMetadataLookupPanel.tsx",
    "apps/web/components/BibTeXPanel.tsx",
    "apps/web/components/CitationSupportPanel.tsx",
    "apps/web/e2e/v11-literature-intelligence.spec.ts",
    "docs/v1.1_acceptance_criteria.md",
    "docs/v1.1_acceptance_report.md",
]
REQUIRED_DEMO_FILES = [
    "literature/rag/chunks.jsonl",
    "literature/rag/rag_index.json",
    "literature/rag/rag_answers.jsonl",
    "provenance/source_passage_evidence.json",
    "literature/metadata_lookup_results.jsonl",
    "literature/metadata_lookup_summary.json",
    "literature/references.bib",
    "literature/bibtex_report.json",
    "provenance/citation_support_report.json",
    "llm/llm_calls.jsonl",
]
SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"LLM_API_KEY\s*[:=]", re.IGNORECASE),
    re.compile(r"[A-Za-z]:[\\/][^\s\"']+"),
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_command(label: str, command: list[str], cwd: Path) -> None:
    print(f"[validate_v11] {label}...", flush=True)
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


def assert_files_exist() -> None:
    for relative_path in REQUIRED_FILES:
        assert_true((ROOT / relative_path).exists(), f"{relative_path} must exist")


def assert_demo_outputs() -> None:
    run_command("v1.1 demo", [sys.executable, "scripts/run_demo.py"], ROOT)
    project_dir = storage_service.project_dir("demo_project")
    for relative_path in REQUIRED_DEMO_FILES:
        assert_true((project_dir / relative_path).exists(), f"demo output missing: {relative_path}")
    llm_log = (project_dir / "llm" / "llm_calls.jsonl").read_text(encoding="utf-8")
    for pattern in SECRET_PATTERNS:
        assert_true(not pattern.search(llm_log), "LLM call log must not contain secrets or absolute paths")


def assert_api_contracts() -> None:
    client = TestClient(app)
    status = client.get("/api/system/llm/status")
    assert_true(status.status_code == 200, "LLM status API must return 200")
    assert_true("api_key" not in status.text.lower() or "api_key_configured" in status.text, "status must not expose an API key")

    prompts = client.get("/api/system/prompts")
    assert_true(prompts.status_code == 200, "prompt registry API must return 200")
    assert_true(prompts.json()["count"] >= 4, "prompt registry must list at least 4 prompts")

    ask = client.post(
        "/api/projects/demo_project/literature/rag/ask",
        json={"question": "What does the demo literature mention about efficiency?", "top_k": 3},
    )
    assert_true(ask.status_code == 200, "RAG ask API must return 200")
    assert_true("source_passages" in ask.json(), "RAG answer must include source_passages")

    for path in [
        "/api/projects/demo_project/llm/calls",
        "/api/projects/demo_project/literature/rag/chunks",
        "/api/projects/demo_project/literature/rag/answers",
        "/api/projects/demo_project/provenance/source-passage-evidence",
        "/api/projects/demo_project/literature/metadata-lookup/results",
        "/api/projects/demo_project/literature/bibtex",
        "/api/projects/demo_project/provenance/citation-support",
    ]:
        response = client.get(path)
        assert_true(response.status_code == 200, f"{path} must return 200")


def assert_frontend_markers() -> None:
    page_text = (ROOT / "apps" / "web" / "app" / "page.tsx").read_text(encoding="utf-8")
    api_text = (ROOT / "apps" / "web" / "lib" / "api.ts").read_text(encoding="utf-8")
    for marker in [
        "Literature Intelligence",
        "LLM Settings",
        "Prompt Registry",
        "Literature RAG",
        "Source Passage Evidence",
        "Metadata Lookup",
        "BibTeX",
        "Citation Support",
    ]:
        assert_true(marker in page_text, f"dashboard must include {marker}")
    for marker in [
        "getLLMStatus",
        "testLLM",
        "buildLiteratureRAG",
        "askLiteratureRAG",
        "runMetadataLookup",
        "generateBibTeX",
        "getCitationSupport",
    ]:
        assert_true(marker in api_text, f"frontend API must include {marker}")


def main() -> None:
    run_command("v1.0 validation", [sys.executable, "scripts/validate_v1.py"], ROOT)
    assert_files_exist()
    assert_demo_outputs()
    assert_api_contracts()
    assert_frontend_markers()
    print("ResearchAgent v1.1 literature intelligence validation passed.")


if __name__ == "__main__":
    main()
