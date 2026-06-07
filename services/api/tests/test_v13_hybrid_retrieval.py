from __future__ import annotations

from pathlib import Path

from app.tools.literature_rag import ask_literature_rag, build_literature_rag, retrieve_chunks


def test_hybrid_retrieval_adds_score_breakdown(demo_project_dir: Path) -> None:
    index = build_literature_rag(demo_project_dir, "demo_project")
    assert index["retrieval_mode"] == "local_hybrid"
    assert "local_keyword" in index["supported_retrieval_modes"]

    retrieved = retrieve_chunks(
        demo_project_dir,
        "demo_project",
        "efficiency stability",
        top_k=3,
        retrieval_mode="local_hybrid",
    )
    assert retrieved
    assert retrieved[0]["score"] >= retrieved[-1]["score"]
    assert {"keyword_score", "ngram_score", "metadata_trust_score", "quality_score"} <= set(retrieved[0])
    assert isinstance(retrieved[0]["matched_terms"], list)


def test_rag_answer_records_hybrid_quality_signals(demo_project_dir: Path) -> None:
    build_literature_rag(demo_project_dir, "demo_project")
    answer = ask_literature_rag(
        demo_project_dir,
        "demo_project",
        "What does the demo literature mention about efficiency?",
        retrieval_mode="local_hybrid",
    )
    assert answer["retrieval"]["retrieval_mode"] == "local_hybrid"
    assert "quality_warnings" in answer["retrieval"]
    assert answer["source_passages"]
    passage = answer["source_passages"][0]
    assert {"keyword_score", "ngram_score", "metadata_trust_score", "quality_score"} <= set(
        passage["score_breakdown"]
    )
