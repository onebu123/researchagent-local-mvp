from pathlib import Path

import pytest

from app.services.storage_service import InvalidUploadError, StorageService


def test_ensure_inside_project_rejects_prefix_sibling(tmp_path: Path) -> None:
    service = StorageService(tmp_path)
    sibling = tmp_path / "demo_evil" / "file.csv"

    with pytest.raises(InvalidUploadError):
        service.ensure_inside_project("demo", sibling)


def test_ensure_inside_project_accepts_project_child(tmp_path: Path) -> None:
    service = StorageService(tmp_path)
    child = tmp_path / "demo" / "data" / "file.csv"

    assert service.ensure_inside_project("demo", child) == child.resolve()
