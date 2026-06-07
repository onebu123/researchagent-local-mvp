from __future__ import annotations

from pathlib import Path

from app.tools.literature_rag import ask_literature_rag, build_literature_rag
from app.tools.source_passage_evidence import generate_source_passage_evidence


def test_source_passage_evidence_binds_chunk_ids(demo_project_dir: Path) -> None:
    build_literature_rag(demo_project_dir, "demo_project")
    ask_literature_rag(demo_project_dir, "demo_project", "efficiency stability")

    report = generate_source_passage_evidence(demo_project_dir, "demo_project")

    assert report["records"]
    assert all(record["chunk_id"].startswith("chunk_") for record in report["records"])
    assert all(
        record["support_status"] in {"supported", "partial", "needs_human_review"}
        for record in report["records"]
    )
    assert (demo_project_dir / "provenance" / "source_passage_evidence.json").exists()
