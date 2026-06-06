from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.services.storage_service import storage_service
from app.services.workflow_service import workflow_service
from app.tools.audit_log import verify_audit_hash_chain
from app.tools.patch_safety import check_patch_item
from main import app
from scripts.seed_demo import main as seed_demo
from scripts.validate_v01 import main as validate_v01
from scripts.validate_v02 import main as validate_v02
from scripts.validate_v03 import main as validate_v03
from scripts.validate_v04 import main as validate_v04


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def run_quietly(func) -> object:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        return func()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_v05_outputs(project_dir: Path) -> None:
    for relative_path in ["manuscript/patches", "manuscript/versions"]:
        path = (project_dir / relative_path).resolve()
        assert_true(
            project_dir.resolve() in path.parents or path == project_dir.resolve(),
            f"cleanup target escaped project: {relative_path}",
        )
        if path.exists():
            shutil.rmtree(path)


def find_safe_issue(project_dir: Path) -> dict:
    review_path = project_dir / "reviews" / "review_report.json"
    assert_true(review_path.exists(), "review_report.json must exist")
    review = read_json(review_path)
    assert_true(isinstance(review, dict), "review_report.json must be object")
    issues = review.get("sentence_issues")
    assert_true(isinstance(issues, list) and issues, "sentence_issues must be non-empty")
    draft_text = (project_dir / "manuscript" / "draft.md").read_text(encoding="utf-8")
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        diff = issue.get("revision_diff")
        if isinstance(diff, dict) and diff.get("before") in draft_text and diff.get("after"):
            return issue
    raise AssertionError("no draft-backed revision_diff found for v0.5 validation")


def main() -> None:
    run_quietly(validate_v01)
    run_quietly(validate_v02)
    run_quietly(validate_v03)
    run_quietly(validate_v04)
    run_quietly(seed_demo)
    response = run_quietly(lambda: workflow_service.run_workflow("demo_project"))
    assert_true(response.workflow_status == "completed", "workflow must complete")

    project_dir = storage_service.project_dir("demo_project")
    assert_true(project_dir.exists(), "demo_project must exist")
    clean_v05_outputs(project_dir)

    draft_path = project_dir / "manuscript" / "draft.md"
    assert_true(draft_path.exists(), "draft.md must exist")
    original_draft_hash = sha256_file(draft_path)
    issue = find_safe_issue(project_dir)

    client = TestClient(app)
    decision_response = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue['issue_id']}/decision",
        json={"decision": "accepted", "reason": "validate_v05 accepted revision"},
    )
    assert_true(decision_response.status_code == 200, "accepted revision decision must be recorded")
    decision = decision_response.json()
    assert_true(decision["decision"] == "accepted", "revision decision must be accepted")
    assert_true(decision["applied_to_manuscript"] is False, "decision must not modify manuscript")

    patch_response = client.post("/api/projects/demo_project/manuscript/patches/generate", json={})
    assert_true(patch_response.status_code == 200, "patch generation API must return 200")
    patch = patch_response.json()
    assert_true(patch["patch_id"] == "patch_001", "first v0.5 patch must be patch_001")
    assert_true(patch["status"] == "proposed", "patch status must be proposed")
    assert_true(patch["items"], "patch must contain at least one safe item")
    assert_true(
        any(item["decision_id"] == decision["decision_id"] for item in patch["items"]),
        "patch must include accepted decision item",
    )

    patch_path = project_dir / "manuscript" / "patches" / "patch_001.json"
    preview_path = project_dir / "manuscript" / "patches" / "patch_001.preview.md"
    assert_true(patch_path.exists(), "patch_001.json must exist")
    assert_true(preview_path.exists(), "patch_001.preview.md must exist")
    assert_true("Manuscript Patch Preview" in preview_path.read_text(encoding="utf-8"), "preview must be readable")
    assert_true(sha256_file(draft_path) == original_draft_hash, "patch generation must not change draft.md")

    dangerous_item = {
        **patch["items"][0],
        "after": f"{patch['items'][0]['after']} p < 0.05",
    }
    safety = check_patch_item(project_dir, dangerous_item)
    assert_true(safety["safe"] is False, "patch safety must block dangerous p-value item")

    confirm_response = client.post(
        "/api/projects/demo_project/manuscript/patches/patch_001/confirm",
        json={"decision": "confirmed", "reason": "validate_v05 manual confirmation"},
    )
    assert_true(confirm_response.status_code == 200, "patch confirmation API must return 200")
    confirmation = confirm_response.json()
    assert_true(confirmation["patch"]["status"] == "confirmed", "patch status must be confirmed")
    version = confirmation["version"]
    assert_true(isinstance(version, dict), "confirmed patch must create manuscript version")
    assert_true(version["version_id"] == "manuscript_v001", "first manuscript version must be manuscript_v001")

    version_path = project_dir / "manuscript" / "versions" / "manuscript_v001.md"
    history_path = project_dir / "manuscript" / "versions" / "version_history.json"
    assert_true(version_path.exists(), "manuscript_v001.md must exist")
    assert_true(history_path.exists(), "version_history.json must exist")
    history = read_json(history_path)
    assert_true(isinstance(history, dict), "version_history must be object")
    assert_true(
        any(item.get("source_patch_id") == "patch_001" for item in history.get("versions", [])),
        "version history must record source_patch_id",
    )
    assert_true(sha256_file(draft_path) == original_draft_hash, "patch confirmation must not change draft.md")

    audit_result = verify_audit_hash_chain(project_dir)
    assert_true(audit_result["valid"] is True, "audit hash chain must be valid")
    audit_api_response = client.get("/api/projects/demo_project/audit/verify")
    assert_true(audit_api_response.status_code == 200, "audit verify API must return 200")
    assert_true(audit_api_response.json()["valid"] is True, "audit verify API must return valid")

    print("ResearchAgent v0.5 validation passed.")


if __name__ == "__main__":
    main()
