from __future__ import annotations

from pathlib import Path

import urllib.request

from app.tools.statistical_assistant import generate_statistical_assistant_report


def test_v14_statistical_assistant_does_not_require_network(
    demo_project_dir: Path,
    monkeypatch,
) -> None:
    def fail_network(*args, **kwargs):
        raise AssertionError("network must not be used by v1.4 statistical assistant")

    monkeypatch.setattr(urllib.request, "urlopen", fail_network)

    report = generate_statistical_assistant_report(demo_project_dir, "demo_project")

    assert report["dataset"]["row_count"] > 0
    assert report["descriptive_cards"]
    assert report["method_suggestions"]
