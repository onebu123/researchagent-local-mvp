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
    "services/api/app/tools/rag_quality.py",
    "services/api/tests/test_v13_hybrid_retrieval.py",
    "services/api/tests/test_v13_rag_quality.py",
    "services/api/tests/test_v13_no_network_required.py",
    "apps/web/components/RAGQualityPanel.tsx",
    "apps/web/e2e/v13-rag-quality.spec.ts",
    "docs/v1.3_acceptance_criteria.md",
    "docs/v1.3_acceptance_report.md",
]

REQUIRED_DEMO_FILES = [
    "literature/rag/chunks.jsonl",
    "literature/rag/rag_index.json",
    "literature/rag/rag_answers.jsonl",
    "literature/rag/chunk_quality_report.json",
    "literature/rag/retrieval_eval_set.json",
    "literature/rag/retrieval_eval_report.json",
]

SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"OPENAI_API_KEY\s*[:=]", re.IGNORECASE),
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY"),
    re.compile(r"(^|[\s\"'`(])[A-Za-z]:[\\/][^\s\"')]+"),
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_command(label: str, command: list[str], cwd: Path) -> None:
    print(f"[validate_v13] {label}...", flush=True)
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


def read_json(relative_path: str) -> object:
    project_dir = storage_service.project_dir("demo_project")
    return json.loads((project_dir / relative_path).read_text(encoding="utf-8"))


def read_jsonl(relative_path: str) -> list[dict]:
    project_dir = storage_service.project_dir("demo_project")
    path = project_dir / relative_path
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def assert_files_exist() -> None:
    for relative_path in REQUIRED_FILES:
        assert_true((ROOT / relative_path).exists(), f"{relative_path} must exist")


def assert_demo_outputs() -> None:
    run_command("v1.3 demo", [sys.executable, "scripts/run_demo.py"], ROOT)
    project_dir = storage_service.project_dir("demo_project")
    for relative_path in REQUIRED_DEMO_FILES:
        assert_true((project_dir / relative_path).exists(), f"demo output missing: {relative_path}")

    rag_index = read_json("literature/rag/rag_index.json")
    assert_true(isinstance(rag_index, dict), "rag_index.json must be an object")
    assert_true(rag_index["retrieval_mode"] == "local_hybrid", "RAG index must use local_hybrid mode")
    assert_true("local_keyword" in rag_index["supported_retrieval_modes"], "RAG index must retain keyword fallback")

    answers = read_jsonl("literature/rag/rag_answers.jsonl")
    assert_true(answers, "rag_answers.jsonl must include an answer")
    latest = answers[-1]
    assert_true(latest["retrieval"]["retrieval_mode"] == "local_hybrid", "RAG answer must record hybrid retrieval")
    passages = latest.get("source_passages") or []
    assert_true(bool(passages), "RAG answer must include source passages")
    assert_true("score_breakdown" in passages[0], "source passage must include score_breakdown")

    quality = read_json("literature/rag/chunk_quality_report.json")
    assert_true(isinstance(quality, dict), "chunk quality report must be a dict")
    assert_true(quality["summary"]["total_chunks"] > 0, "chunk quality report must count chunks")
    assert_true(
        all(0 <= item["quality_score"] <= 1 for item in quality["items"]),
        "chunk quality scores must stay in [0, 1]",
    )

    evaluation = read_json("literature/rag/retrieval_eval_report.json")
    assert_true(isinstance(evaluation, dict), "retrieval eval report must be a dict")
    assert_true(evaluation["metrics"]["total_cases"] > 0, "retrieval eval must include local cases")
    assert_true(0 <= evaluation["metrics"]["hit_at_3"] <= 1, "hit_at_3 must stay in [0, 1]")


def assert_api_contracts() -> None:
    client = TestClient(app)
    build = client.post("/api/projects/demo_project/literature/rag/build")
    assert_true(build.status_code == 200, "RAG build API must return 200")
    assert_true(build.json()["retrieval_mode"] == "local_hybrid", "RAG build API must return local_hybrid")

    ask = client.post(
        "/api/projects/demo_project/literature/rag/ask",
        json={"question": "efficiency stability", "top_k": 2, "retrieval_mode": "local_hybrid"},
    )
    assert_true(ask.status_code == 200, "RAG ask API must return 200")
    assert_true(ask.json()["retrieval"]["retrieval_mode"] == "local_hybrid", "RAG ask must record retrieval mode")

    invalid = client.post(
        "/api/projects/demo_project/literature/rag/ask",
        json={"question": "efficiency", "top_k": 2, "retrieval_mode": "external_vector"},
    )
    assert_true(invalid.status_code == 422, "invalid retrieval_mode must return 422")

    for method, path in [
        ("get", "/api/projects/demo_project/literature/rag/quality"),
        ("get", "/api/projects/demo_project/literature/rag/eval-set"),
        ("post", "/api/projects/demo_project/literature/rag/evaluate"),
        ("get", "/api/projects/demo_project/literature/rag/evaluation"),
    ]:
        response = getattr(client, method)(path)
        assert_true(response.status_code == 200, f"{path} must return 200")


def assert_frontend_markers() -> None:
    page_text = (ROOT / "apps" / "web" / "app" / "page.tsx").read_text(encoding="utf-8")
    api_text = (ROOT / "apps" / "web" / "lib" / "api.ts").read_text(encoding="utf-8")
    panel_text = (ROOT / "apps" / "web" / "components" / "RAGQualityPanel.tsx").read_text(encoding="utf-8")
    for marker in ["RAG Quality", "handleOpenRAGQuality", "local_hybrid"]:
        assert_true(marker in page_text or marker in panel_text or marker in api_text, f"frontend must include {marker}")
    for marker in ["getRAGChunkQuality", "evaluateRAGRetrieval", "mockRAGRetrievalEvaluation"]:
        assert_true(marker in api_text, f"frontend API must include {marker}")


def assert_docs_and_safety_markers() -> None:
    combined = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in [
            "README.md",
            "AGENTS.md",
            "docs/user_guide.md",
            "docs/local_mvp_limitations.md",
            "docs/v1.3_acceptance_criteria.md",
            "docs/v1.3_acceptance_report.md",
        ]
    )
    for marker in [
        "ResearchAgent v1.3",
        "RAG Quality",
        "local_hybrid",
        "chunk_quality_report.json",
        "retrieval_eval_report.json",
    ]:
        assert_true(marker in combined, f"docs must include {marker}")
    for pattern in SECRET_PATTERNS:
        assert_true(not pattern.search(combined), "docs must not contain secrets or absolute local paths")


def main() -> None:
    run_command("v1.2 validation", [sys.executable, "scripts/validate_v12.py"], ROOT)
    assert_files_exist()
    assert_demo_outputs()
    assert_api_contracts()
    assert_frontend_markers()
    assert_docs_and_safety_markers()
    print("ResearchAgent v1.3 validation passed.")


if __name__ == "__main__":
    main()
