from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json, write_text
from app.tools.literature_rag import ask_literature_rag

CLAIM_AUDIT_JSON = "provenance/claim_audit.json"
CLAIM_AUDIT_MD = "provenance/claim_audit.md"
CLAIM_SECTIONS = ["Abstract", "Results", "Discussion", "Conclusion"]
RETRIEVAL_FALLBACKS = ["local_hybrid_fts", "local_hybrid", "local_keyword"]
RESTRICTED_CLAIM_TERMS = [
    "statistically significant",
    "p-value",
    "p-values",
    "causal",
    "causality",
    "proves",
    "proved",
    "显著",
    "因果",
    "证明",
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


def read_claim_audit(project_dir: Path) -> dict[str, Any]:
    payload = _read_json(project_dir / CLAIM_AUDIT_JSON, {})
    if isinstance(payload, dict):
        return payload
    return {}


def _extract_section(markdown: str, section: str) -> str:
    pattern = re.compile(rf"^#{{1,6}}\s+{re.escape(section)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(markdown)
    if not match:
        return ""
    next_heading = re.search(r"^#{1,6}\s+", markdown[match.end() :], re.MULTILINE)
    if not next_heading:
        return markdown[match.end() :].strip()
    return markdown[match.end() : match.end() + next_heading.start()].strip()


def _split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip().strip("-* ")
    if not cleaned:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", cleaned) if part.strip()]


def _is_claim_like(sentence: str) -> bool:
    lowered = sentence.lower()
    if len(sentence) < 24:
        return False
    if any(marker in lowered for marker in ["source_data=", "data_hash=", "outputs=", "figure provenance records"]):
        return False
    if lowered.startswith(("figure provenance", "linked results claims", "references")):
        return False
    markers = [
        "shows",
        "suggests",
        "indicates",
        "contains",
        "reports",
        "is limited",
        "does not",
        "improves",
        "improved",
        "reduces",
        "supports",
        "proves",
        "p-value",
        "表明",
        "显示",
        "说明",
        "支持",
        "包含",
    ]
    return any(marker in lowered for marker in markers) or re.search(r"\d+\s+(rows?|columns?|samples?)", lowered) is not None


def extract_claim_sentences(markdown: str) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for section in CLAIM_SECTIONS:
        block = _extract_section(markdown, section)
        if not block:
            continue
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", block) if item.strip()]
        for paragraph_index, paragraph in enumerate(paragraphs, start=1):
            lines = [line.strip() for line in paragraph.splitlines() if line.strip() and not line.strip().startswith("#")]
            for sentence_index, sentence in enumerate(_split_sentences(" ".join(lines)), start=1):
                if _is_claim_like(sentence):
                    claims.append(
                        {
                            "section": section,
                            "paragraph_index": paragraph_index,
                            "sentence_index": sentence_index,
                            "sentence": sentence,
                        }
                    )
    return claims



def _restricted_claim_hits(sentence: str) -> list[str]:
    lowered = sentence.lower()
    hits: list[str] = []
    for term in RESTRICTED_CLAIM_TERMS:
        if term.isascii():
            if re.search(r"\b" + re.escape(term.lower()) + r"\b", lowered):
                hits.append(term)
        elif term in sentence:
            hits.append(term)
    return sorted(set(hits))

def _recommended_action(status: str, flags: list[str]) -> str:
    if status == "supported" and not flags:
        return "keep_with_citation"
    if status == "supported":
        return "needs_human_review"
    if status == "weakly_supported":
        return "rewrite_as_limitation"
    return "add_source_or_remove"


def _human_review_required(status: str, flags: list[str]) -> bool:
    return status != "supported" or bool(flags)


def audit_claim_sentence(
    project_dir: Path,
    project_id: str,
    sentence: str,
    retrieval_mode: str = "local_hybrid_fts",
    top_k: int = 5,
) -> dict[str, Any]:
    modes = [retrieval_mode, *[mode for mode in RETRIEVAL_FALLBACKS if mode != retrieval_mode]]
    last_error: Exception | None = None
    answer: dict[str, Any] | None = None
    for mode in modes:
        try:
            answer = ask_literature_rag(project_dir, project_id, sentence, top_k=top_k, retrieval_mode=mode)
            break
        except ValueError as exc:
            last_error = exc
            continue
    if answer is None:
        raise last_error or ValueError("claim audit retrieval failed")
    passages = [item for item in answer.get("source_passages", []) if isinstance(item, dict)]
    flags = sorted(
        {
            str(flag)
            for passage in passages
            for flag in (passage.get("evidence_warning_flags") or [])
            if isinstance(flag, str)
        }
    )
    status = str(answer.get("answer_support_status") or "unsupported")
    restricted_hits = _restricted_claim_hits(sentence)
    extra_notes = list(answer.get("unsupported_notes", [])) if isinstance(answer.get("unsupported_notes"), list) else []
    if restricted_hits and status != "supported":
        status = "unsupported"
        extra_notes.append(
            "The audited sentence contains strong statistical/causal/proof wording that local passages do not verify."
        )
        flags = sorted(set([*flags, "restricted_claim_wording"]))
    return {
        "answer_support_status": status,
        "matched_source_passages": passages,
        "unsupported_notes": extra_notes,
        "evidence_warning_flags": flags,
        "recommended_action": _recommended_action(status, flags),
        "human_review_required": _human_review_required(status, flags),
        "rag_answer_id": answer.get("answer_id"),
        "retrieval_mode": answer.get("retrieval_mode", retrieval_mode),
        "top_source_score": answer.get("top_source_score", 0),
    }


def _status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    result = {"supported": 0, "weakly_supported": 0, "unsupported": 0}
    for item in items:
        status = str(item.get("answer_support_status") or "unsupported")
        if status in result:
            result[status] += 1
    return result


def _markdown_report(payload: dict[str, Any]) -> str:
    items = payload.get("claim_audits", []) if isinstance(payload.get("claim_audits"), list) else []
    lines = [
        "# Draft Claim Audit",
        "",
        "> Local Evidence Q&A was used to check manuscript-like claims against project-local source passages. This is not peer review or citation verification.",
        "",
        "## Summary",
        "",
        f"- Manuscript file: `{payload.get('manuscript_file')}`",
        f"- Total claim-like sentences: {payload.get('total_claims_checked', 0)}",
        f"- Supported: {payload.get('summary', {}).get('supported', 0)}",
        f"- Weakly supported: {payload.get('summary', {}).get('weakly_supported', 0)}",
        f"- Unsupported: {payload.get('summary', {}).get('unsupported', 0)}",
        f"- Human review required: {payload.get('human_review_required_count', 0)}",
        "",
        "## Claim Findings",
        "",
    ]
    if not items:
        lines.append("- No claim-like sentences were found for audit.")
    for item in items:
        passages = item.get("matched_source_passages") or []
        locators = [str(p.get("source_locator") or p.get("source_file") or p.get("chunk_id")) for p in passages if isinstance(p, dict)]
        lines.extend(
            [
                f"### {item.get('claim_audit_id')} — {item.get('answer_support_status')}",
                "",
                f"- Location: {item.get('section')} paragraph {item.get('paragraph_index')}, sentence {item.get('sentence_index')}",
                f"- Recommended action: `{item.get('recommended_action')}`",
                f"- Human review required: {item.get('human_review_required')}",
                f"- Sentence: {item.get('sentence')}",
                f"- Source locators: {', '.join(locators) if locators else 'none'}",
                f"- Unsupported notes: {item.get('unsupported_notes') or []}",
                "",
            ]
        )
    return "\n".join(lines)


def run_draft_claim_audit(
    project_dir: Path,
    project_id: str,
    manuscript_text: str | None = None,
    manuscript_relative_path: str = "manuscript/draft.md",
    retrieval_mode: str = "local_hybrid_fts",
    top_k: int = 5,
) -> dict[str, Any]:
    manuscript_path = project_dir / manuscript_relative_path
    if manuscript_text is None:
        if not manuscript_path.exists():
            raise FileNotFoundError(f"manuscript not found: {manuscript_relative_path}")
        manuscript_text = manuscript_path.read_text(encoding="utf-8", errors="replace")
    claims = extract_claim_sentences(manuscript_text)
    claim_audits: list[dict[str, Any]] = []
    for index, claim in enumerate(claims, start=1):
        result = audit_claim_sentence(
            project_dir,
            project_id,
            str(claim["sentence"]),
            retrieval_mode=retrieval_mode,
            top_k=top_k,
        )
        claim_audits.append(
            {
                "claim_audit_id": f"claim_audit_{index:03d}",
                **claim,
                **result,
            }
        )
    counts = _status_counts(claim_audits)
    payload = {
        "project_id": project_id,
        "created_at": _utc_now(),
        "manuscript_file": manuscript_relative_path,
        "claim_audit_file": CLAIM_AUDIT_JSON,
        "claim_audit_markdown_file": CLAIM_AUDIT_MD,
        "retrieval_mode": retrieval_mode,
        "top_k": top_k,
        "total_claims_checked": len(claim_audits),
        "summary": counts,
        "human_review_required_count": sum(1 for item in claim_audits if item.get("human_review_required")),
        "claim_audits": claim_audits,
        "limitations": [
            "Claim audit uses local parsed source passages only.",
            "Supported does not mean citation verification or peer review is complete.",
            "Weakly supported and unsupported claims require human review before external use.",
        ],
    }
    write_json(project_dir / CLAIM_AUDIT_JSON, payload)
    write_text(project_dir / CLAIM_AUDIT_MD, _markdown_report(payload))
    append_audit_event(
        project_dir,
        project_id,
        "run_claim_audit",
        "Draft claim audit was generated from local literature evidence.",
        {
            "claim_audit_file": CLAIM_AUDIT_JSON,
            "total_claims_checked": len(claim_audits),
            "unsupported_count": counts["unsupported"],
            "weakly_supported_count": counts["weakly_supported"],
        },
        source="api",
        event_category="review",
        risk_level="medium" if counts["unsupported"] or counts["weakly_supported"] else "low",
        entity_type="review_issue",
        entity_id="claim_audit",
    )
    return payload
