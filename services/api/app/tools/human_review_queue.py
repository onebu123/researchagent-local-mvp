from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json
from app.tools.literature_index import load_literature_index

QUEUE_FILE = "trust/human_review_queue.json"
DECISIONS_FILE = "trust/human_review_decisions.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _decision_by_review_id(project_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        str(record.get("review_id")): record
        for record in _read_jsonl(project_dir / DECISIONS_FILE)
        if isinstance(record.get("review_id"), str)
    }


def _item(
    review_id: str,
    review_type: str,
    severity: str,
    title: str,
    description: str,
    artifact_path: str,
    entity_type: str,
    entity_id: str,
    recommended_action: str,
) -> dict[str, Any]:
    return {
        "review_id": review_id,
        "review_type": review_type,
        "severity": severity,
        "title": title,
        "description": description,
        "artifact_path": artifact_path,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "recommended_action": recommended_action,
        "status": "pending",
        "created_at": _utc_now(),
        "decided_at": None,
        "decision_reason": "",
        "human_review_required": True,
    }


def _literature_items(project_dir: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for entry in load_literature_index(project_dir):
        if not isinstance(entry, dict):
            continue
        literature_id = str(entry.get("literature_id") or entry.get("source_file") or "literature")
        metadata_status = str(entry.get("metadata_status") or "unknown")
        if metadata_status != "verified" or entry.get("human_verified") is not True:
            result.append(
                _item(
                    f"metadata_{literature_id}",
                    "metadata",
                    "warning",
                    f"Metadata requires human verification for {literature_id}",
                    "Literature metadata is placeholder, extracted, or not human verified.",
                    "literature/literature_index.json",
                    "literature",
                    literature_id,
                    "verify_or_mark_unverified",
                )
            )
        if entry.get("source_type") == "pdf" and (
            entry.get("quality_label") in {"low", "failed"} or entry.get("needs_manual_review") is True
        ):
            result.append(
                _item(
                    f"pdf_quality_{literature_id}",
                    "pdf_quality",
                    "blocking" if entry.get("quality_label") == "failed" else "warning",
                    f"PDF parser quality needs review for {literature_id}",
                    "PDF parsing quality is low, failed, or marked for manual review.",
                    "literature/literature_index.json",
                    "literature",
                    literature_id,
                    "review_pdf_parse_quality",
                )
            )
    return result


def _claim_audit_items(project_dir: Path) -> list[dict[str, Any]]:
    payload = _read_json(project_dir / "provenance" / "claim_audit.json", {})
    if not isinstance(payload, dict):
        return []
    items: list[dict[str, Any]] = []
    for claim in payload.get("claim_audits", []):
        if not isinstance(claim, dict):
            continue
        status = claim.get("answer_support_status")
        if status not in {"unsupported", "weakly_supported"} and not claim.get("human_review_required"):
            continue
        claim_id = str(claim.get("claim_audit_id") or len(items) + 1)
        severity = "blocking" if status == "unsupported" else "warning"
        action = "add_source_or_remove" if status == "unsupported" else "rewrite_as_limitation"
        items.append(
            _item(
                f"claim_{claim_id}",
                "claim",
                severity,
                f"Claim audit requires review: {claim_id}",
                str(claim.get("sentence") or "Claim requires review."),
                "provenance/claim_audit.json",
                "evidence_claim",
                claim_id,
                action,
            )
        )
    return items


def _reviewer_items(project_dir: Path) -> list[dict[str, Any]]:
    report = _read_json(project_dir / "reviews" / "review_report.json", {})
    if not isinstance(report, dict):
        return []
    issues = [item for item in report.get("major_issues", []) if item]
    items: list[dict[str, Any]] = []
    for index, issue in enumerate(issues, start=1):
        items.append(
            _item(
                f"reviewer_issue_{index:03d}",
                "reviewer_issue",
                "blocking",
                f"Reviewer issue {index}",
                str(issue),
                "reviews/review_report.json",
                "review_issue",
                f"reviewer_issue_{index:03d}",
                "resolve_or_document_limitation",
            )
        )
    return items


def _revision_patch_items(project_dir: Path) -> list[dict[str, Any]]:
    patches = _read_json(project_dir / "manuscript" / "patch_suggestions.json", [])
    if not isinstance(patches, list):
        return []
    items: list[dict[str, Any]] = []
    for patch in patches:
        if not isinstance(patch, dict) or patch.get("requires_human_approval") is not True:
            continue
        patch_id = str(patch.get("patch_id") or len(items) + 1)
        items.append(
            _item(
                f"revision_patch_{patch_id}",
                "revision_patch",
                "warning" if patch.get("risk_level") != "high" else "blocking",
                f"Revision patch requires approval: {patch_id}",
                str(patch.get("reason") or "Patch requires human approval."),
                "manuscript/patch_suggestions.json",
                "patch",
                patch_id,
                "approve_reject_or_edit_patch",
            )
        )
    return items


def _auto_scientist_items(project_dir: Path) -> list[dict[str, Any]]:
    review = _read_json(project_dir / "auto_scientist" / "scientist_review.json", {})
    paper_audit = _read_json(project_dir / "auto_scientist" / "paper_audit.json", {})
    reference_brief = _read_json(project_dir / "auto_scientist" / "reference_brief.json", {})
    items: list[dict[str, Any]] = []
    if isinstance(review, dict) and review:
        for index, issue in enumerate(review.get("blocking_issues", []), start=1):
            items.append(
                _item(
                    f"auto_scientist_blocking_{index:03d}",
                    "auto_scientist",
                    "blocking",
                    f"Auto Scientist blocking issue {index}",
                    str(issue),
                    "auto_scientist/scientist_review.json",
                    "auto_scientist_issue",
                    f"auto_scientist_blocking_{index:03d}",
                    "resolve_before_external_use",
                )
            )
        for index, warning in enumerate(review.get("warnings", []), start=1):
            items.append(
                _item(
                    f"auto_scientist_warning_{index:03d}",
                    "auto_scientist",
                    "warning",
                    f"Auto Scientist warning {index}",
                    str(warning),
                    "auto_scientist/scientist_review.json",
                    "auto_scientist_issue",
                    f"auto_scientist_warning_{index:03d}",
                    "document_or_revise",
                )
            )

    latest_run = _read_json(project_dir / "auto_scientist" / "latest_run.json", {})
    analysis = _read_json(project_dir / "auto_scientist" / "analysis.json", {})
    if isinstance(latest_run, dict) and latest_run.get("generated_code_experiments_enabled") is True:
        items.append(
            _item(
                "auto_scientist_generated_code_review",
                "auto_scientist",
                "warning",
                "Sandboxed generated-code experiment requires review",
                "Generated-code experiments were enabled for this Auto Scientist run. Review static scan, stdout/stderr, outputs, and sandbox limits before using results.",
                "auto_scientist/latest_run.json",
                "auto_scientist_sandbox",
                "generated_code_experiment",
                "review_sandbox_outputs_before_external_use",
            )
        )
    if isinstance(analysis, dict) and int(analysis.get("sandbox_failure_count") or 0) > 0:
        items.append(
            _item(
                "auto_scientist_sandbox_failure",
                "auto_scientist",
                "blocking",
                "Generated-code sandbox failure requires review",
                "At least one generated-code sandbox experiment failed, timed out, or was rejected by static scan.",
                "auto_scientist/analysis.json",
                "auto_scientist_sandbox",
                "sandbox_failure",
                "inspect_or_rerun_with_safer_code",
            )
        )
    if isinstance(latest_run, dict) and latest_run.get("generated_code_sandbox_mode") == "docker":
        items.append(
            _item(
                "auto_scientist_docker_sandbox_review",
                "auto_scientist",
                "warning",
                "Docker generated-code sandbox requires review",
                "Docker sandbox mode was requested. Review image provenance, network policy, resource limits, generated source, and outputs before using results.",
                "auto_scientist/latest_run.json",
                "auto_scientist_sandbox",
                "docker_generated_code_sandbox",
                "review_docker_sandbox_policy_and_outputs",
            )
        )
    approvals = _read_jsonl(project_dir / "auto_scientist" / "generated_code_approvals.jsonl")
    pending_proposals = sorted((project_dir / "auto_scientist" / "generated_code").glob("**/code_proposal.json"))
    decided_keys = {
        (str(item.get("run_id")), str(item.get("experiment_id")), str(item.get("source_hash")))
        for item in approvals
        if isinstance(item, dict)
    }
    for proposal_path in pending_proposals:
        proposal = _read_json(proposal_path, {})
        if not isinstance(proposal, dict):
            continue
        key = (str(proposal.get("run_id")), str(proposal.get("experiment_id")), str(proposal.get("source_hash")))
        source_mode = str(proposal.get("source_mode") or "deterministic")
        if source_mode == "deterministic" and key in decided_keys:
            continue
        if source_mode in {"provided", "mock_llm", "live_llm"} and key not in decided_keys:
            relative = proposal_path.relative_to(project_dir).as_posix()
            items.append(
                _item(
                    f"auto_scientist_code_approval_{proposal.get('experiment_id', 'unknown')}",
                    "auto_scientist",
                    "blocking",
                    "Generated experiment code requires approval",
                    "LLM/provided generated-code experiment source was proposed. Review static scan and source hash before sandbox execution.",
                    relative,
                    "auto_scientist_generated_code",
                    str(proposal.get("experiment_id") or "generated_code"),
                    "approve_or_reject_generated_code",
                )
            )
    revision_rounds = _read_jsonl(project_dir / "auto_scientist" / "code_revision_rounds.jsonl")
    if revision_rounds:
        items.append(
            _item(
                "auto_scientist_code_revision_review",
                "auto_scientist",
                "warning",
                "Generated-code revision loop requires review",
                "The system attempted conservative generated-code repair/rerun rounds. Review parent failures and revised outputs before relying on results.",
                "auto_scientist/code_revision_rounds.jsonl",
                "auto_scientist_generated_code",
                "code_revision_rounds",
                "review_revision_rounds_and_outputs",
            )
        )
    code_reviews = _read_jsonl(project_dir / "auto_scientist" / "code_review_rounds.jsonl")
    if code_reviews:
        items.append(
            _item(
                "auto_scientist_code_reviewer_review",
                "auto_scientist",
                "warning",
                "Generated-code reviewer diagnostics require review",
                "Reviewer-style diagnostics classified generated-code failures and recommended revision strategies. Review these diagnostics before trusting rerun outputs.",
                "auto_scientist/code_review_rounds.jsonl",
                "auto_scientist_generated_code",
                "code_review_rounds",
                "review_code_diagnostics_and_revision_strategy",
            )
        )

    latest_job = _read_json(project_dir / "jobs" / "latest_job.json", {})
    if isinstance(latest_job, dict) and latest_job.get("job_type") == "auto_scientist_run":
        job_status = str(latest_job.get("status") or "unknown")
        severity = "blocking" if job_status in {"failed", "cancelled", "cancelling"} else "info"
        if job_status in {"failed", "completed", "cancelled", "cancelling"}:
            items.append(
                _item(
                    "auto_scientist_job_review",
                    "auto_scientist",
                    severity,
                    "Auto Scientist job artifact available",
                    "A local Auto Scientist job recorded progress, outputs, logs, and cancellation state. Review failed or cancelled jobs before using downstream artifacts.",
                    "jobs/latest_job.json",
                    "job",
                    str(latest_job.get("job_id") or "auto_scientist_run"),
                    "inspect_job_log_and_outputs",
                )
            )

    experiment_tree = _read_json(project_dir / "auto_scientist" / "experiment_tree.json", {})
    if isinstance(experiment_tree, dict) and experiment_tree.get("tree_search_enabled") is True:
        items.append(
            _item(
                "auto_scientist_experiment_tree_review",
                "auto_scientist",
                "warning",
                "Experiment tree search requires review",
                "Agentic experiment tree search selected candidates using a local heuristic score. Review the tree, best node, and child experiment outputs before relying on the result.",
                "auto_scientist/experiment_tree.json",
                "auto_scientist_experiment_tree",
                "experiment_tree_search",
                "review_tree_scores_and_best_node",
            )
        )
    tree_selection = _read_json(project_dir / "auto_scientist" / "experiment_tree_selection.json", {})
    if isinstance(tree_selection, dict) and tree_selection.get("latest_selection"):
        items.append(
            _item(
                "auto_scientist_tree_selection_review",
                "auto_scientist",
                "warning",
                "Experiment tree best-node selection requires review",
                "A local user or workflow selected an experiment tree node for manuscript emphasis. Verify the selected node, source artifacts, and rationale before treating it as a result.",
                "auto_scientist/experiment_tree_selection.json",
                "auto_scientist_experiment_tree",
                str((tree_selection.get("latest_selection") or {}).get("node_id") or "selected_node"),
                "review_selected_tree_node_and_rationale",
            )
        )

    tree_reruns = _read_jsonl(project_dir / "auto_scientist" / "experiment_tree_reruns.jsonl")
    if tree_reruns:
        items.append(
            _item(
                "auto_scientist_tree_rerun_review",
                "auto_scientist",
                "warning",
                "Experiment tree node reruns require review",
                "One or more selected experiment tree nodes were rerun. Review rerun outputs and compare them with the original node before using them in the manuscript.",
                "auto_scientist/experiment_tree_reruns.jsonl",
                "auto_scientist_experiment_tree",
                "tree_reruns",
                "review_tree_node_rerun_outputs",
            )
        )

    paper_rewrite = _read_json(project_dir / "auto_scientist" / "latest_paper_rewrite.json", {})
    if isinstance(paper_rewrite, dict) and paper_rewrite:
        items.append(
            _item(
                "auto_scientist_paper_rewrite_review",
                "auto_scientist",
                "warning",
                "Tree-selected paper rewrite requires review",
                "The Auto Scientist manuscript was rewritten using a selected experiment tree node. Review the selected node and rewritten manuscript before external use.",
                "auto_scientist/latest_paper_rewrite.json",
                "auto_scientist_paper",
                str(paper_rewrite.get("selected_node_id") or "paper_rewrite"),
                "review_tree_selected_paper_rewrite",
            )
        )

    tree_revision_plan = _read_json(project_dir / "auto_scientist" / "tree_revision_plan.json", {})
    if isinstance(tree_revision_plan, dict) and tree_revision_plan:
        items.append(
            _item(
                "auto_scientist_tree_revision_plan_review",
                "auto_scientist",
                "warning",
                "Best-node-driven revision plan requires review",
                "The system generated critiques and patch suggestions from the selected experiment tree node. Review critiques before applying patches.",
                "auto_scientist/tree_revision_plan.json",
                "auto_scientist_revision",
                str(tree_revision_plan.get("selected_node_id") or "tree_revision_plan"),
                "review_tree_revision_plan_and_patches",
            )
        )
        for patch in tree_revision_plan.get("patch_suggestions", []):
            if not isinstance(patch, dict):
                continue
            review_id = str(patch.get("review_id") or f"auto_scientist_tree_revision_patch_{patch.get('patch_id', 'unknown')}")
            severity = "blocking" if patch.get("risk_level") == "high" else "warning"
            items.append(
                _item(
                    review_id,
                    "revision_patch",
                    severity,
                    f"Tree revision patch requires approval: {patch.get('patch_id')}",
                    str(patch.get("reason") or "Review generated tree revision patch before application."),
                    "auto_scientist/tree_revision_patches.json",
                    "auto_scientist_revision_patch",
                    str(patch.get("patch_id") or "tree_revision_patch"),
                    "approve_or_reject_tree_revision_patch",
                )
            )

    latest_tree_revision_application = _read_json(project_dir / "auto_scientist" / "latest_tree_revision_application.json", {})
    if isinstance(latest_tree_revision_application, dict) and latest_tree_revision_application:
        items.append(
            _item(
                "auto_scientist_tree_revision_application_review",
                "auto_scientist",
                "warning",
                "Applied tree revision manuscript requires review",
                "Approved tree revision patches produced a revised Auto Scientist manuscript copy. Review revised text and rerun audit results before external use.",
                "auto_scientist/latest_tree_revision_application.json",
                "auto_scientist_revision",
                "tree_revision_application",
                "review_revised_manuscript_and_claim_audit",
            )
        )

    citation_bindings = _read_json(project_dir / "manuscript" / "paper_citation_bindings.json", {})
    if isinstance(citation_bindings, dict) and citation_bindings:
        summary = citation_bindings.get("summary") if isinstance(citation_bindings.get("summary"), dict) else {}
        if int(summary.get("unbound") or 0) > 0 or int(summary.get("weak_binding") or 0) > 0 or int(summary.get("source_passage_only") or 0) > 0 or int(summary.get("human_review_required") or 0) > 0:
            items.append(
                _item(
                    "auto_scientist_paper_citation_binding_review",
                    "citation",
                    "blocking" if int(summary.get("unbound") or 0) > 0 else "warning",
                    "Auto Scientist paper citation bindings require review",
                    "Manuscript sentences were matched to local source passages and approved-reference state. Review weak, unbound, or source-passage-only citations before external use.",
                    "manuscript/paper_citation_bindings.json",
                    "auto_scientist_paper_citation_binding",
                    "paper_citation_bindings",
                    "review_source_passage_and_reference_bindings",
                )
            )
        for binding in citation_bindings.get("bindings", []):
            if not isinstance(binding, dict) or not binding.get("human_review_required"):
                continue
            binding_id = str(binding.get("citation_binding_id") or "citation_binding")
            severity = "blocking" if binding.get("binding_status") == "unbound" else "warning"
            items.append(
                _item(
                    f"auto_scientist_paper_citation_{binding_id}",
                    "citation",
                    severity,
                    f"Paper citation binding requires review: {binding_id}",
                    str(binding.get("sentence") or "Citation/source-passage binding requires review."),
                    "manuscript/paper_citation_bindings.json",
                    "auto_scientist_paper_citation_binding",
                    binding_id,
                    str(binding.get("recommended_action") or "review_citation_binding"),
                )
            )

    compile_report = _read_json(project_dir / "manuscript" / "latex_compile_report.json", {})
    if isinstance(compile_report, dict) and compile_report:
        compile_status = str(compile_report.get("compile_status") or "unknown")
        if compile_status not in {"compiled"}:
            severity = "blocking" if compile_status in {"unsafe_latex_rejected", "compile_failed", "compile_timeout"} else "warning"
            items.append(
                _item(
                    "auto_scientist_paper_compile_review",
                    "export",
                    severity,
                    "Auto Scientist paper compile pipeline requires review",
                    "The local LaTeX/PDF pipeline did not produce a reviewed compiled PDF or generated only a fallback preview. Review compile report before external use.",
                    "manuscript/latex_compile_report.json",
                    "auto_scientist_paper_compile",
                    "latex_compile_report",
                    "install_latex_or_review_preview_limitations",
                )
            )

    experiment_bindings = _read_json(project_dir / "auto_scientist" / "experiment_claim_bindings.json", {})
    if isinstance(experiment_bindings, dict) and experiment_bindings:
        summary = experiment_bindings.get("summary") if isinstance(experiment_bindings.get("summary"), dict) else {}
        if int(summary.get("unbound") or 0) > 0 or int(summary.get("weakly_bound") or summary.get("weak_binding") or 0) > 0 or int(summary.get("human_review_required") or 0) > 0:
            items.append(
                _item(
                    "auto_scientist_experiment_claim_binding_review",
                    "auto_scientist",
                    "blocking" if int(summary.get("unbound") or 0) > 0 else "warning",
                    "Auto Scientist manuscript experiment-claim bindings require review",
                    "Manuscript sentences were bound to experiment nodes, metrics, and artifacts. Review weak, unbound, or generated-code bindings before external use.",
                    "auto_scientist/experiment_claim_bindings.json",
                    "auto_scientist_experiment_claim_binding",
                    "experiment_claim_bindings",
                    "review_sentence_to_experiment_bindings",
                )
            )
        for binding in experiment_bindings.get("bindings", []):
            if not isinstance(binding, dict) or not binding.get("human_review_required"):
                continue
            binding_id = str(binding.get("binding_id") or "binding")
            status = str(binding.get("binding_status") or "unknown")
            severity = "blocking" if status == "unbound" else "warning"
            items.append(
                _item(
                    f"auto_scientist_{binding.get('review_id') or binding_id}",
                    "auto_scientist",
                    severity,
                    f"Experiment-claim binding requires review: {binding_id}",
                    str(binding.get("sentence") or "Manuscript sentence requires experiment binding review."),
                    "auto_scientist/experiment_claim_bindings.json",
                    "auto_scientist_experiment_claim_binding",
                    binding_id,
                    str(binding.get("recommended_action") or "review_binding_and_revise_if_needed"),
                )
            )

    if isinstance(paper_audit, dict) and paper_audit.get("human_review_required") is True:
        items.append(
            _item(
                "auto_scientist_paper_review",
                "auto_scientist",
                "warning",
                "Auto Scientist paper requires human review",
                "The AI-generated Auto Scientist manuscript is a draft artifact and requires human scientific review.",
                "auto_scientist/paper_audit.json",
                "auto_scientist_paper",
                "auto_scientist_paper",
                "review_experiment_results_claims_and_citations",
            )
        )
    if isinstance(reference_brief, dict) and reference_brief:
        summary = reference_brief.get("summary") if isinstance(reference_brief.get("summary"), dict) else {}
        warning_count = int(summary.get("review_warning_count") or 0)
        if warning_count > 0:
            items.append(
                _item(
                    "auto_scientist_reference_brief_review",
                    "reference_ideation",
                    "warning",
                    "Reference-based ideation brief requires review",
                    "Selected local references include placeholder, unverified, unapproved, or uncovered metadata. Review warnings before using ideas beyond the local workflow.",
                    "auto_scientist/reference_brief.json",
                    "auto_scientist_reference_brief",
                    "reference_brief",
                    "review_reference_metadata_and_source_passages",
                )
            )
    return items


def _apply_decisions(items: list[dict[str, Any]], decisions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for item in items:
        decision = decisions.get(str(item.get("review_id")))
        if decision:
            updated = dict(item)
            updated["status"] = decision.get("decision") or item.get("status")
            updated["decided_at"] = decision.get("decided_at")
            updated["decision_reason"] = decision.get("reason", "")
            resolved.append(updated)
        else:
            resolved.append(item)
    return resolved


def build_human_review_queue(project_dir: Path, project_id: str) -> dict[str, Any]:
    items = [
        *_literature_items(project_dir),
        *_claim_audit_items(project_dir),
        *_reviewer_items(project_dir),
        *_revision_patch_items(project_dir),
        *_auto_scientist_items(project_dir),
    ]
    decisions = _decision_by_review_id(project_dir)
    items = _apply_decisions(items, decisions)
    pending = [item for item in items if item.get("status") == "pending"]
    payload = {
        "project_id": project_id,
        "generated_at": _utc_now(),
        "relative_path": QUEUE_FILE,
        "items": items,
        "summary": {
            "total": len(items),
            "pending": len(pending),
            "blocking": sum(1 for item in pending if item.get("severity") == "blocking"),
            "warning": sum(1 for item in pending if item.get("severity") == "warning"),
            "info": sum(1 for item in pending if item.get("severity") == "info"),
        },
        "limitations": [
            "Human review queue aggregates local risk signals; it does not verify scientific truth.",
            "Approving an item records a local decision, not external peer review or citation verification.",
        ],
    }
    write_json(project_dir / QUEUE_FILE, payload)
    return payload


def read_human_review_queue(project_dir: Path, project_id: str) -> dict[str, Any]:
    return build_human_review_queue(project_dir, project_id)


def record_human_review_decision(
    project_dir: Path,
    project_id: str,
    review_id: str,
    decision: str,
    reason: str,
    source: str = "api",
) -> dict[str, Any]:
    queue = build_human_review_queue(project_dir, project_id)
    ids = {str(item.get("review_id")) for item in queue.get("items", []) if isinstance(item, dict)}
    if review_id not in ids:
        raise KeyError(f"review_id not found: {review_id}")
    record = {
        "review_id": review_id,
        "decision": decision,
        "reason": reason,
        "decided_at": _utc_now(),
        "source": source,
    }
    _append_jsonl(project_dir / DECISIONS_FILE, record)
    append_audit_event(
        project_dir,
        project_id,
        "record_human_review_decision",
        "Human review queue decision was recorded locally.",
        {"review_id": review_id, "decision": decision, "reason": reason},
        source=source,
        event_category="review",
        risk_level="medium",
        entity_type="review_issue",
        entity_id=review_id,
    )
    return build_human_review_queue(project_dir, project_id)
