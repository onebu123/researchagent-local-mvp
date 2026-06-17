from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.tools import literature_rag
from app.tools import llm_client as llm_client_module
from app.tools.claim_audit import run_draft_claim_audit
from app.tools.evidence_trust_package import build_evidence_trust_package
from app.tools.human_review_queue import build_human_review_queue, record_human_review_decision
from app.tools.literature_rag import ask_literature_rag, build_literature_rag, read_rag_chunks
from app.tools.llm_client import LLMResponse
from app.tools.revision_plan import generate_evidence_revision_plan
from main import app

ROOT = Path(__file__).resolve().parents[3]


def test_page_aware_chunks_and_source_locators(demo_project_dir: Path) -> None:
    build_literature_rag(demo_project_dir, "demo_project")
    chunks = read_rag_chunks(demo_project_dir)

    assert chunks
    assert all("position_label" in chunk for chunk in chunks)
    assert all("source_locator" in chunk for chunk in chunks)
    assert all("metadata_trust_level" in chunk for chunk in chunks)
    assert all("evidence_warning_flags" in chunk for chunk in chunks)
    pdf_chunks = [chunk for chunk in chunks if chunk.get("source_type") == "pdf"]
    assert pdf_chunks
    assert {"page_start", "page_end", "page_quality_signals"} <= set(pdf_chunks[0])

    answer = ask_literature_rag(demo_project_dir, "demo_project", "efficiency stability")
    passage = answer["source_passages"][0]
    assert "source_locator" in passage
    assert "position_label" in passage
    assert "evidence_warning_flags" in passage


def test_unsupported_answer_contract_replaces_unsafe_live_output(
    demo_project_dir: Path,
    monkeypatch,
) -> None:
    class UnsafeLiveClient:
        def chat_json(self, messages, fallback, prompt_version):  # type: ignore[no-untyped-def]
            return LLMResponse(
                content=json.dumps(
                    {
                        "answer": "The result proves a statistically significant causal effect with a p-value.",
                        "unsupported_notes": [],
                        "limitations": [],
                    }
                ),
                mode="live",
                provider="fake",
                model="fake-model",
                prompt_version=prompt_version,
                status="success",
                parsed_json={
                    "answer": "The result proves a statistically significant causal effect with a p-value.",
                    "unsupported_notes": [],
                    "limitations": [],
                },
            )

    monkeypatch.setattr(llm_client_module, "llm_client", UnsafeLiveClient())
    answer = literature_rag.ask_literature_rag(
        demo_project_dir,
        "demo_project",
        "What exact p-value proves the clinical survival outcome?",
        retrieval_mode="local_hybrid_fts",
    )

    assert answer["answer_support_status"] == "unsupported"
    assert answer["source_passage_count"] == 0
    lowered = answer["answer"].lower()
    for forbidden in ["statistically significant", "causal", "p-value", "proves"]:
        assert forbidden not in lowered
    assert answer["unsupported_notes"]


def test_claim_audit_revision_queue_and_trust_package(demo_project_dir: Path) -> None:
    draft_path = demo_project_dir / "manuscript" / "draft.md"
    original_draft = draft_path.read_text(encoding="utf-8")
    manuscript = """# Results

The project literature mentions efficiency and stability in a local mock context.

The prototype proves a statistically significant survival outcome with a p-value.

# Discussion

The local evidence is limited and requires human review.
"""

    audit = run_draft_claim_audit(
        demo_project_dir,
        "demo_project",
        manuscript_text=manuscript,
        retrieval_mode="local_hybrid_fts",
    )

    statuses = [item["answer_support_status"] for item in audit["claim_audits"]]
    assert "unsupported" in statuses
    assert (demo_project_dir / "provenance" / "claim_audit.json").exists()
    assert draft_path.read_text(encoding="utf-8") == original_draft

    plan = generate_evidence_revision_plan(demo_project_dir, "demo_project")
    assert plan["human_approval_required"] is True
    assert plan["patch_suggestions"]
    assert all(item["requires_human_approval"] for item in plan["patch_suggestions"])
    assert draft_path.read_text(encoding="utf-8") == original_draft

    queue = build_human_review_queue(demo_project_dir, "demo_project")
    assert queue["summary"]["pending"] > 0
    claim_items = [item for item in queue["items"] if item["review_type"] == "claim"]
    assert claim_items
    decided = record_human_review_decision(
        demo_project_dir,
        "demo_project",
        claim_items[0]["review_id"],
        "dismissed",
        "test decision",
        source="test",
    )
    assert any(
        item["review_id"] == claim_items[0]["review_id"] and item["status"] == "dismissed"
        for item in decided["items"]
    )

    package = build_evidence_trust_package(demo_project_dir, "demo_project")
    assert package["available"] is True
    assert package["files"]
    assert all(not str(item["relative_path"]).startswith("/") for item in package["files"])
    package_path = demo_project_dir / package["package_file"]
    with zipfile.ZipFile(package_path) as zf:
        names = zf.namelist()
    assert "evidence_trust_package/manifest.json" in names
    assert not any(".env" in name or "node_modules" in name for name in names)


def test_claim_audit_and_human_review_api(demo_project_dir: Path) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/projects/demo_project/manuscript/claim-audit",
        json={
            "manuscript_text": "# Results\n\nThe prototype proves a statistically significant survival outcome with a p-value.",
            "retrieval_mode": "local_hybrid_fts",
        },
    )
    assert response.status_code == 200
    assert response.json()["summary"]["unsupported"] >= 1

    queue = client.get("/api/projects/demo_project/human-review-queue")
    assert queue.status_code == 200
    assert queue.json()["summary"]["pending"] >= 1

    trust = client.post("/api/projects/demo_project/export/evidence-trust-package")
    assert trust.status_code == 200
    assert trust.json()["available"] is True


def test_local_eval_suite_runs_offline(tmp_path: Path) -> None:
    output = tmp_path / "local_eval.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_local_researchagent.py",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert completed.returncode == 0, completed.stdout
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["failed"] == 0
    assert report["aggregate_pass_rate"] == 1.0
