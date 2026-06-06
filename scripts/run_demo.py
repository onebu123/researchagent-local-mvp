from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.services.storage_service import storage_service
from app.services.workflow_service import workflow_service
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
]


def main() -> None:
    seed_demo()
    response = workflow_service.run_workflow("demo_project")
    project_dir = storage_service.project_dir("demo_project")
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
