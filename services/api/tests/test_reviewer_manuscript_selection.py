from __future__ import annotations

import json
import os
from pathlib import Path

from app.agents.reviewer_agent import ReviewerAgent
from app.workflows.state import ResearchState


def _state(project_dir: Path) -> ResearchState:
    return ResearchState(
        project_id="selection_project",
        project_name="Selection Project",
        domain="demo",
        language="en",
        output_format="markdown",
        project_dir=project_dir,
    )


def _write(path: Path, text: str, mtime: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    os.utime(path, (mtime, mtime))


def _run_review(project_dir: Path) -> dict[str, object]:
    ReviewerAgent().run(_state(project_dir))
    return json.loads((project_dir / "reviews" / "review_report.json").read_text(encoding="utf-8"))


def test_reviewer_reviews_draft_when_only_draft_exists(tmp_path: Path) -> None:
    _write(tmp_path / "manuscript" / "draft.md", "# Results\n\nDraft only.\n", 100)

    report = _run_review(tmp_path)

    assert report["reviewed_manuscript_file"] == "manuscript/draft.md"


def test_reviewer_reviews_refined_when_refined_is_latest_without_alignment_path(tmp_path: Path) -> None:
    _write(tmp_path / "manuscript" / "draft.md", "# Results\n\nDraft.\n", 100)
    _write(tmp_path / "manuscript" / "refined.md", "# Results\n\nRefined.\n", 200)

    report = _run_review(tmp_path)

    assert report["reviewed_manuscript_file"] == "manuscript/refined.md"


def test_reviewer_reviews_draft_when_user_modifies_draft_later(tmp_path: Path) -> None:
    _write(tmp_path / "manuscript" / "refined.md", "# Results\n\nRefined.\n", 100)
    _write(tmp_path / "manuscript" / "draft.md", "# Results\n\nUpdated draft.\n", 300)

    report = _run_review(tmp_path)

    assert report["reviewed_manuscript_file"] == "manuscript/draft.md"


def test_reviewer_prefers_claim_alignment_audited_manuscript_file(tmp_path: Path) -> None:
    _write(tmp_path / "manuscript" / "draft.md", "# Results\n\nAligned draft.\n", 100)
    _write(tmp_path / "manuscript" / "readable.md", "# Results\n\nReadable.\n", 200)
    _write(tmp_path / "manuscript" / "refined.md", "# Results\n\nRefined.\n", 300)
    claim_alignment = {
        "audited_manuscript_file": "manuscript/readable.md",
        "aligned_claims": [],
    }
    (tmp_path / "provenance").mkdir(parents=True, exist_ok=True)
    (tmp_path / "provenance" / "claim_alignment.json").write_text(
        json.dumps(claim_alignment),
        encoding="utf-8",
    )

    report = _run_review(tmp_path)

    assert report["reviewed_manuscript_file"] == "manuscript/readable.md"
