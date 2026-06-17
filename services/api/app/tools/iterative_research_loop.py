from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.project_service import project_service
from app.services.storage_service import storage_service
from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, relative_posix, write_json, write_text
from app.tools.literature_index import load_literature_index
from app.tools.literature_rag import read_rag_answers
from app.tools.manuscript_safety import check_manuscript_safety
from app.tools.reference_approval import read_reference_approval_summary
from app.tools.run_history import append_run_history, utc_now

ALLOWED_CLAIMS_FILE = "agent/allowed_claims.json"
UNSUPPORTED_CLAIMS_FILE = "agent/unsupported_claims.json"
GENERATION_NOTES_FILE = "agent/generation_notes.json"
REVIEWER_ROUNDS_FILE = "agent/reviewer_rounds.jsonl"
RESEARCH_LOOP_RUNS_FILE = "agent/research_loop_runs.jsonl"
LATEST_LOOP_FILE = "agent/iterative_loop_latest.json"

RESTRICTED_REFERENCE_PATTERN = re.compile(
    r"\b(?:doi|journal|volume|issue|pages?|pp\.)\b", re.IGNORECASE
)
READINESS_PATTERN = re.compile(r"\b(?:peer-review-ready|production-ready|submission-ready)\b", re.IGNORECASE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_path(project_dir: Path, relative_path: str) -> Path:
    return project_dir / relative_path


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


def _relative(project_dir: Path, path: Path) -> str:
    return relative_posix(path, project_dir)


def _artifact_exists(project_dir: Path, relative_path: str) -> bool:
    return (project_dir / relative_path).exists()


def _source_passages(project_dir: Path) -> list[dict[str, Any]]:
    passages: list[dict[str, Any]] = []
    seen: set[str] = set()
    for answer in read_rag_answers(project_dir):
        raw_passages = answer.get("source_passages")
        if not isinstance(raw_passages, list):
            continue
        for passage in raw_passages:
            if not isinstance(passage, dict):
                continue
            passage_id = str(passage.get("chunk_id") or passage.get("source_file") or len(passages))
            if passage_id in seen:
                continue
            seen.add(passage_id)
            passages.append(
                {
                    "chunk_id": passage.get("chunk_id"),
                    "source_file": passage.get("source_file"),
                    "title": passage.get("title"),
                    "metadata_status": passage.get("metadata_status"),
                    "human_verified": bool(passage.get("human_verified")),
                    "score": passage.get("score"),
                    "text": str(passage.get("text") or "")[:800],
                }
            )
    return passages


def _load_context(project_dir: Path) -> dict[str, Any]:
    evidence = _read_json(project_dir / "provenance" / "evidence.json", [])
    if not isinstance(evidence, list):
        evidence = []
    analysis = _read_json(project_dir / "analysis" / "result_summary.json", {})
    if not isinstance(analysis, dict):
        analysis = {}
    figure_provenance = _read_json(project_dir / "figures" / "figure_provenance.json", [])
    if not isinstance(figure_provenance, list):
        figure_provenance = []
    passages = _source_passages(project_dir)
    literature = load_literature_index(project_dir)
    return {
        "evidence": evidence,
        "analysis": analysis,
        "figure_provenance": figure_provenance,
        "source_passages": passages,
        "literature": literature,
    }


def _claim_source_passages(claim: dict[str, Any], passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claim_text = str(claim.get("claim") or "").lower()
    if not claim_text:
        return []
    claim_terms = {
        term
        for term in re.findall(r"[a-z0-9][a-z0-9_-]{3,}", claim_text)
        if term not in {"claim", "figure", "results", "section", "limited"}
    }
    matches: list[dict[str, Any]] = []
    for passage in passages:
        text = str(passage.get("text") or "").lower()
        if claim_terms and claim_terms.intersection(re.findall(r"[a-z0-9][a-z0-9_-]{3,}", text)):
            matches.append(passage)
    return matches[:2]


def _build_claim_tables(context: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    allowed: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    passages = context["source_passages"]
    for index, claim in enumerate(context["evidence"], start=1):
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("claim_id") or f"claim_{index:03d}")
        evidence_status = str(claim.get("evidence_status") or "needs_human_review")
        record = {
            "claim_id": claim_id,
            "evidence_id": claim_id,
            "section": claim.get("section") or "Manuscript",
            "claim": str(claim.get("claim") or "").strip(),
            "evidence_status": evidence_status,
            "evidence_type": claim.get("evidence_type"),
            "analysis_file": claim.get("analysis_file"),
            "figure_file": claim.get("figure_file"),
            "source_passages": _claim_source_passages(claim, passages),
            "human_verified": bool(claim.get("human_verified")),
        }
        if record["claim"] and evidence_status in {"supported", "partial", "needs_human_review"}:
            allowed.append(record)
        else:
            unsupported.append(
                {
                    **record,
                    "reason": "Claim is missing text or evidence_status is missing.",
                    "draft_inclusion": "excluded",
                }
            )
    return allowed, unsupported


def _analysis_note(analysis: dict[str, Any]) -> str:
    row_count = analysis.get("row_count")
    column_count = analysis.get("column_count")
    numeric_columns = analysis.get("numeric_columns")
    if isinstance(row_count, int) and isinstance(column_count, int):
        numeric_count = len(numeric_columns) if isinstance(numeric_columns, list) else 0
        return (
            f"Local analysis artifact records {row_count} rows, {column_count} columns, "
            f"and {numeric_count} numeric fields."
        )
    return "Local analysis artifact was not sufficient to summarize dataset structure."


def _safe_user_focus(topic: str | None, research_question: str | None) -> str:
    focus = (research_question or topic or "local research question").strip()
    if not focus:
        return "local research question"
    if len(focus) > 180:
        focus = focus[:177].rstrip() + "..."
    if check_manuscript_safety(focus)["issues"]:
        return "user-provided research focus that requires manual safety review before inclusion"
    return focus


def _draft_text(
    round_number: int,
    allowed_claims: list[dict[str, Any]],
    unsupported_claims: list[dict[str, Any]],
    context: dict[str, Any],
    topic: str | None,
    research_question: str | None,
) -> str:
    focus = _safe_user_focus(topic, research_question)
    lines = [
        f"# ResearchAgent Iterative Draft Round {round_number}",
        "",
        "Scope: evidence-grounded draft suggestion for the local workspace.",
        f"Research focus: {focus}",
        "",
        "## Evidence-grounded claims",
    ]
    if allowed_claims:
        for claim in allowed_claims:
            support = claim.get("evidence_id") or claim.get("claim_id")
            source_count = len(claim.get("source_passages") or [])
            lines.append(
                f"- [{claim['claim_id']}] {claim['claim']} "
                f"(support: {support}; local source passages: {source_count})"
            )
    else:
        lines.append("- No claim was promoted into the draft because local evidence was insufficient.")
    lines.extend(
        [
            "",
            "## Local analysis context",
            _analysis_note(context["analysis"]),
            "",
            "## Figure provenance",
        ]
    )
    figures = context["figure_provenance"]
    if figures:
        for figure in figures:
            if not isinstance(figure, dict):
                continue
            figure_id = figure.get("figure_id") or "figure"
            outputs = figure.get("output_files")
            output_note = ", ".join(outputs) if isinstance(outputs, list) else str(figure.get("figure_file") or "")
            lines.append(f"- {figure_id}: generated from local provenance record; outputs: {output_note}.")
    else:
        lines.append("- No figure provenance record was available.")
    lines.extend(
        [
            "",
            "## Limitations",
            "- This draft is generated in mock/offline mode and is not a scientific conclusion.",
            "- Placeholder or unverified literature must be reviewed by a human before citation.",
            "- The draft does not add new bibliographic identifiers, statistical test outcomes, or mechanism conclusions.",
        ]
    )
    if unsupported_claims:
        lines.append("- Some candidate claims were excluded because support was incomplete.")
    return "\n".join(lines).strip() + "\n"


def _write_generation_artifacts(
    project_dir: Path,
    project_id: str,
    round_number: int,
    context: dict[str, Any],
    topic: str | None,
    research_question: str | None,
) -> dict[str, Any]:
    ensure_dir(project_dir / "agent")
    ensure_dir(project_dir / "manuscript")
    allowed_claims, unsupported_claims = _build_claim_tables(context)
    draft_relative = f"manuscript/draft_round_{round_number}.md"
    draft_path = project_dir / draft_relative
    draft = _draft_text(round_number, allowed_claims, unsupported_claims, context, topic, research_question)
    write_text(draft_path, draft)
    write_json(project_dir / ALLOWED_CLAIMS_FILE, allowed_claims)
    write_json(project_dir / UNSUPPORTED_CLAIMS_FILE, unsupported_claims)
    notes = {
        "project_id": project_id,
        "round_id": f"round_{round_number}",
        "generated_at": _now(),
        "mode": "mock_offline",
        "topic": topic or "",
        "research_question": research_question or "",
        "draft_file": draft_relative,
        "allowed_claim_count": len(allowed_claims),
        "unsupported_claim_count": len(unsupported_claims),
        "source_passage_count": len(context["source_passages"]),
        "constraints": [
            "Draft uses local allowed_claims and evidence artifacts only.",
            "No new DOI, bibliographic metadata, statistical test outcome, or mechanism conclusion is introduced.",
            "Human approval is required before treating any revision as accepted manuscript text.",
        ],
        "input_artifacts": [
            "literature/rag/rag_answers.jsonl",
            "analysis/result_summary.json",
            "provenance/evidence.json",
            "figures/figure_provenance.json",
        ],
    }
    write_json(project_dir / GENERATION_NOTES_FILE, notes)
    append_audit_event(
        project_dir,
        project_id,
        "iterative_generator_round",
        "Generator created an evidence-bounded draft round without modifying the formal draft.",
        {
            "round_id": f"round_{round_number}",
            "draft_file": draft_relative,
            "allowed_claims_file": ALLOWED_CLAIMS_FILE,
            "unsupported_claims_file": UNSUPPORTED_CLAIMS_FILE,
            "formal_draft_modified": False,
        },
        source="agent",
        event_category="workflow",
        entity_type="workflow",
        entity_id=f"round_{round_number}",
    )
    return {
        "round_id": f"round_{round_number}",
        "draft_file": draft_relative,
        "allowed_claims": allowed_claims,
        "unsupported_claims": unsupported_claims,
        "generation_notes_file": GENERATION_NOTES_FILE,
    }


def _issue(issue_id: str, severity: str, message: str) -> dict[str, str]:
    return {"issue_id": issue_id, "severity": severity, "message": message}


def _approved_reference_count(project_dir: Path) -> int:
    summary = read_reference_approval_summary(project_dir).get("summary")
    approved = summary.get("approved") if isinstance(summary, dict) else 0
    applied = summary.get("applied_to_literature_index") if isinstance(summary, dict) else 0
    literature_verified = 0
    for entry in load_literature_index(project_dir):
        if (
            isinstance(entry, dict)
            and entry.get("metadata_status") == "verified"
            and entry.get("human_verified") is True
        ):
            literature_verified += 1
    return int(approved or 0) + int(applied or 0) + literature_verified


def _review_evidence(round_id: str, generated: dict[str, Any]) -> dict[str, Any]:
    blocking: list[dict[str, str]] = []
    warnings: list[str] = []
    related_claims: list[str] = []
    related_passages: list[str] = []
    for claim in generated["allowed_claims"]:
        claim_id = str(claim.get("claim_id") or "")
        passages = claim.get("source_passages") if isinstance(claim.get("source_passages"), list) else []
        if not claim.get("evidence_id") and not passages:
            blocking.append(
                _issue(
                    f"{round_id}_evidence_{claim_id}",
                    "blocking",
                    "Claim is missing both an evidence_id and a local source passage.",
                )
            )
            related_claims.append(claim_id)
        elif not passages:
            warnings.append(f"{claim_id} has structured evidence but no retrieved source passage.")
        for passage in passages:
            if isinstance(passage, dict) and passage.get("chunk_id"):
                related_passages.append(str(passage["chunk_id"]))
    return {
        "round_id": round_id,
        "reviewer_name": "EvidenceReviewer",
        "blocking_issues": blocking,
        "warnings": warnings,
        "suggested_fixes": [
            "Attach a source passage or keep the claim limited to existing evidence_id records."
        ],
        "related_claim_ids": sorted(set(related_claims)),
        "related_source_passages": sorted(set(related_passages)),
    }


def _review_citations(project_dir: Path, round_id: str, generated: dict[str, Any]) -> dict[str, Any]:
    blocking: list[dict[str, str]] = []
    warnings: list[str] = []
    if _approved_reference_count(project_dir) == 0:
        blocking.append(
            _issue(
                f"{round_id}_citation_approval",
                "blocking",
                "No verified or human-approved reference is available for manuscript citation.",
            )
        )
    if generated["allowed_claims"] and not generated["unsupported_claims"]:
        warnings.append("Citation review still requires human approval before export.")
    return {
        "round_id": round_id,
        "reviewer_name": "CitationReviewer",
        "blocking_issues": blocking,
        "warnings": warnings,
        "suggested_fixes": [
            "Run reference verification and record a human approval before using citations."
        ],
        "related_claim_ids": [str(claim.get("claim_id")) for claim in generated["allowed_claims"]],
        "related_source_passages": [],
    }


def _review_statistics(project_dir: Path, round_id: str, generated: dict[str, Any]) -> dict[str, Any]:
    draft_text = (project_dir / generated["draft_file"]).read_text(encoding="utf-8")
    safety = check_manuscript_safety(draft_text)
    blocking = [
        _issue(
            f"{round_id}_stats_{index:03d}",
            "blocking",
            f"Restricted statistical or inference wording detected: {issue['term']}",
        )
        for index, issue in enumerate(safety.get("issues", []), start=1)
    ]
    return {
        "round_id": round_id,
        "reviewer_name": "StatisticalReviewer",
        "blocking_issues": blocking,
        "warnings": [] if blocking else ["No restricted statistical conclusion wording was detected."],
        "suggested_fixes": [
            "Replace restricted inference wording with descriptive, evidence-scoped language."
        ],
        "related_claim_ids": [str(claim.get("claim_id")) for claim in generated["allowed_claims"]],
        "related_source_passages": [],
    }


def _review_safety(project_dir: Path, round_id: str, generated: dict[str, Any]) -> dict[str, Any]:
    draft_text = (project_dir / generated["draft_file"]).read_text(encoding="utf-8")
    blocking: list[dict[str, str]] = []
    if READINESS_PATTERN.search(draft_text):
        blocking.append(
            _issue(
                f"{round_id}_safety_readiness",
                "blocking",
                "Draft contains readiness language that must not be auto-claimed.",
            )
        )
    if RESTRICTED_REFERENCE_PATTERN.search(draft_text) and "does not add new bibliographic identifiers" not in draft_text:
        blocking.append(
            _issue(
                f"{round_id}_safety_reference",
                "blocking",
                "Draft appears to add bibliographic metadata without verified reference support.",
            )
        )
    warnings = []
    if generated["unsupported_claims"]:
        warnings.append("Unsupported candidate claims were excluded from the draft and need human review.")
    return {
        "round_id": round_id,
        "reviewer_name": "SafetyReviewer",
        "blocking_issues": blocking,
        "warnings": warnings,
        "suggested_fixes": [
            "Keep limitations explicit and do not promote excluded claims without evidence."
        ],
        "related_claim_ids": [str(claim.get("claim_id")) for claim in generated["unsupported_claims"]],
        "related_source_passages": [],
    }


def _review_round(project_dir: Path, project_id: str, generated: dict[str, Any]) -> list[dict[str, Any]]:
    round_id = str(generated["round_id"])
    reviewers = [
        _review_evidence(round_id, generated),
        _review_citations(project_dir, round_id, generated),
        _review_statistics(project_dir, round_id, generated),
        _review_safety(project_dir, round_id, generated),
    ]
    created_at = _now()
    for reviewer in reviewers:
        reviewer["created_at"] = created_at
        _append_jsonl(project_dir / REVIEWER_ROUNDS_FILE, reviewer)
    append_audit_event(
        project_dir,
        project_id,
        "iterative_reviewer_round",
        "Reviewer group evaluated the draft round and recorded blocking issues.",
        {
            "round_id": round_id,
            "reviewer_records_file": REVIEWER_ROUNDS_FILE,
            "reviewer_count": len(reviewers),
            "blocking_issue_count": sum(len(item["blocking_issues"]) for item in reviewers),
        },
        source="agent",
        event_category="review",
        risk_level="medium",
        entity_type="review_issue",
        entity_id=round_id,
    )
    return reviewers


def _issue_message(issue: Any) -> str:
    if isinstance(issue, dict):
        return str(issue.get("message") or issue.get("issue") or issue)
    return str(issue)


def _build_revision_plan(
    project_dir: Path,
    project_id: str,
    round_number: int,
    generated: dict[str, Any],
    reviewer_records: list[dict[str, Any]],
) -> dict[str, Any]:
    round_id = str(generated["round_id"])
    patches: list[dict[str, Any]] = []
    for reviewer in reviewer_records:
        reviewer_name = str(reviewer.get("reviewer_name") or "Reviewer")
        for issue_index, issue in enumerate(reviewer.get("blocking_issues") or [], start=1):
            patches.append(
                {
                    "patch_id": f"patch_{round_id}_{len(patches) + 1:03d}",
                    "issue_source": reviewer_name,
                    "issue": _issue_message(issue),
                    "action": "Prepare a human-reviewed edit that resolves the blocking issue without adding new unsupported claims.",
                    "target_file": str(generated["draft_file"]),
                    "requires_human_approval": True,
                    "auto_applied": False,
                    "related_claim_ids": reviewer.get("related_claim_ids", []),
                    "related_source_passages": reviewer.get("related_source_passages", []),
                    "reviewer_issue_index": issue_index,
                }
            )
    revised_relative = f"manuscript/revised_round_{round_number}.md"
    plan_relative = f"agent/revision_plan_round_{round_number}.json"
    draft_text = (project_dir / generated["draft_file"]).read_text(encoding="utf-8")
    revision_lines = [
        draft_text.rstrip(),
        "",
        "## Revision notes requiring human approval",
    ]
    if patches:
        for patch in patches:
            revision_lines.append(f"- {patch['patch_id']}: {patch['issue']} Approval required before use.")
    else:
        revision_lines.append("- No blocking reviewer issue was detected in this round.")
    write_text(project_dir / revised_relative, "\n".join(revision_lines).strip() + "\n")
    plan = {
        "project_id": project_id,
        "round_id": round_id,
        "created_at": _now(),
        "source_draft": generated["draft_file"],
        "revised_manuscript": revised_relative,
        "formal_draft_modified": False,
        "human_approval_required": bool(patches),
        "patches": patches,
        "constraints": [
            "Patch suggestions are not automatically applied.",
            "No new bibliographic identifier is introduced.",
            "Reference verification status is not changed by the reviser.",
        ],
    }
    write_json(project_dir / plan_relative, plan)
    append_audit_event(
        project_dir,
        project_id,
        "iterative_reviser_round",
        "Reviser created patch suggestions requiring human approval.",
        {
            "round_id": round_id,
            "revision_plan_file": plan_relative,
            "revised_manuscript_file": revised_relative,
            "patch_count": len(patches),
            "requires_human_approval": True,
            "formal_draft_modified": False,
        },
        source="agent",
        event_category="patch",
        risk_level="medium",
        entity_type="patch",
        entity_id=round_id,
    )
    return plan


def _round_summary(
    round_number: int,
    generated: dict[str, Any],
    reviewers: list[dict[str, Any]],
    revision_plan: dict[str, Any],
) -> dict[str, Any]:
    blocking_count = sum(len(reviewer.get("blocking_issues") or []) for reviewer in reviewers)
    return {
        "round_id": generated["round_id"],
        "round_number": round_number,
        "draft_file": generated["draft_file"],
        "revised_file": revision_plan["revised_manuscript"],
        "revision_plan_file": f"agent/revision_plan_round_{round_number}.json",
        "revision_plan": {
            "human_approval_required": revision_plan.get("human_approval_required", False),
            "patch_count": len(revision_plan.get("patches") or []),
            "patches": revision_plan.get("patches") or [],
        },
        "reviewer_records": reviewers,
        "blocking_issue_count": blocking_count,
        "warnings": [warning for reviewer in reviewers for warning in reviewer.get("warnings", [])],
        "outputs": [
            generated["draft_file"],
            revision_plan["revised_manuscript"],
            f"agent/revision_plan_round_{round_number}.json",
            REVIEWER_ROUNDS_FILE,
        ],
    }


def run_iterative_research_loop(
    project_id: str,
    max_rounds: int = 2,
    topic: str | None = None,
    research_question: str | None = None,
) -> dict[str, Any]:
    project_service.require_project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    ensure_dir(project_dir / "agent")
    max_rounds = max(1, min(int(max_rounds or 1), 5))
    start_time = utc_now()
    context = _load_context(project_dir)
    rounds: list[dict[str, Any]] = []
    stopped_reason = "max_rounds_reached"
    outputs: list[str] = []

    for round_number in range(1, max_rounds + 1):
        generated = _write_generation_artifacts(
            project_dir,
            project_id,
            round_number,
            context,
            topic,
            research_question,
        )
        reviewers = _review_round(project_dir, project_id, generated)
        revision_plan = _build_revision_plan(project_dir, project_id, round_number, generated, reviewers)
        summary = _round_summary(round_number, generated, reviewers, revision_plan)
        rounds.append(summary)
        outputs.extend(summary["outputs"])
        run_record = {
            "project_id": project_id,
            "run_id": f"iterative_loop_{len(_read_jsonl(project_dir / RESEARCH_LOOP_RUNS_FILE)) + 1:04d}",
            "round_id": summary["round_id"],
            "round_number": round_number,
            "created_at": _now(),
            "status": "completed",
            "blocking_issue_count": summary["blocking_issue_count"],
            "stopped": summary["blocking_issue_count"] == 0,
            "stop_reason": "no_blocking_issues" if summary["blocking_issue_count"] == 0 else None,
            "outputs": summary["outputs"],
        }
        _append_jsonl(project_dir / RESEARCH_LOOP_RUNS_FILE, run_record)
        if summary["blocking_issue_count"] == 0:
            stopped_reason = "no_blocking_issues"
            break

    end_time = utc_now()
    unique_outputs = sorted(set(outputs + [ALLOWED_CLAIMS_FILE, UNSUPPORTED_CLAIMS_FILE, GENERATION_NOTES_FILE, RESEARCH_LOOP_RUNS_FILE]))
    run_history_record = append_run_history(
        project_dir,
        run_type="iterative_research_loop",
        step="agent.iterative_loop",
        status="completed",
        start_time=start_time,
        end_time=end_time,
        outputs=unique_outputs,
        warnings=[] if stopped_reason == "no_blocking_issues" else ["Loop stopped at max_rounds with unresolved reviewer issues."],
    )
    latest_outputs = {
        "allowed_claims_file": ALLOWED_CLAIMS_FILE,
        "unsupported_claims_file": UNSUPPORTED_CLAIMS_FILE,
        "generation_notes_file": GENERATION_NOTES_FILE,
        "reviewer_rounds_file": REVIEWER_ROUNDS_FILE,
        "research_loop_runs_file": RESEARCH_LOOP_RUNS_FILE,
        "run_history_file": "runs/run_history.json",
    }
    if rounds:
        latest_outputs.update(
            {
                "latest_draft_file": rounds[-1]["draft_file"],
                "latest_revised_file": rounds[-1]["revised_file"],
                "latest_revision_plan_file": rounds[-1]["revision_plan_file"],
            }
        )
    result = {
        "project_id": project_id,
        "status": "completed",
        "mode": "mock_offline",
        "max_rounds": max_rounds,
        "executed_rounds": len(rounds),
        "stopped_reason": stopped_reason,
        "run_history_id": run_history_record["run_id"],
        "rounds": rounds,
        "latest_outputs": latest_outputs,
        "formal_draft_modified": False,
        "audit_log_file": "audit/audit_log.jsonl",
    }
    write_json(project_dir / LATEST_LOOP_FILE, result)
    append_audit_event(
        project_dir,
        project_id,
        "iterative_research_loop_completed",
        "Iterative research loop completed with audited generator, reviewer, and reviser outputs.",
        {
            "executed_rounds": len(rounds),
            "stopped_reason": stopped_reason,
            "latest_file": LATEST_LOOP_FILE,
            "run_history_id": run_history_record["run_id"],
        },
        source="agent",
        event_category="workflow",
        risk_level="medium" if stopped_reason != "no_blocking_issues" else "low",
        entity_type="workflow",
        entity_id="iterative_research_loop",
    )
    return result


def read_iterative_research_loop_latest(project_id: str) -> dict[str, Any]:
    project_service.require_project(project_id)
    project_dir = storage_service.project_dir(project_id)
    path = project_dir / LATEST_LOOP_FILE
    if not path.exists():
        return {
            "project_id": project_id,
            "available": False,
            "message": "agent/iterative_loop_latest.json does not exist",
            "rounds": [],
        }
    payload = _read_json(path, {})
    if not isinstance(payload, dict):
        return {"project_id": project_id, "available": False, "message": "latest loop file is invalid", "rounds": []}
    return {**payload, "available": True}


def read_agent_runs(project_id: str) -> list[dict[str, Any]]:
    project_service.require_project(project_id)
    project_dir = storage_service.project_dir(project_id)
    records = _read_jsonl(project_dir / RESEARCH_LOOP_RUNS_FILE)
    for record in records:
        record["outputs"] = [str(item) for item in record.get("outputs", []) if isinstance(item, str)]
    return records
