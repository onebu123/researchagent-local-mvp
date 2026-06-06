from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.agents.base import BaseAgent
from app.workflows.state import ResearchState


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _extract_section(markdown: str, section: str) -> str:
    pattern = re.compile(rf"^#\s+{re.escape(section)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(markdown)
    if not match:
        return ""
    next_heading = re.search(r"^#\s+", markdown[match.end() :], re.MULTILINE)
    if not next_heading:
        return markdown[match.end() :].strip()
    return markdown[match.end() : match.end() + next_heading.start()].strip()


def _split_sentences(paragraph: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", paragraph).strip()
    cleaned = cleaned.strip("-* ")
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _section_sentences(markdown: str, section: str) -> list[tuple[int, int, str]]:
    block = _extract_section(markdown, section)
    if not block:
        return []
    result: list[tuple[int, int, str]] = []
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", block) if item.strip()]
    for paragraph_index, paragraph in enumerate(paragraphs, start=1):
        lines = []
        for line in paragraph.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(stripped)
        for sentence_index, sentence in enumerate(_split_sentences(" ".join(lines)), start=1):
            result.append((paragraph_index, sentence_index, sentence))
    return result


def _explicit_claim_id(sentence: str, evidence_by_id: dict[str, dict[str, Any]]) -> str | None:
    for claim_id in re.findall(r"\bclaim_\d{3,}\b", sentence):
        if claim_id in evidence_by_id:
            return claim_id
    return None


def _keyword_match(
    sentence: str,
    evidence: list[dict[str, Any]],
    stats: dict[str, Any],
    figures: list[dict[str, Any]],
) -> str | None:
    lower = sentence.lower()
    row_count = str(stats.get("row_count", ""))
    column_count = str(stats.get("column_count", ""))

    if (
        "dataset" in lower
        and any(word in lower for word in ["sample", "row", "column", "numerical"])
        and (not row_count or row_count in lower or not column_count or column_count in lower)
    ):
        return "claim_001"
    if "figure 1" in lower or ("distribution" in lower and figures):
        return "claim_002"
    if "limited to" in lower or "descriptive statistics" in lower or "does not include" in lower:
        return "claim_003"

    sentence_words = set(re.findall(r"[a-zA-Z0-9_]+", lower))
    best_claim_id: str | None = None
    best_overlap = 0
    for claim in evidence:
        claim_id = claim.get("claim_id")
        claim_text = str(claim.get("claim", "")).lower()
        claim_words = set(re.findall(r"[a-zA-Z0-9_]+", claim_text))
        overlap = len(sentence_words & claim_words)
        if claim_id and overlap > best_overlap:
            best_claim_id = claim_id
            best_overlap = overlap
    if best_overlap >= 5:
        return best_claim_id
    return None


def _is_not_claim(sentence: str) -> bool:
    lower = sentence.lower()
    not_claim_markers = [
        "figure provenance records",
        "linked results claims",
        "before submission",
        "authors need",
        "manual review",
        "source_data=",
        "data_hash=",
        "outputs=",
    ]
    return any(marker in lower for marker in not_claim_markers)


class ClaimAlignmentAgent(BaseAgent):
    name = "Claim Alignment Agent"
    description = "在 manuscript 生成后对齐正文句子与 evidence claim。"

    def run(self, state: ResearchState) -> ResearchState:
        self.log(state, "aligning manuscript sentences to evidence claims")
        project_dir = state.project_dir
        draft_path = project_dir / "manuscript" / "draft.md"
        evidence_path = project_dir / "provenance" / "evidence.json"
        analysis_path = project_dir / "analysis" / "result_summary.json"
        figure_path = project_dir / "figures" / "figure_provenance.json"

        manuscript = (
            draft_path.read_text(encoding="utf-8", errors="replace")
            if draft_path.exists()
            else state.manuscript
        )
        evidence = _read_json(evidence_path, state.provenance or [])
        if not isinstance(evidence, list):
            evidence = []
        evidence_items = [item for item in evidence if isinstance(item, dict)]
        evidence_by_id = {
            item["claim_id"]: item for item in evidence_items if isinstance(item.get("claim_id"), str)
        }
        analysis = _read_json(analysis_path, state.analysis_results or {})
        if not isinstance(analysis, dict):
            analysis = {}
        figures = _read_json(figure_path, state.figures or [])
        if not isinstance(figures, list):
            figures = []

        aligned_claims: list[dict[str, Any]] = []
        counters = {"matched": 0, "needs_claim_alignment": 0, "not_claim": 0}
        alignment_index = 1
        for section in ["Results", "Discussion"]:
            for paragraph_index, sentence_index, sentence in _section_sentences(manuscript, section):
                matched_claim_id = _explicit_claim_id(sentence, evidence_by_id)
                if matched_claim_id is None:
                    matched_claim_id = _keyword_match(sentence, evidence_items, analysis, figures)

                notes: list[str] = []
                if matched_claim_id:
                    match_status = "matched"
                    evidence_status = evidence_by_id.get(matched_claim_id, {}).get(
                        "evidence_status", "needs_human_review"
                    )
                    confidence = "high"
                elif _is_not_claim(sentence):
                    match_status = "not_claim"
                    evidence_status = "needs_human_review"
                    confidence = "medium"
                    notes.append("Sentence is treated as context, limitation, or provenance listing.")
                else:
                    match_status = "needs_claim_alignment"
                    evidence_status = "needs_human_review"
                    confidence = "low"
                    notes.append("No direct evidence claim found.")

                counters[match_status] += 1
                aligned_claims.append(
                    {
                        "alignment_id": f"align_{alignment_index:03d}",
                        "section": section,
                        "paragraph_index": paragraph_index,
                        "sentence_index": sentence_index,
                        "sentence": sentence,
                        "matched_claim_id": matched_claim_id,
                        "match_status": match_status,
                        "evidence_status": evidence_status,
                        "confidence": confidence,
                        "notes": notes,
                    }
                )
                alignment_index += 1

        summary = {
            "total_sentences_checked": len(aligned_claims),
            "matched": counters["matched"],
            "needs_claim_alignment": counters["needs_claim_alignment"],
            "not_claim": counters["not_claim"],
        }
        alignment_status = "complete"
        if not aligned_claims:
            alignment_status = "missing"
        elif counters["needs_claim_alignment"]:
            alignment_status = "partial"

        payload = {
            "manuscript_file": "manuscript/draft.md",
            "evidence_file": "provenance/evidence.json",
            "analysis_file": "analysis/result_summary.json",
            "figure_provenance_file": "figures/figure_provenance.json",
            "alignment_status": alignment_status,
            "aligned_claims": aligned_claims,
            "summary": summary,
        }
        self.save_output(
            state,
            "provenance/claim_alignment.json",
            payload,
            "provenance",
            "Claim 对齐记录",
        )
        return state
