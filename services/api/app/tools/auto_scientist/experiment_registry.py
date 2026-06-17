from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Callable

from app.tools.auto_scientist.contracts import REGISTERED_EXPERIMENT_NOTICE, utc_now
from app.tools.auto_scientist.generated_code_sandbox import GENERATED_CODE_TEMPLATE
from app.tools.claim_audit import run_draft_claim_audit
from app.tools.literature_rag import ask_literature_rag, read_rag_chunks
from app.tools.paper_writer.citation_binder import available_evidence_summary
from app.tools.paper_writer.writer_eval import evaluate_auto_paper_draft

ExperimentFn = Callable[[Path, str, dict[str, Any]], dict[str, Any]]


def _small_svg_bar(title: str, values: dict[str, int]) -> str:
    labels = list(values)
    max_value = max(values.values(), default=1) or 1
    width = 520
    height = 80 + len(labels) * 36
    rows = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-label="{title}">',
        f'<title>{title}</title>',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="16" y="28" font-family="sans-serif" font-size="16" font-weight="600">{title}</text>',
    ]
    y = 58
    for label in labels:
        value = values[label]
        bar_width = int((value / max_value) * 300) if max_value else 0
        rows.append(f'<text x="16" y="{y + 14}" font-family="sans-serif" font-size="12">{label}</text>')
        rows.append(f'<rect x="180" y="{y}" width="{bar_width}" height="20" fill="#64748b"/>')
        rows.append(f'<text x="{190 + bar_width}" y="{y + 14}" font-family="sans-serif" font-size="12">{value}</text>')
        y += 36
    rows.append('</svg>')
    return "\n".join(rows)


def evidence_inventory(project_dir: Path, project_id: str, config: dict[str, Any]) -> dict[str, Any]:
    summary = available_evidence_summary(project_dir, project_id)
    chunks = read_rag_chunks(project_dir)
    warning_counts = Counter(
        flag
        for chunk in chunks
        for flag in (chunk.get("evidence_warning_flags") or [])
        if isinstance(flag, str)
    )
    metadata_counts = Counter(str(chunk.get("metadata_trust_level") or "unknown") for chunk in chunks)
    metrics = {
        **summary,
        "chunk_warning_counts": dict(warning_counts),
        "metadata_trust_counts": dict(metadata_counts),
        "registered_safe_template": True,
    }
    return {
        "status": "completed",
        "metrics": metrics,
        "claims": [
            {
                "claim": "The local evidence inventory can be summarized from project artifacts.",
                "support_status": "supported" if summary.get("rag_chunk_count", 0) else "unsupported",
                "evidence": summary.get("artifact_paths", []),
            }
        ],
        "figure_svg": _small_svg_bar(
            "RAG metadata trust counts", {k: int(v) for k, v in metadata_counts.items()}
        ),
        "summary_markdown": (
            "# Evidence inventory\n\n"
            f"{REGISTERED_EXPERIMENT_NOTICE}\n\n"
            f"- Literature records: {summary.get('literature_count', 0)}\n"
            f"- RAG chunks: {summary.get('rag_chunk_count', 0)}\n"
            f"- Analysis available: {bool(summary.get('analysis_available'))}\n"
        ),
    }


def rag_retrieval_eval(project_dir: Path, project_id: str, config: dict[str, Any]) -> dict[str, Any]:
    question = str(config.get("question") or config.get("research_question") or "What does the local evidence support?")
    retrieval_mode = str(config.get("retrieval_mode") or "local_hybrid_fts")
    answer = ask_literature_rag(project_dir, project_id, question, top_k=5, retrieval_mode=retrieval_mode)
    passages = answer.get("source_passages") or []
    top_score = max((float(p.get("score") or 0) for p in passages if isinstance(p, dict)), default=0.0)
    metrics = {
        "question": question,
        "retrieval_mode": retrieval_mode,
        "source_passage_count": len(passages),
        "top_source_score": top_score,
        "answer_support_status": answer.get("answer_support_status"),
    }
    return {
        "status": "completed",
        "metrics": metrics,
        "claims": [
            {
                "claim": "The retrieval experiment returned local source passages for the research question.",
                "support_status": answer.get("answer_support_status", "unsupported"),
                "evidence": [p.get("source_locator") or p.get("chunk_id") for p in passages if isinstance(p, dict)],
            }
        ],
        "summary_markdown": (
            "# RAG retrieval evaluation\n\n"
            f"{REGISTERED_EXPERIMENT_NOTICE}\n\n"
            f"- Question: {question}\n"
            f"- Support status: {answer.get('answer_support_status')}\n"
            f"- Source passages: {len(passages)}\n"
            f"- Top score: {top_score}\n"
        ),
    }


def claim_audit_eval(project_dir: Path, project_id: str, config: dict[str, Any]) -> dict[str, Any]:
    manuscript_relative_path = str(config.get("manuscript_relative_path") or "manuscript/draft_full.md")
    if not (project_dir / manuscript_relative_path).exists():
        manuscript_relative_path = "manuscript/draft.md"
    if not (project_dir / manuscript_relative_path).exists():
        return {
            "status": "skipped",
            "metrics": {"reason": "no manuscript markdown available"},
            "claims": [],
            "summary_markdown": "# Claim audit evaluation\n\nSkipped because no manuscript markdown is available.\n",
        }
    payload = run_draft_claim_audit(
        project_dir,
        project_id,
        manuscript_relative_path=manuscript_relative_path,
        retrieval_mode=str(config.get("retrieval_mode") or "local_hybrid_fts"),
        top_k=5,
    )
    summary = payload.get("summary") or {}
    metrics = {
        "manuscript_relative_path": manuscript_relative_path,
        "claim_count": summary.get("claim_count", 0),
        "supported": summary.get("supported", 0),
        "weakly_supported": summary.get("weakly_supported", 0),
        "unsupported": summary.get("unsupported", 0),
    }
    return {
        "status": "completed",
        "metrics": metrics,
        "claims": [
            {
                "claim": f"The manuscript contains {metrics['claim_count']} auditable claim-like sentences.",
                "support_status": "supported" if metrics["claim_count"] else "unsupported",
                "evidence": [payload.get("claim_audit_file")],
            }
        ],
        "summary_markdown": (
            "# Claim audit evaluation\n\n"
            f"{REGISTERED_EXPERIMENT_NOTICE}\n\n"
            f"- Manuscript: {manuscript_relative_path}\n"
            f"- Claims: {metrics['claim_count']}\n"
            f"- Unsupported: {metrics['unsupported']}\n"
        ),
    }


def descriptive_data_profile(project_dir: Path, project_id: str, config: dict[str, Any]) -> dict[str, Any]:
    data_dir = project_dir / "data"
    csv_files = sorted(data_dir.glob("*.csv")) if data_dir.exists() else []
    profiles: list[dict[str, Any]] = []
    for csv_path in csv_files[:5]:
        try:
            with csv_path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
        except Exception:
            rows = []
        columns = list(rows[0].keys()) if rows else []
        numeric_columns: list[str] = []
        for column in columns:
            values: list[float] = []
            for row in rows:
                value = (row.get(column) or "").strip()
                if not value:
                    continue
                try:
                    values.append(float(value))
                except ValueError:
                    values = []
                    break
            if values:
                numeric_columns.append(column)
        profiles.append(
            {
                "source_file": csv_path.relative_to(project_dir).as_posix(),
                "row_count": len(rows),
                "column_count": len(columns),
                "numeric_columns": numeric_columns,
                "numeric_column_count": len(numeric_columns),
            }
        )
    totals = {
        "csv_file_count": len(csv_files),
        "profiled_file_count": len(profiles),
        "total_rows_profiled": sum(int(item["row_count"]) for item in profiles),
        "average_numeric_columns": round(mean([int(item["numeric_column_count"]) for item in profiles]) if profiles else 0.0, 3),
    }
    return {
        "status": "completed" if profiles else "skipped",
        "metrics": {"totals": totals, "profiles": profiles},
        "claims": [
            {
                "claim": "Local CSV artifacts were profiled descriptively without inferential statistics.",
                "support_status": "supported" if profiles else "unsupported",
                "evidence": [item["source_file"] for item in profiles],
            }
        ],
        "figure_svg": _small_svg_bar(
            "Rows per profiled CSV", {Path(item["source_file"]).name: int(item["row_count"]) for item in profiles}
        ) if profiles else None,
        "summary_markdown": (
            "# Descriptive data profile\n\n"
            f"{REGISTERED_EXPERIMENT_NOTICE}\n\n"
            f"- CSV files: {len(csv_files)}\n"
            f"- Profiled files: {len(profiles)}\n"
            "- No p-values, significance, or causal inference were generated.\n"
        ),
    }


def writing_safety_eval(project_dir: Path, project_id: str, config: dict[str, Any]) -> dict[str, Any]:
    safety = evaluate_auto_paper_draft(project_dir)
    hits = safety.get("restricted_term_hits") or []
    metrics = {
        "has_ai_generated_notice": bool(safety.get("has_ai_generated_notice")),
        "restricted_term_count": len(hits),
        "restricted_term_hits": hits,
        "human_review_required": True,
    }
    return {
        "status": "completed",
        "metrics": metrics,
        "claims": [
            {
                "claim": "The generated manuscript draft passed the restricted-term safety smoke check.",
                "support_status": "supported" if not hits and metrics["has_ai_generated_notice"] else "weakly_supported",
                "evidence": ["manuscript/writing_audit.json", "manuscript/draft_full.md"],
            }
        ],
        "summary_markdown": (
            "# Writing safety evaluation\n\n"
            f"{REGISTERED_EXPERIMENT_NOTICE}\n\n"
            f"- AI-generated notice: {metrics['has_ai_generated_notice']}\n"
            f"- Restricted term hits: {len(hits)}\n"
        ),
    }


EXPERIMENT_REGISTRY: dict[str, ExperimentFn] = {
    "evidence_inventory": evidence_inventory,
    "rag_retrieval_eval": rag_retrieval_eval,
    "claim_audit_eval": claim_audit_eval,
    "descriptive_data_profile": descriptive_data_profile,
    "writing_safety_eval": writing_safety_eval,
}


def registered_experiment_templates(include_generated_code: bool = False) -> list[str]:
    templates = sorted(EXPERIMENT_REGISTRY)
    if include_generated_code:
        templates.append(GENERATED_CODE_TEMPLATE)
    return sorted(set(templates))


def run_registered_experiment(
    project_dir: Path,
    project_id: str,
    template_name: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    if template_name == GENERATED_CODE_TEMPLATE:
        raise ValueError("generated-code experiments must be executed by the sandbox manager")
    if template_name not in EXPERIMENT_REGISTRY:
        raise ValueError(f"unsupported safe experiment template: {template_name}")
    result = EXPERIMENT_REGISTRY[template_name](project_dir, project_id, config)
    result.setdefault("status", "completed")
    result["template_name"] = template_name
    result["created_at"] = utc_now()
    result["arbitrary_code_execution"] = False
    result["registered_safe_template"] = True
    return result
