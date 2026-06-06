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
from main import app
from scripts.seed_demo import main as seed_demo
from scripts.validate_v01 import main as validate_v01
from scripts.validate_v02 import main as validate_v02
from scripts.validate_v03 import main as validate_v03
from scripts.validate_v04 import main as validate_v04
from scripts.validate_v05 import main as validate_v05


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


def clean_v06_outputs(project_dir: Path) -> None:
    for relative_path in [
        "manuscript/patches",
        "manuscript/versions",
        "manuscript/diffs",
        "audit/exports",
    ]:
        path = (project_dir / relative_path).resolve()
        assert_true(
            project_dir.resolve() in path.parents or path == project_dir.resolve(),
            f"cleanup target escaped project: {relative_path}",
        )
        if path.exists():
            shutil.rmtree(path)
    for relative_path in ["reviews/revision_decisions.jsonl", "reviews/issue_resolution.json"]:
        path = (project_dir / relative_path).resolve()
        assert_true(
            project_dir.resolve() in path.parents,
            f"cleanup target escaped project: {relative_path}",
        )
        path.unlink(missing_ok=True)


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
    raise AssertionError("no draft-backed revision_diff found for v0.6 validation")


def safe_edit_text(after: str) -> str:
    if "before submission" in after:
        return after.replace("before submission", "before final submission")
    return f"{after} Manual review is still required."


def create_patch(client: TestClient, issue_id: str, reason: str) -> dict:
    decision_response = client.post(
        f"/api/projects/demo_project/review/sentence-issues/{issue_id}/decision",
        json={"decision": "accepted", "reason": reason},
    )
    assert_true(decision_response.status_code == 200, "accepted revision decision must be recorded")
    patch_response = client.post("/api/projects/demo_project/manuscript/patches/generate", json={})
    assert_true(patch_response.status_code == 200, "patch generation API must return 200")
    patch = patch_response.json()
    assert_true(patch["items"], "patch must contain at least one item")
    return patch


def main() -> None:
    run_quietly(validate_v01)
    run_quietly(validate_v02)
    run_quietly(validate_v03)
    run_quietly(validate_v04)
    run_quietly(validate_v05)

    run_quietly(seed_demo)
    response = run_quietly(lambda: workflow_service.run_workflow("demo_project"))
    assert_true(response.workflow_status == "completed", "workflow must complete")

    project_dir = storage_service.project_dir("demo_project")
    assert_true(project_dir.exists(), "demo_project must exist")
    clean_v06_outputs(project_dir)

    playwright_config = ROOT / "apps" / "web" / "playwright.config.ts"
    config_text = playwright_config.read_text(encoding="utf-8")
    assert_true('trace: "retain-on-failure"' in config_text, "Playwright trace strategy missing")
    assert_true('video: "retain-on-failure"' in config_text, "Playwright video strategy missing")
    assert_true('screenshot: "only-on-failure"' in config_text, "Playwright screenshot strategy missing")

    draft_path = project_dir / "manuscript" / "draft.md"
    assert_true(draft_path.exists(), "draft.md must exist")
    original_draft_hash = sha256_file(draft_path)
    issue = find_safe_issue(project_dir)
    client = TestClient(app)

    patch_001 = create_patch(client, issue["issue_id"], "validate_v06 patch 1")
    assert_true(patch_001["patch_id"] == "patch_001", "first v0.6 patch must be patch_001")
    patch_item = patch_001["items"][0]
    edited_after = safe_edit_text(patch_item["after"])
    edit_response = client.patch(
        f"/api/projects/demo_project/manuscript/patches/{patch_001['patch_id']}/items/{patch_item['patch_item_id']}",
        json={"after": edited_after, "reason": "validate_v06 safe edit"},
    )
    assert_true(edit_response.status_code == 200, "patch item edit API must return 200")
    edited_patch = edit_response.json()
    edited_item = edited_patch["items"][0]
    assert_true(edited_item["after"] == edited_after, "patch item after must be updated")
    assert_true(edited_item["manual_edits"], "manual_edits must be recorded")
    assert_true(edited_item["latest_safety_result"]["safe"] is True, "safe edit must pass safety")

    safety_response = client.post(
        f"/api/projects/demo_project/manuscript/patches/{patch_001['patch_id']}/items/{patch_item['patch_item_id']}/safety-check"
    )
    assert_true(safety_response.status_code == 200, "patch item safety-check API must return 200")
    assert_true(safety_response.json()["safety_result"]["safe"] is True, "safety rerun must pass")

    patch_002 = create_patch(client, issue["issue_id"], "validate_v06 patch 2")
    unsafe_item = patch_002["items"][0]
    unsafe_response = client.patch(
        f"/api/projects/demo_project/manuscript/patches/{patch_002['patch_id']}/items/{unsafe_item['patch_item_id']}",
        json={
            "after": f"{unsafe_item['after']} This significantly improved the result.",
            "reason": "validate_v06 unsafe edit",
        },
    )
    assert_true(unsafe_response.status_code == 200, "unsafe edit API must return 200")
    unsafe_patch = unsafe_response.json()
    assert_true(
        unsafe_patch["items"][0]["item_status"] == "blocked",
        "unsafe edit must mark item as blocked",
    )
    assert_true(
        unsafe_patch["items"][0]["latest_safety_result"]["safe"] is False,
        "unsafe edit must fail safety",
    )

    conflict_response = client.post(
        "/api/projects/demo_project/manuscript/patches/conflicts/check",
        json={"patch_ids": ["patch_001", "patch_002"]},
    )
    assert_true(conflict_response.status_code == 200, "conflict API must return 200")
    conflict = conflict_response.json()
    assert_true(conflict["summary"]["conflicts"] >= 1, "conflict report must include conflicts")
    conflict_path = project_dir / conflict["relative_path"]
    assert_true(conflict_path.exists(), "conflict report file must exist")

    merge_response = client.post(
        "/api/projects/demo_project/manuscript/patches/merge-preview",
        json={"patch_ids": ["patch_001", "patch_002"]},
    )
    assert_true(merge_response.status_code == 200, "merge preview API must return 200")
    merge = merge_response.json()
    assert_true(merge["can_apply"] is False, "conflicting merge preview must not be applicable")
    assert_true((project_dir / "manuscript" / "patches" / "merges" / f"{merge['merge_id']}.json").exists(), "merge JSON must exist")
    assert_true((project_dir / "manuscript" / "patches" / "merges" / f"{merge['merge_id']}.preview.md").exists(), "merge markdown preview must exist")
    assert_true(sha256_file(draft_path) == original_draft_hash, "merge preview must not modify draft.md")

    confirm_response = client.post(
        "/api/projects/demo_project/manuscript/patches/patch_001/confirm",
        json={"decision": "confirmed", "reason": "validate_v06 confirmed patch"},
    )
    assert_true(confirm_response.status_code == 200, "patch confirmation API must return 200")
    version = confirm_response.json()["version"]
    assert_true(isinstance(version, dict), "confirmed patch must create manuscript version")
    assert_true(version["version_id"] == "manuscript_v001", "first v0.6 version must be manuscript_v001")
    assert_true(sha256_file(draft_path) == original_draft_hash, "confirmed patch must not modify draft.md")

    diff_response = client.post(
        "/api/projects/demo_project/manuscript/diffs/generate",
        json={"base_file": "manuscript/draft.md", "version_id": version["version_id"]},
    )
    assert_true(diff_response.status_code == 200, "manuscript diff API must return 200")
    diff = diff_response.json()
    assert_true(diff["hunks"], "manuscript diff must include hunks")
    assert_true((project_dir / diff["relative_path"]).exists(), "diff JSON must exist")
    assert_true((project_dir / diff["preview_file"]).exists(), "diff markdown must exist")

    issue_resolution_response = client.get("/api/projects/demo_project/review/issue-resolution")
    assert_true(issue_resolution_response.status_code == 200, "issue resolution API must return 200")
    issue_resolution = issue_resolution_response.json()
    assert_true((project_dir / "reviews" / "issue_resolution.json").exists(), "issue_resolution.json must exist")
    assert_true(issue_resolution["summary"]["total_sentence_issues"] >= 1, "issue resolution must count issues")

    audit_export_response = client.post("/api/projects/demo_project/audit/export")
    assert_true(audit_export_response.status_code == 200, "audit export API must return 200")
    audit_export = audit_export_response.json()
    assert_true(audit_export["hash_chain_valid"] is True, "audit export hash chain must be valid")
    assert_true((project_dir / "audit" / "exports" / f"{audit_export['export_id']}.json").exists(), "audit export JSON must exist")
    report_path = project_dir / "audit" / "exports" / f"audit_integrity_report_{audit_export['export_id'].removeprefix('audit_export_')}.md"
    assert_true(report_path.exists(), "audit integrity report must exist")
    assert_true(
        "not a production-grade tamper-proof audit system" in report_path.read_text(encoding="utf-8"),
        "audit report must state local integrity limitation",
    )

    print("ResearchAgent v0.6 validation passed.")


if __name__ == "__main__":
    main()

