from __future__ import annotations

from pathlib import Path

import urllib.request

from app.tools.literature_rag import ask_literature_rag, build_literature_rag
from app.tools.rag_quality import generate_chunk_quality_report, generate_retrieval_eval_report


def test_v13_rag_quality_does_not_require_network(
    demo_project_dir: Path,
    monkeypatch,
) -> None:
    def fail_network(*args, **kwargs):
        raise AssertionError("network must not be used by v1.3 local RAG quality")

    monkeypatch.setattr(urllib.request, "urlopen", fail_network)

    build_literature_rag(demo_project_dir, "demo_project")
    answer = ask_literature_rag(
        demo_project_dir,
        "demo_project",
        "efficiency stability",
        retrieval_mode="local_hybrid",
    )
    quality = generate_chunk_quality_report(demo_project_dir, "demo_project")
    evaluation = generate_retrieval_eval_report(demo_project_dir, "demo_project")

    assert answer["source_passages"]
    assert quality["summary"]["total_chunks"] > 0
    assert evaluation["metrics"]["total_cases"] > 0
