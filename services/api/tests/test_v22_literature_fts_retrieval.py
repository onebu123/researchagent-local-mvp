from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

from app.tools.literature_rag import ask_literature_rag, build_literature_rag, retrieve_chunks
from app.tools.literature_search import fts_index_path

ROOT = Path(__file__).resolve().parents[3]


def test_build_literature_rag_creates_local_fts_index(demo_project_dir: Path) -> None:
    index = build_literature_rag(demo_project_dir, "demo_project")

    assert "local_fts" in index["supported_retrieval_modes"]
    assert "local_hybrid_fts" in index["supported_retrieval_modes"]
    assert index["fts_index_file"] == "literature/rag/literature_fts.sqlite3"
    assert index["fts_index_kind"] in {"sqlite_fts5", "sqlite_like_fallback"}
    assert fts_index_path(demo_project_dir).exists()


def test_local_fts_returns_matching_passage_with_score_breakdown(demo_project_dir: Path) -> None:
    build_literature_rag(demo_project_dir, "demo_project")

    retrieved = retrieve_chunks(
        demo_project_dir,
        "demo_project",
        "efficiency stability",
        top_k=3,
        retrieval_mode="local_fts",
    )

    assert retrieved
    assert retrieved[0]["retrieval_mode"] == "local_fts"
    assert retrieved[0]["fts_score"] > 0
    assert "bm25_score" in retrieved[0]
    assert "efficiency" in retrieved[0]["text"].lower()


def test_local_hybrid_fts_preserves_hybrid_fields(demo_project_dir: Path) -> None:
    build_literature_rag(demo_project_dir, "demo_project")

    hybrid = retrieve_chunks(
        demo_project_dir,
        "demo_project",
        "efficiency stability",
        top_k=3,
        retrieval_mode="local_hybrid",
    )
    hybrid_fts = retrieve_chunks(
        demo_project_dir,
        "demo_project",
        "efficiency stability",
        top_k=3,
        retrieval_mode="local_hybrid_fts",
    )

    assert hybrid
    assert hybrid_fts
    assert hybrid_fts[0]["retrieval_mode"] == "local_hybrid_fts"
    assert {"keyword_score", "ngram_score", "fts_score", "bm25_score"} <= set(hybrid_fts[0])
    assert hybrid[0]["chunk_id"] in {item["chunk_id"] for item in hybrid_fts}


def test_unsupported_question_is_not_promoted_by_weak_fts_match(demo_project_dir: Path) -> None:
    build_literature_rag(demo_project_dir, "demo_project")

    answer = ask_literature_rag(
        demo_project_dir,
        "demo_project",
        "What exact p-value proves the clinical survival outcome?",
        retrieval_mode="local_fts",
    )

    assert answer["answer_support_status"] == "unsupported"
    assert answer["source_passage_count"] == 0
    assert "not contain enough passage support" in answer["answer"]
    lowered = answer["answer"].lower()
    for forbidden in ["statistically significant", "causal", "p-value", "proves"]:
        assert forbidden not in lowered


def test_fts_source_passages_keep_evidence_metadata(demo_project_dir: Path) -> None:
    build_literature_rag(demo_project_dir, "demo_project")

    answer = ask_literature_rag(
        demo_project_dir,
        "demo_project",
        "efficiency stability",
        retrieval_mode="local_hybrid_fts",
    )

    assert answer["answer_support_status"] == "weakly_supported"
    passage = answer["source_passages"][0]
    assert passage["retrieval_mode"] == "local_hybrid_fts"
    assert "fts_score" in passage["score_breakdown"]
    assert "bm25_score" in passage["score_breakdown"]
    assert passage["metadata_trust_level"] == "placeholder_or_unverified"
    assert "placeholder_metadata" in passage["evidence_warning_flags"]


def test_local_fts_mock_mode_does_not_require_network_or_api_key(
    demo_project_dir: Path,
    monkeypatch,
) -> None:
    def fail_network(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("network must not be required by local FTS retrieval")

    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(socket, "create_connection", fail_network)

    build_literature_rag(demo_project_dir, "demo_project")
    answer = ask_literature_rag(
        demo_project_dir,
        "demo_project",
        "efficiency stability",
        retrieval_mode="local_hybrid_fts",
    )

    assert answer["llm_mode"] == "mock"
    assert answer["source_passages"]


def test_evaluate_rag_supports_local_hybrid_fts(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    literature_dir = project_dir / "literature"
    literature_dir.mkdir(parents=True)
    (literature_dir / "source.md").write_text(
        "Local placeholder literature discusses efficiency and stability. "
        "It does not report p-values, causal claims, or verified citations.",
        encoding="utf-8",
    )
    eval_set = tmp_path / "eval.jsonl"
    eval_set.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "question": "What does the local literature say about efficiency?",
                        "expected_answer_support_status": "weakly_supported",
                        "expected_terms": ["efficiency"],
                        "must_not_contain": ["statistically significant", "causal", "p-value"],
                    }
                ),
                json.dumps(
                    {
                        "question": "What p-value proves the clinical result?",
                        "expected_answer_support_status": "unsupported",
                        "expected_terms": [],
                        "must_not_contain": ["statistically significant", "causal", "p-value"],
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "report.json"

    env = os.environ.copy()
    env.update({"LLM_MODE": "mock", "LLM_API_KEY": "", "OPENAI_API_KEY": "", "PYTHONUTF8": "1"})
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_rag.py",
            "--project-id",
            "tmp_eval",
            "--project-dir",
            str(project_dir),
            "--eval-set",
            str(eval_set),
            "--retrieval-mode",
            "local_hybrid_fts",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    assert completed.returncode == 0, completed.stdout
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["retrieval_mode"] == "local_hybrid_fts"
    assert report["total"] == 2
    assert report["failed"] == 0
    assert report["support_status_accuracy"] == 1.0
