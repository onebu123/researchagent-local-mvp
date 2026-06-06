from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.agents.base import BaseAgent
from app.tools.revision_diff import build_revision_diff
from app.workflows.state import ResearchState


STRONG_CONCLUSION_TERMS = [
    "statistically significant",
    "significantly",
    "significant",
    "prove",
    "proves",
    "proved",
    "causal",
    "causality",
    "demonstrated that",
    "confirmed that",
    "显著",
    "证明",
    "证实",
    "因果",
    "显著提高",
    "显著改善",
]


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decision_at_most(current: str, cap: str) -> str:
    order = ["accept", "minor_revision", "major_revision", "reject"]
    return order[max(order.index(current), order.index(cap))]


def _extract_checklist_claim_ids(manuscript: str) -> list[str]:
    marker = "Evidence Checklist"
    if marker not in manuscript:
        return []
    checklist = manuscript.split(marker, 1)[1]
    return sorted(set(re.findall(r"\bclaim_\d{3,}\b", checklist)))


def _contains_strong_term(text: str, lower_text: str, term: str) -> bool:
    if term.isascii():
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        return re.search(pattern, lower_text) is not None
    return term in text


def _strong_terms_in_sentence(sentence: str) -> list[str]:
    lower = sentence.lower()
    return sorted(
        {
            term
            for term in STRONG_CONCLUSION_TERMS
            if _contains_strong_term(sentence, lower, term)
        }
    )


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
    cleaned = re.sub(r"\s+", " ", paragraph).strip().strip("-* ")
    if not cleaned:
        return []
    return [item.strip() for item in re.split(r"(?<=[.!?。！？])\s+", cleaned) if item.strip()]


def _section_sentences(markdown: str, section: str) -> list[tuple[str, int, int, str]]:
    block = _extract_section(markdown, section)
    if not block:
        return []
    result: list[tuple[str, int, int, str]] = []
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", block) if item.strip()]
    for paragraph_index, paragraph in enumerate(paragraphs, start=1):
        lines = []
        for line in paragraph.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(stripped)
        for sentence_index, sentence in enumerate(_split_sentences(" ".join(lines)), start=1):
            result.append((section, paragraph_index, sentence_index, sentence))
    return result


def _all_sentences_with_sections(markdown: str) -> list[tuple[str, int, int, str]]:
    sections = re.split(r"(?m)^#\s+", markdown)
    result: list[tuple[str, int, int, str]] = []
    for chunk in sections:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.splitlines()
        section = lines[0].strip() if lines else "Manuscript"
        body = "\n".join(lines[1:])
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", body) if item.strip()]
        for paragraph_index, paragraph in enumerate(paragraphs, start=1):
            for sentence_index, sentence in enumerate(_split_sentences(paragraph), start=1):
                result.append((section, paragraph_index, sentence_index, sentence))
    return result


def _new_sentence_issue(
    index: int,
    section: str,
    paragraph_index: int,
    sentence_index: int,
    sentence: str,
    issue_type: str,
    severity: str,
    related_claim_id: str | None,
    evidence_status: str,
    suggested_revision: str,
) -> dict[str, Any]:
    issue = {
        "issue_id": f"sent_issue_{index:03d}",
        "section": section,
        "paragraph_index": paragraph_index,
        "sentence_index": sentence_index,
        "sentence": sentence,
        "issue_type": issue_type,
        "severity": severity,
        "related_claim_id": related_claim_id,
        "evidence_status": evidence_status,
        "suggested_revision": suggested_revision,
    }
    issue["revision_diff"] = build_revision_diff(issue)
    return issue


def _discussion_over_inference(sentence: str) -> bool:
    lower = sentence.lower()
    markers = [
        "promising direction",
        "suggest",
        "suggests",
        "indicate",
        "indicates",
        "optimization",
        "mechanism",
        "therefore",
        "由此",
        "表明",
        "优化",
        "机制",
    ]
    return any(marker in lower for marker in markers)


class ReviewerAgent(BaseAgent):
    name = "Reviewer Agent"
    description = "检查草稿、证据、图表、文献 metadata、claim alignment 和句子级风险。"

    def run(self, state: ResearchState) -> ResearchState:
        self.log(state, "reviewing manuscript")
        project_dir = state.project_dir
        draft_path = project_dir / "manuscript" / "draft.md"
        refined_path = project_dir / "manuscript" / "refined.md"
        evidence_path = project_dir / "provenance" / "evidence.json"
        claim_alignment_path = project_dir / "provenance" / "claim_alignment.json"
        figure_path = project_dir / "figures" / "figure_provenance.json"
        analysis_path = project_dir / "analysis" / "result_summary.json"
        analysis_provenance_path = project_dir / "analysis" / "analysis_provenance.json"
        literature_index_path = project_dir / "literature" / "literature_index.json"

        manuscript_parts: list[str] = []
        if draft_path.exists():
            manuscript_parts.append(draft_path.read_text(encoding="utf-8", errors="replace"))
        elif state.manuscript:
            manuscript_parts.append(state.manuscript)
        if refined_path.exists():
            manuscript_parts.append(refined_path.read_text(encoding="utf-8", errors="replace"))
        elif state.refined_manuscript:
            manuscript_parts.append(state.refined_manuscript)
        manuscript = "\n\n".join(manuscript_parts)

        evidence = _read_json(evidence_path, state.provenance or [])
        if not isinstance(evidence, list):
            evidence = []
        figures = _read_json(figure_path, state.figures or [])
        if not isinstance(figures, list):
            figures = []
        analysis = _read_json(analysis_path, state.analysis_results or {})
        if not isinstance(analysis, dict):
            analysis = {}
        analysis_provenance = _read_json(analysis_provenance_path, {})
        if not isinstance(analysis_provenance, dict):
            analysis_provenance = {}
        literature_index = _read_json(literature_index_path, state.literature_index or [])
        if not isinstance(literature_index, list):
            literature_index = []
        claim_alignment = _read_json(claim_alignment_path, {})
        if not isinstance(claim_alignment, dict):
            claim_alignment = {}

        report: dict[str, Any] = {
            "overall_decision": "minor_revision",
            "major_issues": [],
            "minor_issues": [],
            "citation_issues": [],
            "evidence_issues": [],
            "figure_issues": [],
            "statistical_issues": [],
            "overclaims": [],
            "consistency_checks": [],
            "metadata_issues": [],
            "sentence_issues": [],
            "recommended_revisions": [],
        }

        if "Evidence Checklist" not in manuscript:
            report["evidence_issues"].append("draft.md is missing Evidence Checklist.")

        evidence_ids = {
            item.get("claim_id")
            for item in evidence
            if isinstance(item, dict) and item.get("claim_id")
        }
        checklist_ids = _extract_checklist_claim_ids(manuscript)
        missing_checklist_ids = [claim_id for claim_id in checklist_ids if claim_id not in evidence_ids]
        if not checklist_ids:
            report["evidence_issues"].append("Evidence Checklist does not contain claim_id.")
        if missing_checklist_ids:
            report["evidence_issues"].append(
                f"Evidence Checklist claim_id not found in evidence.json: {missing_checklist_ids}"
            )

        if len(evidence) < 3:
            report["evidence_issues"].append("evidence.json contains fewer than 3 claims.")
        missing_evidence_ids = [
            item.get("claim_id", "unknown")
            for item in evidence
            if isinstance(item, dict) and item.get("evidence_status") == "missing"
        ]
        if missing_evidence_ids:
            report["evidence_issues"].append(f"Missing evidence claims: {missing_evidence_ids}")

        analysis_claims = [
            item
            for item in evidence
            if isinstance(item, dict)
            and item.get("evidence_type") in {"analysis", "analysis_summary"}
        ]
        for claim in analysis_claims:
            provenance_file = claim.get("analysis_provenance_file")
            if provenance_file != "analysis/analysis_provenance.json":
                report["evidence_issues"].append(
                    f"{claim.get('claim_id', 'unknown')} does not bind analysis_provenance.json."
                )

        if not analysis_provenance_path.exists():
            report["evidence_issues"].append("analysis/analysis_provenance.json is missing.")
        else:
            for field in ["input_data_hash", "analysis_function", "generated_files", "runtime"]:
                if not analysis_provenance.get(field):
                    report["evidence_issues"].append(
                        f"analysis_provenance.json is missing required field: {field}"
                    )
            for field in ["parameters", "script_version", "output_file_hashes"]:
                if not analysis_provenance.get(field):
                    report["evidence_issues"].append(
                        f"analysis_provenance.json is missing v0.4 field: {field}"
                    )
            if "random_seed" not in analysis_provenance:
                report["evidence_issues"].append(
                    "analysis_provenance.json is missing v0.4 field: random_seed"
                )
            limitations = analysis_provenance.get("limitations")
            if not isinstance(limitations, list) or not any(
                "p-value" in str(item).lower() or "p-values" in str(item).lower()
                for item in limitations
            ):
                report["statistical_issues"].append(
                    "analysis_provenance.json must state that no p-values are generated."
                )
            if not isinstance(limitations, list) or not any(
                "causal" in str(item).lower() or "因果" in str(item)
                for item in limitations
            ):
                report["statistical_issues"].append(
                    "analysis_provenance.json must state that causal inference is not performed."
                )
            output_hashes = analysis_provenance.get("output_file_hashes")
            if isinstance(output_hashes, dict):
                for generated_file in analysis_provenance.get("generated_files", []):
                    if generated_file not in output_hashes:
                        report["evidence_issues"].append(
                            f"analysis_provenance output_file_hashes missing {generated_file}."
                        )
            report["consistency_checks"].append("analysis_provenance.json exists.")

        lower_manuscript = manuscript.lower()
        found_terms = [
            term
            for term in STRONG_CONCLUSION_TERMS
            if _contains_strong_term(manuscript, lower_manuscript, term)
        ]
        has_statistical_support = bool(analysis.get("statistical_tests") or analysis.get("p_values"))
        if found_terms and not has_statistical_support:
            report["overclaims"].append(
                {
                    "terms": sorted(set(found_terms)),
                    "reason": (
                        "Manuscript contains strong conclusion terms, but result_summary.json has no "
                        "statistical_tests or p_values."
                    ),
                }
            )
            report["statistical_issues"].append(
                "No statistical_tests or p_values found; strong statistical or causal wording is not allowed."
            )

        if not figure_path.exists():
            report["figure_issues"].append("figures/figure_provenance.json is missing.")
        if not figures:
            report["figure_issues"].append("figure_provenance.json has no figure records.")
        for figure in figures:
            figure_id = figure.get("figure_id", "unknown") if isinstance(figure, dict) else "unknown"
            if not isinstance(figure, dict):
                report["figure_issues"].append("figure_provenance.json contains a non-object record.")
                continue
            if figure.get("is_ai_generated") is not False:
                report["figure_issues"].append(f"{figure_id} is missing is_ai_generated=false.")
            if figure.get("is_experimental_result") is not True:
                report["figure_issues"].append(f"{figure_id} is missing is_experimental_result=true.")
            source_data = figure.get("source_data")
            if not source_data:
                report["figure_issues"].append(f"{figure_id} is missing source_data.")
            elif not (project_dir / source_data).exists():
                report["figure_issues"].append(f"{figure_id} source_data does not exist: {source_data}")
            data_hash = figure.get("data_hash")
            if not data_hash:
                report["figure_issues"].append(f"{figure_id} is missing data_hash.")
            elif source_data and (project_dir / source_data).exists():
                actual_hash = _sha256_file(project_dir / source_data)
                if actual_hash != data_hash:
                    report["figure_issues"].append(f"{figure_id} data_hash does not match source_data.")
            output_files = figure.get("output_files") or []
            if not output_files:
                report["figure_issues"].append(f"{figure_id} is missing output_files.")
            for output_file in output_files:
                if not (project_dir / output_file).exists():
                    report["figure_issues"].append(f"{figure_id} output_file missing: {output_file}")

        row_count = analysis.get("row_count")
        column_count = analysis.get("column_count")
        row_mentions = [int(value) for value in re.findall(r"(\d+)\s+rows?\b", manuscript)]
        column_mentions = [int(value) for value in re.findall(r"(\d+)\s+columns?\b", manuscript)]
        if row_count is not None and row_mentions:
            if any(value != int(row_count) for value in row_mentions):
                report["consistency_checks"].append(
                    f"row_count mismatch: expected {row_count}, found {row_mentions}"
                )
            else:
                report["consistency_checks"].append(f"row_count matches: {row_count}")
        if column_count is not None and column_mentions:
            if any(value != int(column_count) for value in column_mentions):
                report["consistency_checks"].append(
                    f"column_count mismatch: expected {column_count}, found {column_mentions}"
                )
            else:
                report["consistency_checks"].append(f"column_count matches: {column_count}")

        placeholder_records = [
            entry.get("literature_id", entry.get("source_file", "unknown"))
            for entry in literature_index
            if isinstance(entry, dict)
            and (entry.get("metadata_status") == "placeholder" or not entry.get("human_verified"))
        ]
        verified_records = [
            entry
            for entry in literature_index
            if isinstance(entry, dict)
            and entry.get("metadata_status") == "verified"
            and entry.get("human_verified") is True
        ]
        if placeholder_records:
            report["citation_issues"].append(
                f"placeholder or unverified literature metadata remains: {placeholder_records}"
            )
        if not verified_records:
            report["citation_issues"].append("No human-verified references are available.")
        for entry in verified_records:
            missing_fields = [
                field
                for field in ["doi", "year"]
                if entry.get(field) in {None, ""}
            ]
            if missing_fields:
                report["minor_issues"].append(
                    f"{entry.get('literature_id', 'unknown')} is verified but missing {missing_fields}."
                )

        pdf_records = [
            entry for entry in literature_index if isinstance(entry, dict) and entry.get("source_type") == "pdf"
        ]
        low_quality_pdf_records = [
            entry.get("literature_id", entry.get("source_file", "unknown"))
            for entry in pdf_records
            if entry.get("quality_label") in {"low", "failed"} or entry.get("needs_manual_review") is True
        ]
        if low_quality_pdf_records:
            report["metadata_issues"].append(
                f"PDF parse quality requires manual review: {low_quality_pdf_records}"
            )
        for entry in pdf_records:
            pages = entry.get("pages")
            if not isinstance(pages, list):
                report["metadata_issues"].append(
                    f"{entry.get('literature_id', entry.get('source_file', 'unknown'))} is missing page-level PDF quality records."
                )
                continue
            low_pages = [
                page
                for page in pages
                if isinstance(page, dict) and page.get("quality_signal") in {"low", "empty"}
            ]
            if pages and len(low_pages) / len(pages) >= 0.5:
                report["metadata_issues"].append(
                    f"{entry.get('literature_id', entry.get('source_file', 'unknown'))} has a high low-quality PDF page ratio."
                )
            for page in pages:
                if not isinstance(page, dict):
                    report["metadata_issues"].append("PDF page quality record must be an object.")
                    continue
                ocr = page.get("ocr")
                if not isinstance(ocr, dict) or ocr.get("ocr_attempted") is not False:
                    report["metadata_issues"].append(
                        f"{entry.get('literature_id', 'unknown')} page {page.get('page_number')} must reserve OCR fields with ocr_attempted=false."
                    )

        aligned_claims = claim_alignment.get("aligned_claims", [])
        if not claim_alignment_path.exists():
            report["evidence_issues"].append("provenance/claim_alignment.json is missing.")
        elif not isinstance(aligned_claims, list):
            report["evidence_issues"].append("claim_alignment.json aligned_claims must be a list.")

        sentence_issues: list[dict[str, Any]] = []
        seen_issue_keys: set[tuple[str, int, int, str]] = set()

        def add_sentence_issue(
            section: str,
            paragraph_index: int,
            sentence_index: int,
            sentence: str,
            issue_type: str,
            severity: str,
            related_claim_id: str | None,
            evidence_status: str,
            suggested_revision: str,
        ) -> None:
            key = (section, paragraph_index, sentence_index, issue_type)
            if key in seen_issue_keys:
                return
            seen_issue_keys.add(key)
            sentence_issues.append(
                _new_sentence_issue(
                    len(sentence_issues) + 1,
                    section,
                    paragraph_index,
                    sentence_index,
                    sentence,
                    issue_type,
                    severity,
                    related_claim_id,
                    evidence_status,
                    suggested_revision,
                )
            )

        if isinstance(aligned_claims, list):
            for item in aligned_claims:
                if not isinstance(item, dict):
                    continue
                section = str(item.get("section", "Unknown"))
                paragraph_index = int(item.get("paragraph_index") or 0)
                sentence_index = int(item.get("sentence_index") or 0)
                sentence = str(item.get("sentence", ""))
                related_claim_id = item.get("matched_claim_id")
                evidence_status = str(item.get("evidence_status", "missing"))
                match_status = item.get("match_status")
                if match_status == "needs_claim_alignment":
                    issue_type = (
                        "discussion_over_inference"
                        if section == "Discussion" and _discussion_over_inference(sentence)
                        else "missing_claim_alignment"
                    )
                    severity = "major" if section == "Results" or issue_type == "discussion_over_inference" else "minor"
                    add_sentence_issue(
                        section,
                        paragraph_index,
                        sentence_index,
                        sentence,
                        issue_type,
                        severity,
                        related_claim_id if isinstance(related_claim_id, str) else None,
                        evidence_status,
                        "Add a supported evidence claim or revise the sentence as context/limitation.",
                    )

        for section, paragraph_index, sentence_index, sentence in _all_sentences_with_sections(manuscript):
            terms = _strong_terms_in_sentence(sentence)
            if terms and not has_statistical_support:
                add_sentence_issue(
                    section,
                    paragraph_index,
                    sentence_index,
                    sentence,
                    "overclaim",
                    "major",
                    None,
                    "missing",
                    (
                        "Replace strong conclusion wording with a descriptive statement unless "
                        "statistical evidence is provided."
                    ),
                )

        report["sentence_issues"] = sentence_issues

        if not report["major_issues"]:
            report["major_issues"].extend(
                issue
                for issue in [
                    *report["evidence_issues"],
                    *report["figure_issues"],
                    *report["statistical_issues"],
                    *report["citation_issues"],
                    *report["metadata_issues"],
                ]
                if issue
            )
            report["major_issues"].extend(
                f"{item['issue_id']}: {item['issue_type']} in {item['section']}"
                for item in sentence_issues
                if item.get("severity") == "major"
            )

        report["minor_issues"].append(
            "v0.3 still requires human verification of literature metadata, evidence status, and figure interpretation."
        )
        report["recommended_revisions"] = [
            "Add human-verified literature metadata before using Verified references.",
            "Review every human_verified=false claim before submission.",
            "Add statistical_tests or p_values only after a real, reproducible statistical analysis exists.",
            "Resolve claim_alignment needs_claim_alignment sentences or rewrite them as limitations.",
            "Manually review low-quality PDF parse results before relying on extracted text.",
        ]

        decision = "minor_revision"
        if report["citation_issues"]:
            decision = _decision_at_most(decision, "major_revision")
        if report["evidence_issues"] or report["figure_issues"] or report["statistical_issues"] or report["overclaims"]:
            decision = _decision_at_most(decision, "major_revision")
        if report["metadata_issues"] and pdf_records and len(low_quality_pdf_records) == len(pdf_records):
            decision = _decision_at_most(decision, "major_revision")
        if len(evidence) < 3 or missing_evidence_ids:
            decision = _decision_at_most(decision, "major_revision")
        if any(item.get("severity") == "major" for item in sentence_issues):
            decision = _decision_at_most(decision, "major_revision")
        if not manuscript or (not evidence and not figures and not analysis):
            decision = "reject"
        report["overall_decision"] = decision

        markdown = f"""# 审稿报告

## Overall Decision

{report["overall_decision"]}

## Major Issues

{chr(10).join(f"- {item}" for item in report["major_issues"]) or "- 暂无。"}

## Citation Issues

{chr(10).join(f"- {item}" for item in report["citation_issues"]) or "- 暂无。"}

## Metadata Issues

{chr(10).join(f"- {item}" for item in report["metadata_issues"]) or "- 暂无。"}

## Evidence Issues

{chr(10).join(f"- {item}" for item in report["evidence_issues"]) or "- 暂无。"}

## Figure Issues

{chr(10).join(f"- {item}" for item in report["figure_issues"]) or "- 暂无。"}

## Statistical Issues

{chr(10).join(f"- {item}" for item in report["statistical_issues"]) or "- 暂无。"}

## Sentence Issues

{chr(10).join(f"- {item['issue_id']} [{item['severity']}] {item['section']}: {item['issue_type']} - {item['sentence']}" for item in report["sentence_issues"]) or "- 暂无。"}

## Overclaims

{chr(10).join(f"- {item}" for item in report["overclaims"]) or "- 未发现。"}

## Consistency Checks

{chr(10).join(f"- {item}" for item in report["consistency_checks"]) or "- 暂无。"}

## Recommended Revisions

{chr(10).join(f"- {item}" for item in report["recommended_revisions"])}
"""
        state.review_report = report
        self.save_output(state, "reviews/review_report.json", report, "review", "审稿报告 JSON")
        self.save_output(state, "reviews/review_report.md", markdown, "review", "审稿报告 Markdown")
        return state
