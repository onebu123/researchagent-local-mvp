from __future__ import annotations

import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


def test_project_zip_export_excludes_env_secret_cache_and_absolute_paths(demo_project_dir: Path) -> None:
    client = TestClient(app)

    secret_env_name = "OPENAI_API_KEY"
    secret_value = "sk" + "_live_should_not_ship"
    secret_line = f"{secret_env_name}={secret_value}\n"
    absolute_path_value = "C:" + "\\Users\\example\\secret\\data.txt"

    env_file = demo_project_dir / ".env"
    env_file.write_text(secret_line, encoding="utf-8")
    secret_text = demo_project_dir / "trust" / "unsafe_payload.txt"
    secret_text.write_text(secret_line, encoding="utf-8")
    absolute_path_text = demo_project_dir / "reviews" / "absolute_path_payload.txt"
    absolute_path_text.write_text(f"internal_path={absolute_path_value}", encoding="utf-8")
    cache_file = demo_project_dir / "analysis" / "__pycache__" / "cached.pyc"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(b"cached")

    try:
        response = client.post("/api/projects/demo_project/export/zip")

        assert response.status_code == 200
        payload = response.json()
        zip_path = demo_project_dir / payload["relative_path"]
        warning_paths = {item["relative_path"] for item in payload["warnings"]}
        assert "trust/unsafe_payload.txt" in warning_paths
        assert "reviews/absolute_path_payload.txt" in warning_paths

        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
            joined_names = "\n".join(names)
            assert ".env" not in names
            assert "trust/unsafe_payload.txt" not in names
            assert "reviews/absolute_path_payload.txt" not in names
            assert "__pycache__" not in joined_names
            for name in names:
                if Path(name).suffix.lower() in {".json", ".jsonl", ".md", ".txt", ".csv", ".svg"}:
                    text = archive.read(name).decode("utf-8", errors="replace")
                    assert secret_value not in text
                    assert f"{secret_env_name}=" not in text
                    assert absolute_path_value not in text
    finally:
        env_file.unlink(missing_ok=True)
        secret_text.unlink(missing_ok=True)
        absolute_path_text.unlink(missing_ok=True)
        cache_file.unlink(missing_ok=True)
