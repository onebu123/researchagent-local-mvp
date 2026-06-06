from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.services.workflow_service import workflow_service
from scripts.seed_demo import main as seed_demo


@pytest.fixture(scope="session")
def demo_project_dir() -> Path:
    seed_demo()
    response = workflow_service.run_workflow("demo_project")
    assert response.workflow_status == "completed"
    return ROOT / "projects" / "demo_project"
