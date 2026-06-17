from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.claim_audit import read_claim_audit
from app.tools.file_tools import write_json, write_text

REVISION_PLAN_JSON = "manuscript/revision_plan.json"
REVISION_PLAN_MD = "manuscript/revision_plan.md"
PATCH_SUGGESTIONS_JSON = "manuscript/patch_suggestions.json"
RESTRICTED_TERMS = [
    "statistically significant",
    "significant",
    "p-value",
    "p-values",
    "causal",
    "causality",
    "proves",
    "proved",
    "demonstrated",
    "confirmed",
    "显著",
    "证明",
    "证实",
    "因果",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def read_revision_plan(project_dir: Path) -> dict[str, Any]:
    payload = _read_json(project_dir / REVISION_PLAN_JSON, {})
    return payload if isinstance(payload, dict) else {}


def _restricted_hits(text: str) -> list[str]:
    lowered = text.lower()
    hits: list[str] = []
    for term in RESTRICTED_TERMS:
        if term.isascii():
            if re.search(r"\b" + re.escape(term.lower()) + r"\b", lowered):
                hits.append(term)
        elif term in text:
            hits.append(term)
    return sorted(set(hits))


def _descriptive_rewrite(sentence: str, status: str) -> str:
    base = re.sub(r"\b(?:proves?|proved|demonstrated|confirmed)\b", "describes", sentence, flags=re.IGNORECASE)
    base = re.sub(r"\b(?:statistically significant|significant)\b", "descriptive", base, flags=re.IGNORECASE)
    base = re.sub(r"\b(?:causal|causality)\b", "associational or contextual", base, flags=re.IGNORECASE)
    base = base.replace("显著", "描述性地").replace("证明", "描述").replace("证实", "描述").replace("因果", "关联或背景")
    if status == "unsupported":
        return (
            "Local evidence is insufficient for this claim. Remove it, add a verified source passage, "
            f"or rewrite as a limitation: {base}"
        )
    if status == "weakly_supported":
        return f"With human review, present cautiously as a limitation or tentative local note: {base}"
    return base


def _patch_from_claim(item: dict[str, Any], index: int) -> dict[str, Any]:
    status = str(item.get("answer_support_status") or "unsupported")
    sentence = str(item.get("sentence") or "")
    suggested = _descriptive_rewrite(sentence, status)
    if _restricted_hits(suggested):
        suggested = "Rewrite this sentence as a limitation until local source passages and human review support it."
    reason = {
        "unsupported": "No sufficient local source passage supports this claim.",
        "weakly_supported": "Local passages matched, but support is limited by metadata or parser quality.",
        "supported": "Local passages support the sentence, but citation and metadata still need human review.",
    }.get(status, "Claim requires human review.")
    return {
        "patch_id": f"revision_patch_{index:03d}",
        "source_issue_id": item.get("claim_audit_id"),
        "claim_audit_id": item.get("claim_audit_id"),
        "section": item.get("section"),
        "paragraph_index": item.get("paragraph_index"),
        "sentence_index": item.get("sentence_index"),
        "original_sentence": sentence,
        "suggested_sentence": suggested,
        "reason": reason,
        "evidence_basis": [
            passage.get("source_locator") or passage.get("chunk_id")
            for passage in item.get("matched_source_passages", [])
            if isinstance(passage, dict)
        ],
        "risk_level": "high" if status == "unsupported" else "medium" if status == "weakly_supported" else "low",
        "requires_human_approval": True,
        "status": "pending_human_approval",
        "answer_support_status": status,
    }


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Evidence-grounded Revision Plan",
        "",
        "> Suggested revisions are generated from claim audit and reviewer evidence. They do not modify the official draft until a human approves them.",
        "",
        "## Summary",
        "",
        f"- Patch suggestions: {len(payload.get('patch_suggestions', []))}",
        f"- Human approval required: {payload.get('human_approval_required')}",
        f"- Source claim audit: `{payload.get('claim_audit_file')}`",
        "",
        "## Patch Suggestions",
        "",
    ]
    for patch in payload.get("patch_suggestions", []):
        lines.extend(
            [
                f"### {patch.get('patch_id')} — {patch.get('answer_support_status')}",
                "",
                f"- Risk: `{patch.get('risk_level')}`",
                f"- Requires human approval: {patch.get('requires_human_approval')}",
                f"- Original: {patch.get('original_sentence')}",
                f"- Suggested: {patch.get('suggested_sentence')}",
                f"- Reason: {patch.get('reason')}",
                "",
            ]
        )
    if not payload.get("patch_suggestions"):
        lines.append("- No patch suggestions were generated.")
    return "\n".join(lines)


def generate_evidence_revision_plan(
    project_dir: Path,
    project_id: str,
    manuscript_relative_path: str = "manuscript/draft.md",
) -> dict[str, Any]:
    claim_audit = read_claim_audit(project_dir)
    if not claim_audit:
        raise FileNotFoundError("provenance/claim_audit.json does not exist; run claim audit first")
    items = [item for item in claim_audit.get("claim_audits", []) if isinstance(item, dict)]
    risky_items = [
        item
        for item in items
        if item.get("answer_support_status") in {"unsupported", "weakly_supported"}
        or item.get("human_review_required") is True
    ]
    patch_suggestions = [_patch_from_claim(item, index) for index, item in enumerate(risky_items, start=1)]
    payload = {
        "project_id": project_id,
        "created_at": _utc_now(),
        "manuscript_file": manuscript_relative_path,
        "revision_plan_file": REVISION_PLAN_JSON,
        "revision_plan_markdown_file": REVISION_PLAN_MD,
        "patch_suggestions_file": PATCH_SUGGESTIONS_JSON,
        "claim_audit_file": "provenance/claim_audit.json",
        "human_approval_required": True,
        "patch_suggestions": patch_suggestions,
        "limitations": [
            "Revision suggestions are not automatically applied to manuscript/draft.md.",
            "Suggestions do not add DOI, p-values, verified citation metadata, or peer-review claims.",
            "Human approval is required before any patch is merged into a draft.",
        ],
    }
    write_json(project_dir / REVISION_PLAN_JSON, payload)
    write_json(project_dir / PATCH_SUGGESTIONS_JSON, patch_suggestions)
    write_text(project_dir / REVISION_PLAN_MD, _markdown(payload))
    append_audit_event(
        project_dir,
        project_id,
        "generate_evidence_revision_plan",
        "Evidence-grounded revision plan was generated from claim audit.",
        {
            "revision_plan_file": REVISION_PLAN_JSON,
            "patch_suggestions_file": PATCH_SUGGESTIONS_JSON,
            "patch_suggestion_count": len(patch_suggestions),
            "human_approval_required": True,
        },
        source="api",
        event_category="review",
        risk_level="medium",
        entity_type="review_issue",
        entity_id="revision_plan",
    )
    return payload
