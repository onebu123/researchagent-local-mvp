from __future__ import annotations

from pathlib import Path

from app.tools.citation_support_checker import generate_citation_support_report
from app.tools.literature_rag import ask_literature_rag, build_literature_rag
from app.tools.source_passage_evidence import generate_source_passage_evidence


def test_citation_support_report_uses_local_rag_evidence(demo_project_dir: Path) -> None:
    build_literature_rag(demo_project_dir, "demo_project")
    ask_literature_rag(demo_project_dir, "demo_project", "efficiency stability")
    generate_source_passage_evidence(demo_project_dir, "demo_project")

    report = generate_citation_support_report(demo_project_dir, "demo_project")

    assert report["records"]
    assert report["summary"]["claims_checked"] == len(report["records"])
    assert all(
        record["status"] in {"supported", "partial", "unsupported", "needs_human_review"}
        for record in report["records"]
    )
    assert "scientific truth" in " ".join(report["limitations"]).lower()
