from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.bibtex_generator import generate_bibtex
from app.tools.file_tools import ensure_dir, write_json, write_text
from app.tools.literature_index import load_literature_index
from app.tools.paper_writer.citation_binder import retrieve_section_passages
from app.tools.manuscript_references import generate_manuscript_references

PAPER_CITATION_BINDINGS_JSON = "manuscript/paper_citation_bindings.json"
PAPER_CITATION_BINDINGS_MD = "manuscript/paper_citation_bindings.md"
LATEST_PAPER_CITATION_BINDING_JSON = "manuscript/latest_paper_citation_binding.json"
CITATION_BOUND_AUTOSCIENTIST_MD = "manuscript/auto_scientist_paper_citation_bound.md"

CLAIM_SECTIONS = {
    "abstract",
    "introduction",
    "background",
    "related work",
    "methods",
    "results",
    "discussion",
    "limitations",
    "conclusion",
    "experiment tree best candidate",
    "selected experiment node interpretation",
}

CLAIM_MARKERS = {
    "show",
    "shows",
    "showed",
    "suggest",
    "suggests",
    "indicate",
    "indicates",
    "evidence",
    "result",
    "results",
    "metric",
    "metrics",
    "experiment",
    "experiments",
    "method",
    "model",
    "dataset",
    "study",
    "studies",
    "paper",
    "literature",
    "finding",
    "findings",
    "support",
    "supports",
    "demonstrate",
    "demonstrates",
    "improve",
    "improves",
    "risk",
    "risks",
    "claim",
    "claims",
    "表明",
    "显示",
    "结果",
    "实验",
    "证据",
    "支持",
    "研究",
}

SEVERE_PASSAGE_FLAGS = {"failed_or_empty_parse", "low_parser_quality"}
UNVERIFIED_TRUST = {"placeholder_or_unverified", "unknown", None}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _safe_relative_markdown(relative_path: str | None) -> str:
    if not relative_path:
        return _default_manuscript_path_name()
    cleaned = relative_path.strip().replace("\\", "/").lstrip("/")
    if not cleaned or ".." in cleaned.split("/"):
        raise ValueError("manuscript_relative_path must stay inside project")
    if not cleaned.startswith("manuscript/") or not cleaned.endswith(".md"):
        raise ValueError("manuscript_relative_path must be a Markdown file under manuscript/")
    return cleaned


def _default_manuscript_path_name() -> str:
    return "manuscript/auto_scientist_paper_revised.md"


def _select_manuscript(project_dir: Path, manuscript_relative_path: str | None = None) -> str:
    if manuscript_relative_path:
        selected = _safe_relative_markdown(manuscript_relative_path)
        if not (project_dir / selected).exists():
            raise FileNotFoundError(f"manuscript file does not exist: {selected}")
        return selected
    for candidate in [
        "manuscript/auto_scientist_paper_revised.md",
        "manuscript/auto_scientist_paper.md",
        "manuscript/draft_full.md",
        "manuscript/draft.md",
    ]:
        if (project_dir / candidate).exists():
            return candidate
    raise FileNotFoundError("No manuscript Markdown artifact exists to bind citations")


def _split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip().strip("-* ")
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _extract_manuscript_sentences(markdown: str) -> list[dict[str, Any]]:
    current_section = "Manuscript"
    paragraph_lines: list[str] = []
    paragraph_index = 0
    rows: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal paragraph_index, paragraph_lines
        if not paragraph_lines:
            return
        paragraph = " ".join(paragraph_lines).strip()
        paragraph_lines = []
        if not paragraph:
            return
        paragraph_index += 1
        for sentence_index, sentence in enumerate(_split_sentences(paragraph), start=1):
            rows.append(
                {
                    "section": current_section,
                    "paragraph_index": paragraph_index,
                    "sentence_index": sentence_index,
                    "sentence": sentence,
                }
            )

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            flush()
            current_section = heading.group(2).strip().strip("#") or "Manuscript"
            paragraph_index = 0
            continue
        if not line:
            flush()
            continue
        if line.startswith("|") or line.startswith("```"):
            continue
        if line.startswith(">"):
            line = line.lstrip("> ").strip()
        if line.startswith("%"):
            continue
        paragraph_lines.append(line)
    flush()
    return rows


def _claim_like(section: str, sentence: str) -> bool:
    lower = sentence.lower()
    if len(sentence) < 45:
        return False
    if "ai-generated draft" in lower or "requires human review" in lower:
        return False
    if "not scientific proof" in lower or "not peer review" in lower:
        return False
    if "todo:" in lower:
        return True
    tokens = set(re.findall(r"[a-zA-Z][a-zA-Z_-]{2,}|[\u4e00-\u9fff]+", lower))
    if tokens & CLAIM_MARKERS:
        return True
    if section.lower().strip() in CLAIM_SECTIONS and len(sentence) >= 80:
        return True
    return False


def _literature_map(project_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("literature_id")): entry
        for entry in load_literature_index(project_dir)
        if isinstance(entry, dict) and entry.get("literature_id")
    }


def _approved_reference_keys(project_dir: Path, project_id: str) -> dict[str, str]:
    # Reuse the approved-reference-only BibTeX generator so citation binding
    # never fabricates formal reference keys from unapproved metadata.
    try:
        report = generate_bibtex(project_dir, project_id)
    except Exception:
        report = _read_json(project_dir / "literature" / "bibtex_report.json", {})
    result: dict[str, str] = {}
    if isinstance(report, dict):
        for item in report.get("written", []):
            if isinstance(item, dict) and item.get("literature_id") and item.get("entry_key"):
                result[str(item["literature_id"])] = str(item["entry_key"])
    return result


def _passage_flags(passages: list[dict[str, Any]]) -> set[str]:
    return {
        str(flag)
        for passage in passages
        for flag in (passage.get("evidence_warning_flags") or [])
        if isinstance(flag, str)
    }


def _binding_status(passages: list[dict[str, Any]]) -> str:
    if not passages:
        return "unbound"
    best_score = max(float(passage.get("score") or 0.0) for passage in passages)
    flags = _passage_flags(passages)
    all_unverified = all(passage.get("metadata_trust_level") in UNVERIFIED_TRUST for passage in passages)
    if best_score >= 0.45 and not all_unverified and not (flags & SEVERE_PASSAGE_FLAGS):
        return "bound"
    return "weak_binding"


def _citation_status(passages: list[dict[str, Any]], approved_keys: dict[str, str]) -> str:
    if not passages:
        return "missing_source_passage"
    literature_ids = {str(passage.get("literature_id")) for passage in passages if passage.get("literature_id")}
    if literature_ids & set(approved_keys):
        return "formal_reference_available"
    return "source_passage_only"


def _warning_flags(
    binding_status: str,
    citation_status: str,
    passages: list[dict[str, Any]],
    literature_entries: dict[str, dict[str, Any]],
) -> list[str]:
    flags = set(_passage_flags(passages))
    if binding_status == "unbound":
        flags.add("missing_source_passage")
    if binding_status == "weak_binding":
        flags.add("weak_source_passage_binding")
    if citation_status == "source_passage_only":
        flags.add("no_formal_reference_available")
    for passage in passages:
        literature_id = str(passage.get("literature_id") or "")
        entry = literature_entries.get(literature_id, {})
        if entry and not (
            entry.get("metadata_status") == "verified"
            and entry.get("human_verified") is True
            and entry.get("reference_verification_status") == "approved"
        ):
            flags.add("reference_not_approved")
    return sorted(flags)


def _recommended_action(binding_status: str, citation_status: str, flags: list[str]) -> str:
    if binding_status == "unbound":
        return "add_source_or_rewrite_as_limitation"
    if citation_status != "formal_reference_available":
        return "review_source_passage_and_approve_reference_before_formal_citation"
    if flags:
        return "review_binding_before_external_use"
    return "keep_with_formal_reference_after_human_review"


def _markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Paper Citation Bindings",
        "",
        "> Local citation/source-passage bindings are workflow evidence, not citation verification, peer review, or scientific proof.",
        "",
        "## Summary",
        "",
    ]
    summary = payload.get("summary", {})
    for key in [
        "total_sentences_checked",
        "claim_like_sentences",
        "bound",
        "weak_binding",
        "unbound",
        "formal_reference_available",
        "source_passage_only",
        "human_review_required",
    ]:
        lines.append(f"- {key}: {summary.get(key, 0)}")
    lines.extend(["", "## Bindings", ""])
    for item in payload.get("bindings", []):
        if not isinstance(item, dict) or not item.get("claim_like"):
            continue
        marker = item.get("suggested_citation_marker") or "no marker"
        lines.extend(
            [
                f"### {item.get('citation_binding_id')}",
                "",
                f"- Section: {item.get('section')}",
                f"- Binding status: {item.get('binding_status')}",
                f"- Citation support status: {item.get('citation_support_status')}",
                f"- Suggested marker: `{marker}`",
                f"- Human review required: {item.get('human_review_required')}",
                f"- Recommended action: {item.get('recommended_action')}",
                f"- Sentence: {item.get('sentence')}",
                "",
            ]
        )
        for passage in item.get("matched_source_passages", [])[:3]:
            if isinstance(passage, dict):
                lines.append(
                    f"  - {passage.get('chunk_id')} / {passage.get('source_locator') or passage.get('source_file')} / score={passage.get('score')}"
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _citation_bound_copy(original_markdown: str, payload: dict[str, Any]) -> str:
    lines = [
        "# Citation-bound Auto Scientist Draft Copy",
        "",
        "> This copy preserves the generated manuscript and appends local source/citation suggestions. It is not submission-ready and requires human citation review.",
        "",
        original_markdown.rstrip(),
        "",
        "# ResearchAgent Citation Binding Appendix",
        "",
    ]
    for item in payload.get("bindings", []):
        if not isinstance(item, dict) or not item.get("claim_like"):
            continue
        marker = item.get("suggested_citation_marker") or "[missing-source]"
        lines.extend(
            [
                f"- {item.get('citation_binding_id')}: {marker}; status={item.get('binding_status')}; citation_status={item.get('citation_support_status')}; action={item.get('recommended_action')}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def generate_paper_citation_bindings(
    project_dir: Path,
    project_id: str,
    manuscript_relative_path: str | None = None,
    retrieval_mode: str = "local_hybrid_fts",
    top_k: int = 3,
) -> dict[str, Any]:
    ensure_dir(project_dir / "manuscript")
    selected_manuscript = _select_manuscript(project_dir, manuscript_relative_path)
    manuscript_path = project_dir / selected_manuscript
    markdown = manuscript_path.read_text(encoding="utf-8", errors="replace")
    sentences = _extract_manuscript_sentences(markdown)
    approved_keys = _approved_reference_keys(project_dir, project_id)
    literature_entries = _literature_map(project_dir)
    references_status = generate_manuscript_references(project_dir, project_id)
    bindings: list[dict[str, Any]] = []

    for index, row in enumerate(sentences, start=1):
        sentence = str(row["sentence"])
        claim_like = _claim_like(str(row["section"]), sentence)
        passages: list[dict[str, Any]] = []
        if claim_like:
            passages = retrieve_section_passages(
                project_dir,
                project_id,
                sentence,
                top_k=top_k,
                retrieval_mode=retrieval_mode,
            )
        binding_status = _binding_status(passages) if claim_like else "not_citation_claim"
        citation_status = _citation_status(passages, approved_keys) if claim_like else "not_applicable"
        formal_ids = [
            str(passage.get("literature_id"))
            for passage in passages
            if passage.get("literature_id") and str(passage.get("literature_id")) in approved_keys
        ]
        markers = [f"\\cite{{{approved_keys[literature_id]}}}" for literature_id in sorted(set(formal_ids))]
        if not markers and passages:
            markers = [f"[source:{passages[0].get('chunk_id')}]" if passages[0].get("chunk_id") else "[source-passage]"]
        flags = _warning_flags(binding_status, citation_status, passages, literature_entries) if claim_like else []
        human_review_required = bool(claim_like and (binding_status != "bound" or citation_status != "formal_reference_available" or flags))
        bindings.append(
            {
                "citation_binding_id": f"citation_binding_{index:04d}",
                "manuscript_file": selected_manuscript,
                "section": row["section"],
                "paragraph_index": row["paragraph_index"],
                "sentence_index": row["sentence_index"],
                "sentence": sentence,
                "claim_like": claim_like,
                "binding_status": binding_status,
                "citation_support_status": citation_status,
                "matched_source_passages": passages,
                "literature_ids": sorted({str(p.get("literature_id")) for p in passages if p.get("literature_id")}),
                "formal_reference_literature_ids": sorted(set(formal_ids)),
                "suggested_citation_marker": "; ".join(markers),
                "citation_warning_flags": flags,
                "human_review_required": human_review_required,
                "recommended_action": _recommended_action(binding_status, citation_status, flags) if claim_like else "none",
            }
        )

    claim_bindings = [item for item in bindings if item.get("claim_like")]
    payload = {
        "schema_version": "researchagent.auto_scientist.paper_citation_binding.v1",
        "project_id": project_id,
        "generated_at": _utc_now(),
        "manuscript_file": selected_manuscript,
        "binding_file": PAPER_CITATION_BINDINGS_JSON,
        "binding_markdown_file": PAPER_CITATION_BINDINGS_MD,
        "citation_bound_draft_file": CITATION_BOUND_AUTOSCIENTIST_MD,
        "retrieval_mode": retrieval_mode,
        "top_k": top_k,
        "references_status_file": references_status.get("relative_path"),
        "bibtex_file": "literature/references.bib",
        "formal_reference_count": len(approved_keys),
        "bindings": bindings,
        "summary": {
            "total_sentences_checked": len(bindings),
            "claim_like_sentences": len(claim_bindings),
            "bound": sum(1 for item in claim_bindings if item.get("binding_status") == "bound"),
            "weak_binding": sum(1 for item in claim_bindings if item.get("binding_status") == "weak_binding"),
            "unbound": sum(1 for item in claim_bindings if item.get("binding_status") == "unbound"),
            "formal_reference_available": sum(1 for item in claim_bindings if item.get("citation_support_status") == "formal_reference_available"),
            "source_passage_only": sum(1 for item in claim_bindings if item.get("citation_support_status") == "source_passage_only"),
            "missing_source_passage": sum(1 for item in claim_bindings if item.get("citation_support_status") == "missing_source_passage"),
            "human_review_required": sum(1 for item in claim_bindings if item.get("human_review_required")),
        },
        "limitations": [
            "Citation binding uses local source-passage retrieval and approved-reference metadata only.",
            "Source-passage suggestions are not formal citation verification.",
            "Formal LaTeX citation markers are emitted only when BibTeX entries are approved by the local reference workflow.",
        ],
    }
    write_json(project_dir / PAPER_CITATION_BINDINGS_JSON, payload)
    write_json(project_dir / LATEST_PAPER_CITATION_BINDING_JSON, payload)
    write_text(project_dir / PAPER_CITATION_BINDINGS_MD, _markdown_report(payload))
    write_text(project_dir / CITATION_BOUND_AUTOSCIENTIST_MD, _citation_bound_copy(markdown, payload))
    append_audit_event(
        project_dir,
        project_id,
        "generate_paper_citation_bindings",
        "Auto Scientist manuscript citation/source-passage bindings were generated.",
        {
            "binding_file": PAPER_CITATION_BINDINGS_JSON,
            "manuscript_file": selected_manuscript,
            "claim_like_sentences": payload["summary"]["claim_like_sentences"],
            "human_review_required": payload["summary"]["human_review_required"],
        },
        source="api",
        event_category="manuscript",
        risk_level="medium" if payload["summary"]["human_review_required"] else "low",
        entity_type="manuscript",
        entity_id="paper_citation_bindings",
    )
    return payload


def read_paper_citation_bindings(project_dir: Path) -> dict[str, Any]:
    payload = _read_json(project_dir / PAPER_CITATION_BINDINGS_JSON, {})
    return payload if isinstance(payload, dict) else {}
