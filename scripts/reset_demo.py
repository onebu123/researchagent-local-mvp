from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.services.workflow_service import workflow_service
from scripts.seed_demo import main as seed_demo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset only projects/demo_project and rebuild demo outputs.")
    parser.add_argument("--yes", action="store_true", help="Confirm deletion of projects/demo_project.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.yes:
        raise SystemExit("Refusing to reset without --yes. Only projects/demo_project is eligible.")

    projects_root = (ROOT / "projects").resolve()
    target = (projects_root / "demo_project").resolve()
    if target.name != "demo_project" or projects_root not in target.parents:
        raise SystemExit("Resolved demo path is unsafe; aborting reset.")

    if target.exists():
        shutil.rmtree(target)
    seed_demo()
    response = workflow_service.run_workflow("demo_project")
    if response.workflow_status != "completed":
        raise SystemExit("Demo workflow did not complete after reset.")
    print("demo_project reset and rebuilt.")


if __name__ == "__main__":
    main()
