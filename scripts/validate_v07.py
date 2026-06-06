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
from scripts.validate_v06 import main as validate_v06


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


def clean_v07_outputs(project_dir: Path) -> None:
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
    for relative_path in [
        "reviews/revision_decisions.jsonl",
        "reviews/issue_resolution.json",
        "reviews/issue_resolution_reviews.jsonl",
    ]:
        path = (project_dir / relative_path).resolve()
        assert_true(project_dir.resolve() in path.parents, f"cleanup target escaped project: {relative_path}")
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
    raise AssertionError("no draft-backed revision_diff found for v0.7 validation")


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
    run_quietly(validate_v06)

    run_quietly(seed_demo)
    response = run_quietly(lambda: workflow_service.run_workflow("demo_project"))
    assert_true(response.workflow_status == "completed", "workflow must complete")

    project_dir = storage_service.project_dir("demo_project")
    assert_true(project_dir.exists(), "demo_project must exist")
    clean_v07_outputs(project_dir)

    assert_true(
        (ROOT / "docs" / "v0.7_acceptance_criteria.md").exists(),
        "v0.7 acceptance criteria document must exist",
    )
    for frontend_file in [
        "apps/web/components/VersionLineagePanel.tsx",
        "apps/web/components/IssueResolutionReviewPanel.tsx",
        "apps/web/components/PatchMergePanel.tsx",
        "apps/web/components/AuditExportPanel.tsx",
    ]:
        assert_true((ROOT / frontend_file).exists(), f"{frontend_file} must exist")

    e2e_path = ROOT / "apps" / "web" / "e2e" / "v07-trust-chain.spec.ts"
    assert_true(e2e_path.exists(), "v0.7 Playwright E2E spec must exist")
    e2e_text = e2e_path.read_text(encoding="utf-8")
    for marker in ["Version Lineage", "Issue Resolution", "Audit Report"]:
        assert_true(marker in e2e_text, f"Playwright E2E must cover {marker}")

    client = TestClient(app)
    draft_path = project_dir / "manuscript" / "draft.md"
    assert_true(draft_path.exists(), "draft.md must exist")
    original_draft_hash = sha256_file(draft_path)
    issue = find_safe_issue(project_dir)
    patch = create_patch(client, issue["issue_id"], "validate_v07 patch")

    merge_response = client.post(
        "/api/projects/demo_project/manuscript/patches/merge-preview",
        json={"patch_ids": [patch["patch_id"]]},
    )
    assert_true(merge_response.status_code == 200, "merge preview API must return 200")
    merge = merge_response.json()
    assert_true(merge["status"] == "preview", "merge must start in preview status")
    assert_true(merge["can_apply"] is True, "single safe patch merge must be applicable")
    assert_true(sha256_file(draft_path) == original_draft_hash, "merge preview must not modify draft.md")

    confirm_response = client.post(
        f"/api/projects/demo_project/manuscript/patches/merges/{merge['merge_id']}/confirm",
        json={"decision": "confirmed", "reason": "validate_v07 confirmed merge"},
    )
    assert_true(confirm_response.status_code == 200, "merge confirm API must return 200")
    confirmed = confirm_response.json()
    version = confirmed["version"]
    diff = confirmed["diff"]
    assert_true(confirmed["merge"]["status"] == "confirmed", "merge status must be confirmed")
    assert_true(isinstance(version, dict), "confirmed merge must create manuscript version")
    assert_true(version["source_type"] == "merge", "version source_type must be merge")
    assert_true(version["source_merge_id"] == merge["merge_id"], "version must reference source merge")
    assert_true(patch["patch_id"] in version["source_patch_ids"], "version must reference source patch ids")
    assert_true(isinstance(diff, dict), "confirmed merge must generate manuscript diff")
    assert_true((project_dir / version["file"]).exists(), "merge-generated manuscript version must exist")
    assert_true((project_dir / diff["relative_path"]).exists(), "merge-generated diff JSON must exist")
    assert_true(sha256_file(draft_path) == original_draft_hash, "merge confirm must not modify draft.md")

    lineage_response = client.get("/api/projects/demo_project/manuscript/versions/lineage")
    assert_true(lineage_response.status_code == 200, "version lineage API must return 200")
    lineage = lineage_response.json()
    assert_true((project_dir / "manuscript" / "versions" / "version_lineage.json").exists(), "version_lineage.json must exist")
    assert_true(any(node["id"] == merge["merge_id"] for node in lineage["nodes"]), "lineage must include merge node")
    assert_true(any(node["id"] == version["version_id"] for node in lineage["nodes"]), "lineage must include version node")
    assert_true(
        any(
            edge["source"] == merge["merge_id"]
            and edge["target"] == version["version_id"]
            and edge["relation"] == "generated_version"
            for edge in lineage["edges"]
        ),
        "lineage must include merge -> version edge",
    )

    issue_resolution_response = client.get("/api/projects/demo_project/review/issue-resolution")
    assert_true(issue_resolution_response.status_code == 200, "issue resolution API must return 200")
    issue_resolution = issue_resolution_response.json()
    matching_versions = [
        item for item in issue_resolution["versions"] if item["version_id"] == version["version_id"]
    ]
    assert_true(bool(matching_versions), "issue resolution must include merge-generated version")
    assert_true(
        issue["issue_id"] in matching_versions[0]["resolved_issue_ids"],
        "merge-applied issue must be marked resolved by provenance",
    )

    review_response = client.post(
        f"/api/projects/demo_project/review/issue-resolution/{issue['issue_id']}/review",
        json={
            "version_id": version["version_id"],
            "human_status": "resolved",
            "reason": "validate_v07 human review",
        },
    )
    assert_true(review_response.status_code == 200, "issue human review API must return 200")
    review_payload = review_response.json()
    assert_true(review_payload["review"]["human_status"] == "resolved", "human review status must be stored")
    assert_true((project_dir / "reviews" / "issue_resolution_reviews.jsonl").exists(), "issue review JSONL must exist")
    assert_true(
        review_payload["issue_resolution"]["summary"]["human_reviews"] >= 1,
        "issue resolution summary must count human reviews",
    )

    audit_export_response = client.post("/api/projects/demo_project/audit/export")
    assert_true(audit_export_response.status_code == 200, "audit export API must return 200")
    audit_export = audit_export_response.json()
    assert_true(audit_export["hash_chain_valid"] is True, "audit export hash chain must be valid")
    assert_true(audit_export["manifest_file"].startswith("audit/exports/audit_file_manifest_"), "audit export must include manifest_file")
    manifest_path = project_dir / audit_export["manifest_file"]
    assert_true(manifest_path.exists(), "audit file manifest must exist")
    manifest_response = client.get(
        f"/api/projects/demo_project/audit/exports/{audit_export['export_id']}/manifest"
    )
    assert_true(manifest_response.status_code == 200, "audit manifest API must return 200")
    manifest = manifest_response.json()
    assert_true(manifest["file_count"] == len(manifest["files"]), "manifest file count must match files")
    assert_true(any(item["relative_path"] == "manuscript/draft.md" for item in manifest["files"]), "manifest must include draft.md")
    assert_true(
        all(len(item["sha256"]) == 64 for item in manifest["files"]),
        "manifest file records must include SHA256 hashes",
    )
    report_response = client.get(
        f"/api/projects/demo_project/audit/exports/{audit_export['export_id']}/report"
    )
    assert_true(report_response.status_code == 200, "audit report API must return 200")
    assert_true("File Manifest Summary" in report_response.json()["content"], "audit report must include manifest summary")

    print("ResearchAgent v0.7 validation passed.")


if __name__ == "__main__":
    main()
