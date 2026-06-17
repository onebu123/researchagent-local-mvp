from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


ROOT = Path(__file__).resolve().parents[3]


def load_validate_v38():
    script_path = ROOT / "scripts" / "validate_v38.py"
    spec = importlib.util.spec_from_file_location("validate_v38", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v38_static_release_contract_passes() -> None:
    validate_v38 = load_validate_v38()

    report = validate_v38.build_validation_report()

    assert report["version"] == "v3.0.0-rc1"
    assert report["passed"] is True
    assert report["failure_count"] == 0
    assert report["failures"]["version_surface_failures"] == []
    assert report["failures"]["ci_markers_missing"] == []


def test_v38_demo_report_contract_passes(tmp_path: Path) -> None:
    validate_v38 = load_validate_v38()
    demo_report = tmp_path / "demo_report.json"
    demo_report.write_text(
        json.dumps(
            {
                "passed": True,
                "missing_required_artifacts": [],
                "generated_artifacts": list(validate_v38.REQUIRED_DEMO_ARTIFACTS),
                "summary": {
                    "run_status": "completed",
                    "experiment_count": 3,
                    "job_event_count": 26,
                    "trust_package_file_count": 70,
                    "latex_compile_status": "compiled",
                },
            }
        ),
        encoding="utf-8",
    )

    report = validate_v38.build_validation_report(demo_report)

    assert report["passed"] is True
    assert report["failures"]["demo_report"] == {}


def test_v38_health_and_package_version_surfaces() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["version"] == "v3.0.0-rc1"
    assert "v3.0.0-rc1" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "version = \"3.0.0rc1\"" in (ROOT / "services" / "api" / "pyproject.toml").read_text(encoding="utf-8")
