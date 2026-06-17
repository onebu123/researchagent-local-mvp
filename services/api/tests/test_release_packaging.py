from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path


def load_package_release():
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "package_release.py"
    spec = importlib.util.spec_from_file_location("package_release", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_release_fixture(root: Path) -> None:
    for name in [
        "README.md",
        "AGENTS.md",
        ".gitignore",
        ".dockerignore",
        ".env.example",
        "docker-compose.yml",
    ]:
        (root / name).write_text(f"{name}\n", encoding="utf-8")
    for directory in ["services", "apps", "scripts", "docs"]:
        (root / directory).mkdir(parents=True, exist_ok=True)
        (root / directory / "keep.txt").write_text("keep\n", encoding="utf-8")
    (root / ".env").write_text("LLM_API_KEY=local-only\n", encoding="utf-8")
    (root / "projects").mkdir()
    (root / "projects" / "demo.sqlite3").write_text("runtime\n", encoding="utf-8")
    (root / "services" / "__pycache__").mkdir()
    (root / "services" / "__pycache__" / "cached.pyc").write_bytes(b"pyc")
    (root / "apps" / "node_modules").mkdir()
    (root / "apps" / "node_modules" / "module.js").write_text("skip\n", encoding="utf-8")


def test_source_zip_excludes_runtime_and_secret_files(tmp_path: Path) -> None:
    package_release = load_package_release()
    root = tmp_path / "repo"
    root.mkdir()
    create_release_fixture(root)
    output_dir = tmp_path / "dist"

    zip_path = package_release.create_source_zip("v3.0.0-rc1", output_dir, root=root)

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())

    assert ".env.example" in names
    assert ".env" not in names
    assert "projects/demo.sqlite3" not in names
    assert "services/__pycache__/cached.pyc" not in names
    assert "apps/node_modules/module.js" not in names
    assert all("\\" not in name for name in names)
