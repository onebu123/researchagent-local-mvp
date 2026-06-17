from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.auto_scientist.contracts import (
    EXPERIMENT_TREE_JSON,
    LATEST_RUN_JSON,
    RUNS_JSONL,
    SCHEMA_PREFIX,
    read_json,
    read_jsonl,
    safe_id,
    utc_now,
    write_project_json,
    write_project_text,
)

EXPERIMENT_CLAIM_BINDINGS_JSON = "auto_scientist/experiment_claim_bindings.json"
EXPERIMENT_CLAIM_BINDINGS_MD = "auto_scientist/experiment_claim_bindings.md"
LATEST_EXPERIMENT_CLAIM_BINDING_JSON = "auto_scientist/latest_experiment_claim_binding.json"
MANUSCRIPT_CLAIM_TRACE_JSONL = "auto_scientist/manuscript_claim_trace.jsonl"

DEFAULT_MANUSCRIPT_CANDIDATES = [
    "manuscript/auto_scientist_paper_revised.md",
    "manuscript/auto_scientist_paper.md",
    "manuscript/draft_full.md",
]
CLAIM_SECTIONS = {
    "abstract",
    "methods",
    "results",
    "discussion",
    "evidence-bound claims",
    "experiment tree best candidate",
    "selected experiment node interpretation",
    "limitations",
    "conclusion",
}
CLAIM_HINTS = {
    "experiment", "experiments", "result", "results", "metric", "metrics", "score", "node", "template",
    "claim", "claims", "support", "supported", "unsupported", "evidence", "artifact", "output", "outputs",
    "status", "tree", "selected", "best", "heuristic", "sandbox", "generated-code", "diagnostic",
    "retrieval", "ablation", "profile", "matrix", "data", "figure",
}
ADMIN_HINTS = {
    "requires human review", "not scientific proof", "not peer review", "not publication readiness",
    "placeholder references", "limitations",
}


def read_experiment_claim_bindings(project_dir: Path) -> dict[str, Any]:
    payload = read_json(project_dir / EXPERIMENT_CLAIM_BINDINGS_JSON, {})
    return payload if isinstance(payload, dict) else {}


def _read_text(project_dir: Path, relative_path: str) -> str:
    path = project_dir / relative_path
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _resolve_manuscript(project_dir: Path, manuscript_relative_path: str | None) -> tuple[str, str]:
    if manuscript_relative_path:
        normalized = manuscript_relative_path.replace("\\", "/").lstrip("/")
        if ".." in normalized.split("/") or not normalized.endswith(".md"):
            raise ValueError("manuscript_relative_path must be a project-relative markdown file")
        text = _read_text(project_dir, normalized)
        if not text:
            raise FileNotFoundError(normalized)
        return normalized, text
    for candidate in DEFAULT_MANUSCRIPT_CANDIDATES:
        text = _read_text(project_dir, candidate)
        if text:
            return candidate, text
    raise FileNotFoundError("no Auto Scientist manuscript draft is available")


def _split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip().strip("-* ")
    if not cleaned:
        return []
    return [item.strip() for item in re.split(r"(?<=[.!?。！？])\s+", cleaned) if item.strip()]


def _section_sentences(markdown: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current_section = "Preamble"
    section_lines: list[str] = []

    def flush() -> None:
        nonlocal section_lines
        paragraph_index = 1
        for raw in "\n".join(section_lines).split("\n\n"):
            paragraph = raw.strip()
            if not paragraph:
                continue
            lines = []
            for line in paragraph.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped.startswith(">"):
                    continue
                lines.append(stripped)
            sentence_index = 1
            for sentence in _split_sentences(" ".join(lines)):
                records.append(
                    {
                        "section": current_section,
                        "paragraph_index": paragraph_index,
                        "sentence_index": sentence_index,
                        "sentence": sentence,
                    }
                )
                sentence_index += 1
            paragraph_index += 1
        section_lines = []

    for line in markdown.splitlines():
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if heading:
            flush()
            current_section = heading.group(1).strip()
        else:
            section_lines.append(line)
    flush()
    return records


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9_][A-Za-z0-9_-]{2,}", text)}


def _is_claim_like(record: dict[str, Any]) -> bool:
    sentence = str(record.get("sentence") or "")
    section = str(record.get("section") or "").strip().lower()
    lower = sentence.lower()
    if len(sentence) < 35:
        return False
    return section in CLAIM_SECTIONS or any(hint in lower for hint in CLAIM_HINTS)


def _support_from_claims(claims: list[dict[str, Any]]) -> str:
    statuses = {str(item.get("support_status") or "needs_human_review") for item in claims if isinstance(item, dict)}
    if "supported" in statuses:
        return "supported"
    if "weakly_supported" in statuses or "partial" in statuses:
        return "weakly_supported"
    if "unsupported" in statuses:
        return "unsupported"
    return "weakly_supported" if claims else "weakly_supported"


def _tree_payload(project_dir: Path) -> dict[str, Any]:
    payload = read_json(project_dir / EXPERIMENT_TREE_JSON, {})
    return payload if isinstance(payload, dict) else {}


def _collect_experiment_records(project_dir: Path) -> list[dict[str, Any]]:
    tree = _tree_payload(project_dir)
    nodes_by_experiment: dict[str, dict[str, Any]] = {}
    nodes_by_id: dict[str, dict[str, Any]] = {}
    for node in tree.get("nodes", []) if isinstance(tree.get("nodes"), list) else []:
        if not isinstance(node, dict):
            continue
        if isinstance(node.get("experiment_id"), str):
            nodes_by_experiment[node["experiment_id"]] = node
        if isinstance(node.get("node_id"), str):
            nodes_by_id[node["node_id"]] = node
    records: list[dict[str, Any]] = []
    for result_path in sorted((project_dir / "auto_scientist" / "experiments").glob("**/experiment_result.json")):
        result = read_json(result_path, {})
        if not isinstance(result, dict):
            continue
        experiment_id = str(result.get("experiment_id") or result_path.parent.name)
        node = nodes_by_experiment.get(experiment_id, {})
        output_files: list[str] = []
        if isinstance(node.get("output_files"), list):
            output_files.extend(str(item) for item in node.get("output_files", []) if isinstance(item, str))
        for path in sorted(result_path.parent.glob("*")):
            if path.is_file():
                try:
                    rel = path.relative_to(project_dir).as_posix()
                except ValueError:
                    continue
                if rel not in output_files:
                    output_files.append(rel)
        metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
        claims = [item for item in result.get("claims", []) if isinstance(item, dict)] if isinstance(result.get("claims"), list) else []
        records.append(
            {
                "experiment_id": experiment_id,
                "node_id": node.get("node_id"),
                "template_name": result.get("template_name") or node.get("template_name"),
                "status": result.get("status") or node.get("status"),
                "score": node.get("score"),
                "generated_code_execution": bool(result.get("generated_code_execution") or node.get("generated_code_execution")),
                "source_hash": result.get("source_hash") or node.get("source_hash"),
                "metrics": metrics,
                "metric_keys": sorted(str(key) for key in metrics.keys()) if isinstance(metrics, dict) else [],
                "claims": claims,
                "output_files": output_files,
                "result_file": result_path.relative_to(project_dir).as_posix(),
                "support_status": _support_from_claims(claims),
                "node": node,
            }
        )
    existing_experiments = {str(item.get("experiment_id")) for item in records}
    for node_id, node in nodes_by_id.items():
        experiment_id = str(node.get("experiment_id") or node_id)
        if experiment_id in existing_experiments:
            continue
        records.append(
            {
                "experiment_id": experiment_id,
                "node_id": node_id,
                "template_name": node.get("template_name"),
                "status": node.get("status"),
                "score": node.get("score"),
                "generated_code_execution": bool(node.get("generated_code_execution")),
                "source_hash": node.get("source_hash"),
                "metrics": {},
                "metric_keys": node.get("metric_keys", []) if isinstance(node.get("metric_keys"), list) else [],
                "claims": [],
                "output_files": node.get("output_files", []) if isinstance(node.get("output_files"), list) else [],
                "result_file": None,
                "support_status": "weakly_supported",
                "node": node,
            }
        )
    # Add a fallback from runs.jsonl for non-tree runs.
    for run_record in read_jsonl(project_dir, RUNS_JSONL):
        if not isinstance(run_record, dict):
            continue
        experiment_id = str(run_record.get("experiment_id") or "")
        if not experiment_id or experiment_id in existing_experiments:
            continue
        output_files = [item for item in run_record.get("output_files", []) if isinstance(item, str)] if isinstance(run_record.get("output_files"), list) else []
        result_file = next((item for item in output_files if item.endswith("experiment_result.json")), None)
        result = read_json(project_dir / result_file, {}) if result_file else {}
        metrics = result.get("metrics") if isinstance(result, dict) and isinstance(result.get("metrics"), dict) else {}
        claims = [item for item in result.get("claims", []) if isinstance(item, dict)] if isinstance(result, dict) and isinstance(result.get("claims"), list) else []
        records.append(
            {
                "experiment_id": experiment_id,
                "node_id": None,
                "template_name": run_record.get("template_name"),
                "status": run_record.get("status"),
                "score": None,
                "generated_code_execution": bool(run_record.get("generated_code_execution")),
                "source_hash": run_record.get("source_hash"),
                "metrics": metrics,
                "metric_keys": sorted(str(key) for key in metrics.keys()) if isinstance(metrics, dict) else [],
                "claims": claims,
                "output_files": output_files,
                "result_file": result_file,
                "support_status": _support_from_claims(claims),
                "node": {},
            }
        )
        existing_experiments.add(experiment_id)

    # Last-resort traceability fallback: older or interrupted Auto Scientist runs may
    # have manuscript/report artifacts but no per-experiment result files. Treat the
    # local artifact set itself as a weak experiment evidence record so manuscript
    # sentences can still be traced to concrete project-relative outputs instead of
    # silently producing an empty binding report. This is intentionally weak support,
    # not scientific proof.
    if not records:
        artifact_files: list[str] = []
        auto_scientist_dir = project_dir / "auto_scientist"
        if auto_scientist_dir.exists():
            for path in sorted(auto_scientist_dir.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".svg"}:
                    continue
                try:
                    artifact_files.append(path.relative_to(project_dir).as_posix())
                except ValueError:
                    continue
        for manuscript_path in [
            project_dir / "manuscript" / "auto_scientist_paper.md",
            project_dir / "manuscript" / "auto_scientist_paper_revised.md",
            project_dir / "manuscript" / "draft_full.md",
        ]:
            if manuscript_path.exists() and manuscript_path.is_file():
                try:
                    rel = manuscript_path.relative_to(project_dir).as_posix()
                except ValueError:
                    continue
                if rel not in artifact_files:
                    artifact_files.append(rel)
        if artifact_files:
            records.append(
                {
                    "experiment_id": "auto_scientist_local_artifact_index",
                    "node_id": None,
                    "template_name": "auto_scientist_artifact_index",
                    "status": "completed",
                    "score": None,
                    "generated_code_execution": False,
                    "source_hash": None,
                    "metrics": {"artifact_count": len(artifact_files)},
                    "metric_keys": ["artifact_count"],
                    "claims": [
                        {
                            "claim": "Auto Scientist produced local workflow artifacts that can be inspected for manuscript traceability.",
                            "support_status": "weakly_supported",
                        }
                    ],
                    "output_files": artifact_files,
                    "result_file": None,
                    "support_status": "weakly_supported",
                    "node": {},
                }
            )
    return records


def _selected_node_id(project_dir: Path, requested_node_id: str | None) -> str | None:
    if requested_node_id:
        return requested_node_id
    tree = _tree_payload(project_dir)
    selected = tree.get("selected_best_node_id")
    if isinstance(selected, str) and selected:
        return selected
    best = tree.get("best_node") if isinstance(tree.get("best_node"), dict) else None
    return str(best.get("node_id")) if best and best.get("node_id") else None


def _record_score(sentence: str, record: dict[str, Any]) -> tuple[float, list[str]]:
    lower = sentence.lower()
    matched: list[str] = []
    score = 0.0
    for field in ["node_id", "experiment_id", "template_name", "source_hash"]:
        value = record.get(field)
        if isinstance(value, str) and value and value.lower() in lower:
            score += 3.0
            matched.append(field)
    for key in record.get("metric_keys", []) if isinstance(record.get("metric_keys"), list) else []:
        if isinstance(key, str) and key and key.lower() in lower:
            score += 1.2
            matched.append(f"metric:{key}")
    for output_file in record.get("output_files", []) if isinstance(record.get("output_files"), list) else []:
        name = Path(str(output_file)).name.lower()
        if name and name in lower:
            score += 1.0
            matched.append("output_file")
            break
    sentence_tokens = _tokens(sentence)
    for claim in record.get("claims", []) if isinstance(record.get("claims"), list) else []:
        claim_text = str(claim.get("claim") or "")
        claim_tokens = _tokens(claim_text)
        if not claim_tokens:
            continue
        overlap = len(sentence_tokens & claim_tokens) / max(min(len(sentence_tokens), len(claim_tokens)), 1)
        if overlap >= 0.22:
            score += overlap * 2.0
            matched.append("result_claim_overlap")
            break
    if not matched:
        record_tokens = _tokens(" ".join(str(value) for value in [record.get("experiment_id"), record.get("template_name"), *(record.get("metric_keys", []) if isinstance(record.get("metric_keys"), list) else [])]))
        overlap = sentence_tokens & record_tokens
        if overlap:
            score += len(overlap) / max(len(sentence_tokens), 1)
            matched.append("token_overlap")
    return score, sorted(set(matched))


def _pick_binding(
    sentence: str,
    records: list[dict[str, Any]],
    selected_node_id: str | None,
    section: str,
) -> tuple[dict[str, Any] | None, float, list[str], bool]:
    best_record: dict[str, Any] | None = None
    best_score = 0.0
    best_matches: list[str] = []
    for record in records:
        score, matches = _record_score(sentence, record)
        if selected_node_id and record.get("node_id") == selected_node_id:
            score += 0.2
            if matches:
                matches.append("selected_node_boost")
        if score > best_score:
            best_score = score
            best_record = record
            best_matches = matches
    if best_record and best_score >= 0.35:
        return best_record, best_score, best_matches, False
    if section.lower() in {"results", "experiment tree best candidate", "selected experiment node interpretation", "evidence-bound claims"}:
        if selected_node_id:
            for record in records:
                if record.get("node_id") == selected_node_id:
                    return record, 0.75, ["selected_tree_node_fallback"], True
        completed = [record for record in records if record.get("status") == "completed"]
        if completed:
            chosen = max(completed, key=lambda item: float(item.get("score") or 0.0))
            return chosen, 0.5, ["section_fallback_best_completed_experiment"], True
    return best_record, best_score, best_matches, False


def _warnings(record: dict[str, Any] | None, fallback_used: bool, sentence: str) -> list[str]:
    if record is None:
        return ["no_experiment_result_binding"]
    warnings: list[str] = []
    lower = sentence.lower()
    if fallback_used:
        warnings.append("fallback_binding_requires_review")
    if record.get("status") != "completed":
        warnings.append("experiment_not_completed")
    if record.get("generated_code_execution"):
        warnings.append("generated_code_result_requires_sandbox_review")
    if not record.get("result_file"):
        warnings.append("missing_result_file")
    if any(hint in lower for hint in ADMIN_HINTS):
        warnings.append("limitation_or_boundary_statement")
    if not record.get("output_files"):
        warnings.append("no_output_artifacts_recorded")
    return sorted(set(warnings))


def _support_status(record: dict[str, Any] | None, warning_flags: list[str], is_claim_like: bool) -> tuple[str, str, bool, str]:
    if not is_claim_like:
        return "not_claim", "not_claim", False, "no_action_needed"
    if record is None:
        return "unsupported", "unbound", True, "add_experiment_artifact_or_rewrite_as_limitation"
    if "experiment_not_completed" in warning_flags or "no_experiment_result_binding" in warning_flags:
        return "unsupported", "weak_binding", True, "rerun_or_select_completed_experiment"
    status = str(record.get("support_status") or "weakly_supported")
    if status == "supported" and not warning_flags:
        return "supported", "bound", False, "keep_with_artifact_trace"
    if status == "unsupported":
        return "unsupported", "weak_binding", True, "add_experiment_artifact_or_rewrite_as_limitation"
    human_review_required = bool(warning_flags)
    return "weakly_supported", "weak_binding" if warning_flags else "bound", human_review_required, "review_artifact_binding_before_external_use"


def build_experiment_claim_bindings(
    project_dir: Path,
    project_id: str,
    manuscript_relative_path: str | None = None,
    node_id: str | None = None,
    reason: str = "",
) -> dict[str, Any]:
    manuscript_file, markdown = _resolve_manuscript(project_dir, manuscript_relative_path)
    records = _collect_experiment_records(project_dir)
    selected = _selected_node_id(project_dir, node_id)
    bindings: list[dict[str, Any]] = []
    for sentence_record in _section_sentences(markdown):
        sentence = str(sentence_record["sentence"])
        claim_like = _is_claim_like(sentence_record)
        record, score, matches, fallback_used = _pick_binding(sentence, records, selected, str(sentence_record.get("section") or ""))
        warning_flags = _warnings(record, fallback_used, sentence) if claim_like else []
        support_status, binding_status, human_review_required, recommended_action = _support_status(record, warning_flags, claim_like)
        if not claim_like and binding_status == "not_claim" and not any(hint in sentence.lower() for hint in ADMIN_HINTS):
            continue
        artifacts = []
        if record:
            for item in [record.get("result_file"), *(record.get("output_files", []) if isinstance(record.get("output_files"), list) else [])]:
                if isinstance(item, str) and item and item not in artifacts:
                    artifacts.append(item)
        bindings.append(
            {
                "binding_id": f"experiment_claim_binding_{len(bindings) + 1:04d}",
                "manuscript_file": manuscript_file,
                "section": sentence_record.get("section"),
                "paragraph_index": sentence_record.get("paragraph_index"),
                "sentence_index": sentence_record.get("sentence_index"),
                "sentence": sentence,
                "is_claim_like": claim_like,
                "claim_like": claim_like,
                "binding_status": binding_status,
                "claim_support_status": support_status,
                "experiment_node_id": record.get("node_id") if record else None,
                "matched_node_id": record.get("node_id") if record else None,
                "experiment_id": record.get("experiment_id") if record else None,
                "matched_experiment_id": record.get("experiment_id") if record else None,
                "bound_experiment_ids": [record.get("experiment_id")] if record and record.get("experiment_id") else [],
                "bound_tree_node_ids": [record.get("node_id")] if record and record.get("node_id") else [],
                "template_name": record.get("template_name") if record else None,
                "matched_template_name": record.get("template_name") if record else None,
                "result_status": record.get("status") if record else None,
                "result_file": record.get("result_file") if record else None,
                "metric_keys": record.get("metric_keys", []) if record else [],
                "output_files": record.get("output_files", []) if record else [],
                "source_artifacts": {
                    "experiment_result_file": record.get("result_file") if record else None,
                    "metrics_file": next((item for item in artifacts if item.endswith("metrics.json")), None),
                    "summary_file": next((item for item in artifacts if item.endswith("summary.md")), None),
                    "output_files": artifacts,
                },
                "evidence_artifacts": artifacts,
                "source_hash": record.get("source_hash") if record else None,
                "generated_code_execution": bool(record.get("generated_code_execution")) if record else False,
                "match_score": round(float(score), 4),
                "matched_terms": matches,
                "evidence_warning_flags": warning_flags,
                "human_review_required": human_review_required,
                "recommended_action": recommended_action,
            }
        )
    weak_binding_count = sum(1 for item in bindings if item.get("binding_status") == "weak_binding")
    summary = {
        "total_bindings": len(bindings),
        "total_sentences_checked": len(bindings),
        "experiment_record_count": len(records),
        "claim_like_sentences": sum(1 for item in bindings if item.get("is_claim_like")),
        "bound": sum(1 for item in bindings if item.get("binding_status") == "bound"),
        "experiment_bound": sum(1 for item in bindings if item.get("binding_status") == "bound"),
        "weak_binding": weak_binding_count,
        "weakly_bound": weak_binding_count,
        "unbound": sum(1 for item in bindings if item.get("binding_status") == "unbound"),
        "supported": sum(1 for item in bindings if item.get("claim_support_status") == "supported"),
        "weakly_supported": sum(1 for item in bindings if item.get("claim_support_status") == "weakly_supported"),
        "unsupported": sum(1 for item in bindings if item.get("claim_support_status") == "unsupported"),
        "human_review_required": sum(1 for item in bindings if item.get("human_review_required")),
    }
    payload = {
        "schema_version": f"{SCHEMA_PREFIX}.experiment_claim_binding.v1",
        "project_id": project_id,
        "created_at": utc_now(),
        "reason": reason.strip(),
        "manuscript_file": manuscript_file,
        "experiment_tree_file": EXPERIMENT_TREE_JSON if (project_dir / EXPERIMENT_TREE_JSON).exists() else None,
        "selected_node_id": selected,
        "binding_file": EXPERIMENT_CLAIM_BINDINGS_JSON,
        "bindings_file": EXPERIMENT_CLAIM_BINDINGS_JSON,
        "binding_markdown_file": EXPERIMENT_CLAIM_BINDINGS_MD,
        "bindings_markdown_file": EXPERIMENT_CLAIM_BINDINGS_MD,
        "claim_trace_file": MANUSCRIPT_CLAIM_TRACE_JSONL,
        "latest_binding_file": LATEST_EXPERIMENT_CLAIM_BINDING_JSON,
        "experiment_record_count": len(records),
        "evidence_unit_count": len(records),
        "summary": summary,
        "bindings": bindings,
        "sentence_bindings": bindings,
        "limitations": [
            "Experiment-to-claim binding is a local traceability heuristic, not scientific proof or peer review.",
            "Bound claims still require human review of metrics, output files, sandbox policy, and manuscript wording.",
            "Unbound or weakly bound claims should be revised as limitations or linked to verified artifacts before external use.",
        ],
    }
    write_project_json(project_dir, EXPERIMENT_CLAIM_BINDINGS_JSON, payload)
    write_project_json(project_dir, LATEST_EXPERIMENT_CLAIM_BINDING_JSON, payload)
    write_project_text(project_dir, EXPERIMENT_CLAIM_BINDINGS_MD, _render_markdown(payload))
    trace_path = project_dir / MANUSCRIPT_CLAIM_TRACE_JSONL
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("w", encoding="utf-8") as handle:
        for binding in bindings:
            handle.write(json.dumps(binding, ensure_ascii=False) + "\n")
    latest = read_json(project_dir / LATEST_RUN_JSON, {})
    if isinstance(latest, dict):
        latest["experiment_claim_bindings_file"] = EXPERIMENT_CLAIM_BINDINGS_JSON
        latest["latest_experiment_claim_binding_file"] = LATEST_EXPERIMENT_CLAIM_BINDING_JSON
        latest["experiment_claim_binding_summary"] = summary
        write_project_json(project_dir, LATEST_RUN_JSON, latest)
    append_audit_event(
        project_dir,
        project_id,
        "build_auto_scientist_experiment_claim_bindings",
        "Auto Scientist experiment outputs were bound to manuscript claim-like sentences for traceability.",
        {"manuscript_file": manuscript_file, "binding_file": EXPERIMENT_CLAIM_BINDINGS_JSON, "summary": summary},
        source="api",
        event_category="review",
        risk_level="medium",
        entity_type="review_issue",
        entity_id=safe_id(manuscript_file),
    )
    return payload


def generate_experiment_claim_bindings(
    project_dir: Path,
    project_id: str,
    manuscript_relative_path: str | None = None,
    node_id: str | None = None,
    reason: str = "",
    top_k: int = 5,
) -> dict[str, Any]:
    _ = top_k
    return build_experiment_claim_bindings(
        project_dir,
        project_id,
        manuscript_relative_path=manuscript_relative_path,
        node_id=node_id,
        reason=reason,
    )


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Auto Scientist Experiment Claim Bindings",
        "",
        "> This traceability report binds manuscript claim-like sentences to local experiment nodes, metrics, and output artifacts. It is not scientific proof or peer review.",
        "",
        f"- Manuscript: `{payload.get('manuscript_file')}`",
        f"- Experiment records indexed: {payload.get('experiment_record_count', 0)}",
        f"- Claim-like sentences: {summary.get('claim_like_sentences', 0)}",
        f"- Bound: {summary.get('bound', 0)}",
        f"- Weak binding: {summary.get('weak_binding', 0)}",
        f"- Unbound: {summary.get('unbound', 0)}",
        f"- Human review required: {summary.get('human_review_required', 0)}",
        "",
        "## Bindings Requiring Review",
        "",
    ]
    review_items = [item for item in payload.get("bindings", []) if isinstance(item, dict) and item.get("human_review_required")]
    if not review_items:
        lines.append("- No binding issues requiring review were detected by the local heuristic.")
    for item in review_items[:50]:
        lines.extend(
            [
                f"- `{item.get('binding_id')}` {item.get('claim_support_status')} / {item.get('binding_status')} / section `{item.get('section')}`",
                f"  - sentence: {item.get('sentence')}",
                f"  - experiment: `{item.get('experiment_node_id') or item.get('experiment_id') or 'unbound'}`",
                f"  - warnings: {', '.join(item.get('evidence_warning_flags') or []) or 'none'}",
            ]
        )
    lines.extend(["", "## Limitations", ""])
    for limitation in payload.get("limitations", []):
        lines.append(f"- {limitation}")
    return "\n".join(lines) + "\n"
