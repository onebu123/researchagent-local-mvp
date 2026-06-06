from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.services.project_service import project_service
from app.services.storage_service import storage_service
from app.tools.project_export import build_project_export


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a safe local MVP project zip export.")
    parser.add_argument("--project-id", default="demo_project", help="Project ID to export.")
    parser.add_argument("--json", action="store_true", help="Print the full export metadata as JSON.")
    return parser.parse_args()


def main() -> dict:
    args = parse_args()
    project_service.require_project(args.project_id)
    metadata = build_project_export(storage_service.project_dir(args.project_id), args.project_id)
    if args.json:
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
    else:
        print(f"Project export created: {metadata['relative_path']}")
    return metadata


if __name__ == "__main__":
    main()
