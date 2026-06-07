from __future__ import annotations

import json
import re
from pathlib import Path

from app.tools.workspace_export import build_workspace_export


SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"OPENAI_API_KEY\s*[:=]", re.IGNORECASE),
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY"),
    re.compile(r"(^|[\s\"'`(])[A-Za-z]:[\\/][^\s\"')]+"),
]


def test_workspace_export_text_artifacts_do_not_leak_secrets_or_absolute_paths(
    demo_project_dir: Path,
) -> None:
    manifest = build_workspace_export(demo_project_dir, "demo_project")
    assert manifest["safety"]["secret_scan_passed"] is True

    text_paths = [
        "exports/workspace/research_workspace_export.tex",
        "exports/workspace/trust_report.md",
        "exports/workspace/trust_report.json",
        "exports/workspace/workspace_export_manifest.json",
    ]
    for relative_path in text_paths:
        text = (demo_project_dir / relative_path).read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            assert not pattern.search(text), f"{relative_path} leaked sensitive marker"
        assert str(demo_project_dir) not in text


def test_workspace_export_manifest_contains_only_relative_paths(demo_project_dir: Path) -> None:
    manifest = build_workspace_export(demo_project_dir, "demo_project")
    text = json.dumps(manifest, ensure_ascii=False)

    assert str(demo_project_dir) not in text
    for artifact in manifest["artifacts"]:
        relative_path = artifact["relative_path"]
        assert relative_path.startswith("exports/workspace/")
        assert not Path(relative_path).is_absolute()
        assert ".." not in Path(relative_path).parts
