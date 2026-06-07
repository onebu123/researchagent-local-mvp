from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.services.storage_service import storage_service
from app.services.workflow_service import workflow_service
from app.tools.bibtex_generator import generate_bibtex
from app.tools.citation_support_checker import generate_citation_support_report
from app.tools.citation_grounding import generate_citation_grounding_report
from app.tools.literature_metadata_lookup import run_metadata_lookup
from app.tools.literature_rag import ask_literature_rag, build_literature_rag
from app.tools.manuscript_references import generate_manuscript_references
from app.tools.reference_approval import record_reference_approval
from app.tools.reference_verification import run_reference_verification
from app.tools.rag_quality import generate_chunk_quality_report, generate_retrieval_eval_report, generate_retrieval_eval_set
from app.tools.source_passage_evidence import generate_source_passage_evidence
from scripts.seed_demo import main as seed_demo


REQUIRED_FILES = [
    "literature/literature_index.json",
    "literature/parsed/demo_pdf_literature.txt",
    "literature/parsed/demo_pdf_literature.metadata.json",
    "analysis/result_summary.json",
    "analysis/processed_data.csv",
    "analysis/run_log.txt",
    "figures/figure_1.png",
    "figures/figure_1.svg",
    "figures/figure_2.png",
    "figures/figure_2.svg",
    "figures/figure_provenance.json",
    "manuscript/draft.md",
    "manuscript/refined.md",
    "reviews/review_report.json",
    "reviews/review_report.md",
    "provenance/evidence.json",
    "literature/rag/chunks.jsonl",
    "literature/rag/rag_index.json",
    "literature/rag/rag_answers.jsonl",
    "literature/rag/chunk_quality_report.json",
    "literature/rag/retrieval_eval_set.json",
    "literature/rag/retrieval_eval_report.json",
    "provenance/source_passage_evidence.json",
    "literature/metadata_lookup_results.jsonl",
    "literature/metadata_lookup_summary.json",
    "literature/references.bib",
    "literature/bibtex_report.json",
    "provenance/citation_support_report.json",
    "literature/reference_verification/reference_verification_results.jsonl",
    "literature/reference_verification/reference_verification_summary.json",
    "literature/reference_approvals.jsonl",
    "literature/reference_approval_summary.json",
    "manuscript/references_status.json",
    "manuscript/references_section_preview.md",
    "provenance/citation_grounding_report.json",
    "llm/llm_calls.jsonl",
]


def main() -> None:
    seed_demo()
    response = workflow_service.run_workflow("demo_project")
    project_dir = storage_service.project_dir("demo_project")
    build_literature_rag(project_dir, "demo_project")
    ask_literature_rag(
        project_dir,
        "demo_project",
        "What does the demo literature mention about efficiency?",
        retrieval_mode="local_hybrid",
    )
    generate_chunk_quality_report(project_dir, "demo_project")
    generate_retrieval_eval_set(project_dir, "demo_project")
    generate_retrieval_eval_report(project_dir, "demo_project")
    generate_source_passage_evidence(project_dir, "demo_project")
    run_metadata_lookup(project_dir, "demo_project", provider="mock_fixture")
    verification = run_reference_verification(project_dir, "demo_project", provider="mock_fixture")
    first_verification = verification["results"][0] if verification["results"] else None
    if first_verification:
        record_reference_approval(
            project_dir,
            "demo_project",
            first_verification["verification_id"],
            "approved",
            "Demo approval record only; not applied to literature_index.json.",
            apply_to_literature_index=False,
            source="test",
        )
    generate_manuscript_references(project_dir, "demo_project")
    generate_bibtex(project_dir, "demo_project")
    generate_citation_support_report(project_dir, "demo_project")
    generate_citation_grounding_report(project_dir, "demo_project")
    missing = [relative for relative in REQUIRED_FILES if not (project_dir / relative).exists()]
    print(f"Workflow status: {response.workflow_status}")
    print("Output files:")
    for output in response.outputs:
        print(f"- {project_dir / output.relative_path}")
    if missing:
        raise SystemExit(f"Missing required files: {missing}")
    print("Demo workflow completed.")


if __name__ == "__main__":
    main()
