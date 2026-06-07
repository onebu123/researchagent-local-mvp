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
    "services/api/app/tools/reference_match_score.py",
    "services/api/app/tools/reference_verification.py",
    "services/api/app/tools/reference_approval.py",
    "services/api/app/tools/citation_grounding.py",
    "services/api/app/tools/manuscript_references.py",
    "services/api/tests/test_v12_reference_match_score.py",
    "services/api/tests/test_v12_reference_verification.py",
    "services/api/tests/test_v12_reference_approval.py",
    "services/api/tests/test_v12_citation_grounding.py",
    "services/api/tests/test_v12_manuscript_references.py",
    "services/api/tests/test_v12_bibtex_upgrade.py",
    "services/api/tests/test_v12_no_auto_verify.py",
    "services/api/tests/test_v12_no_network_required.py",
    "apps/web/components/ReferenceVerificationPanel.tsx",
    "apps/web/components/ReferenceApprovalPanel.tsx",
    "apps/web/components/CitationGroundingPanel.tsx",
    "apps/web/components/VerifiedReferencesPanel.tsx",
    "apps/web/e2e/v12-reference-verification.spec.ts",
    "docs/v1.2_acceptance_criteria.md",
    "docs/v1.2_acceptance_report.md",
]

REQUIRED_DEMO_FILES = [
    "literature/reference_verification/reference_verification_results.jsonl",
    "literature/reference_verification/reference_verification_summary.json",
    "literature/reference_approvals.jsonl",
    "literature/reference_approval_summary.json",
    "manuscript/references_status.json",
    "manuscript/references_section_preview.md",
    "provenance/citation_grounding_report.json",
    "literature/references.bib",
    "literature/bibtex_report.json",
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
    print(f"[validate_v12] {label}...", flush=True)
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


def assert_demo_outputs_and_no_auto_apply() -> None:
    run_command("v1.2 demo", [sys.executable, "scripts/run_demo.py"], ROOT)
    project_dir = storage_service.project_dir("demo_project")
    for relative_path in REQUIRED_DEMO_FILES:
        assert_true((project_dir / relative_path).exists(), f"demo output missing: {relative_path}")

    index = read_json("literature/literature_index.json")
    assert_true(isinstance(index, list), "literature_index.json must be a list")
    assert_true(
        not any(entry.get("reference_verification_status") == "approved" for entry in index if isinstance(entry, dict)),
        "demo reference verification must not auto apply approval to literature_index.json",
    )
    assert_true(
        not any(entry.get("doi") for entry in index if isinstance(entry, dict) and entry.get("metadata_status") == "placeholder"),
        "demo placeholder literature must not receive fabricated DOI",
    )

    approvals = read_jsonl("literature/reference_approvals.jsonl")
    assert_true(approvals, "demo must include reference approval decision log")
    assert_true(
        all(not approval.get("applied_to_literature_index") for approval in approvals),
        "demo approval workflow must default to no apply",
    )

    bibtex_report = read_json("literature/bibtex_report.json")
    assert_true(isinstance(bibtex_report, dict), "bibtex report must be a dict")
    assert_true(bibtex_report["formal_entries"] == 0, "demo must not create formal BibTeX from unapproved records")
    bibtex = (project_dir / "literature" / "references.bib").read_text(encoding="utf-8")
    assert_true("@misc{" not in bibtex, "unapproved demo references must be comments only")

    references_status = read_json("manuscript/references_status.json")
    assert_true(isinstance(references_status, dict), "references status must be a dict")
    assert_true(
        len(references_status["verified_references"]) == 0,
        "demo must not create formal manuscript references from unapproved records",
    )


def assert_api_contracts() -> None:
    client = TestClient(app)
    project_dir = storage_service.project_dir("demo_project")
    index_path = project_dir / "literature" / "literature_index.json"
    before_index = index_path.read_text(encoding="utf-8")
    before_draft = (project_dir / "manuscript" / "draft.md").read_text(encoding="utf-8")

    run_response = client.post(
        "/api/projects/demo_project/literature/reference-verification/run",
        json={"provider": "mock_fixture"},
    )
    assert_true(run_response.status_code == 200, "reference verification run API must return 200")
    run_payload = run_response.json()
    assert_true(run_payload["literature_index_modified"] is False, "verification run must not modify index")
    assert_true(index_path.read_text(encoding="utf-8") == before_index, "verification run must leave index unchanged")

    verification_id = run_payload["results"][0]["verification_id"]
    approval_response = client.post(
        f"/api/projects/demo_project/literature/reference-verification/{verification_id}/approval",
        json={
            "decision": "approved",
            "reason": "validation records approval only",
            "apply_to_literature_index": False,
        },
    )
    assert_true(approval_response.status_code == 200, "reference approval API must return 200")
    assert_true(
        approval_response.json()["literature_index_modified"] is False,
        "default approval API must not modify index",
    )
    assert_true(index_path.read_text(encoding="utf-8") == before_index, "approval without apply must leave index unchanged")

    for path in [
        "/api/projects/demo_project/literature/reference-verification/results",
        "/api/projects/demo_project/literature/reference-verification/summary",
        "/api/projects/demo_project/literature/reference-approvals",
        "/api/projects/demo_project/literature/reference-approval-summary",
        "/api/projects/demo_project/provenance/citation-grounding",
        "/api/projects/demo_project/manuscript/references/status",
        "/api/projects/demo_project/manuscript/references/preview",
        "/api/projects/demo_project/literature/bibtex",
    ]:
        response = client.get(path)
        assert_true(response.status_code == 200, f"{path} must return 200")

    assert_true(
        (project_dir / "manuscript" / "draft.md").read_text(encoding="utf-8") == before_draft,
        "references preview/status APIs must not overwrite draft.md",
    )


def assert_frontend_markers() -> None:
    page_text = (ROOT / "apps" / "web" / "app" / "page.tsx").read_text(encoding="utf-8")
    api_text = (ROOT / "apps" / "web" / "lib" / "api.ts").read_text(encoding="utf-8")
    for marker in [
        "Run Reference Verification",
        "Verification Results",
        "Approval Workflow",
        "Verified References",
        "Citation Grounding",
        "BibTeX Status",
    ]:
        assert_true(marker in page_text, f"dashboard must include {marker}")
    for marker in [
        "runReferenceVerification",
        "approveReferenceVerification",
        "getCitationGrounding",
        "getManuscriptReferencesStatus",
        "mockReferenceVerificationResults",
        "mockCitationGrounding",
    ]:
        assert_true(marker in api_text, f"frontend API must include {marker}")


def assert_docs_and_safety_markers() -> None:
    combined = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in [
            "README.md",
            "AGENTS.md",
            "docs/user_guide.md",
            "docs/local_mvp_limitations.md",
            "docs/v1.2_acceptance_criteria.md",
            "docs/v1.2_acceptance_report.md",
        ]
    )
    for marker in [
        "ResearchAgent v1.2",
        "Reference Verification",
        "apply_to_literature_index=true",
        "citation_grounding_report.json",
        "reference_verification_status=approved",
    ]:
        assert_true(marker in combined, f"docs must include {marker}")
    for pattern in SECRET_PATTERNS:
        assert_true(not pattern.search(combined), "docs must not contain secrets or absolute local paths")


def main() -> None:
    run_command("v1.1 validation", [sys.executable, "scripts/validate_v11.py"], ROOT)
    assert_files_exist()
    assert_demo_outputs_and_no_auto_apply()
    assert_api_contracts()
    assert_frontend_markers()
    assert_docs_and_safety_markers()
    print("ResearchAgent v1.2 validation passed.")


if __name__ == "__main__":
    main()
