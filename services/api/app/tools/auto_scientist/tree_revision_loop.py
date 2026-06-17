from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.auto_scientist.contracts import (
    EXPERIMENT_TREE_JSON,
    LATEST_RUN_JSON,
    SCHEMA_PREFIX,
    append_jsonl,
    read_json,
    read_jsonl,
    safe_id,
    utc_now,
    write_project_json,
    write_project_text,
)
from app.tools.auto_scientist.experiment_claim_binding import (
    EXPERIMENT_CLAIM_BINDINGS_JSON,
    generate_experiment_claim_bindings,
)
from app.tools.auto_scientist.experiment_tree_ops import (
    read_experiment_tree,
    rewrite_auto_scientist_paper_from_tree,
    select_experiment_tree_node,
)
from app.tools.auto_scientist.scientist_paper import AUTONOMOUS_PAPER_MD
from app.tools.claim_audit import run_draft_claim_audit
from app.tools.evidence_trust_package import build_evidence_trust_package
from app.tools.human_review_queue import DECISIONS_FILE
from app.tools.manuscript_safety import check_manuscript_safety

TREE_REVISION_PLAN_JSON = "auto_scientist/tree_revision_plan.json"
TREE_REVISION_PLAN_MD = "auto_scientist/tree_revision_plan.md"
TREE_REVISION_PATCHES_JSON = "auto_scientist/tree_revision_patches.json"
TREE_REVISION_APPLICATIONS_JSONL = "auto_scientist/tree_revision_applications.jsonl"
LATEST_TREE_REVISION_APPLICATION_JSON = "auto_scientist/latest_tree_revision_application.json"
REVISED_AUTONOMOUS_PAPER_MD = "manuscript/auto_scientist_paper_revised.md"
REVISED_AUTONOMOUS_PAPER_TEX = "manuscript/auto_scientist_paper_revised.tex"

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


def read_tree_revision_plan(project_dir: Path) -> dict[str, Any]:
    payload = read_json(project_dir / TREE_REVISION_PLAN_JSON, {})
    return payload if isinstance(payload, dict) else {}


def _read_text(project_dir: Path, relative_path: str) -> str:
    path = project_dir / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _decision_records(project_dir: Path) -> list[dict[str, Any]]:
    path = project_dir / DECISIONS_FILE
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


def _approved_review_ids(project_dir: Path) -> set[str]:
    return {
        str(record.get("review_id"))
        for record in _decision_records(project_dir)
        if record.get("decision") == "approved" and isinstance(record.get("review_id"), str)
    }


def _selected_node(tree: dict[str, Any]) -> dict[str, Any]:
    node = tree.get("selected_best_node") if isinstance(tree.get("selected_best_node"), dict) else None
    if node:
        return node
    node = tree.get("best_node") if isinstance(tree.get("best_node"), dict) else None
    if node:
        return node
    nodes = [item for item in tree.get("nodes", []) if isinstance(item, dict)]
    if not nodes:
        raise ValueError("experiment tree has no selectable nodes")
    return max(nodes, key=lambda item: float(item.get("score") or 0.0))


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


def _node_status_issue(node: dict[str, Any]) -> dict[str, Any] | None:
    status = str(node.get("status") or "unknown")
    score = float(node.get("score") or 0.0)
    if status != "completed":
        return {
            "critique_id": "tree_critique_status",
            "severity": "blocking",
            "title": "Selected experiment node did not complete successfully",
            "description": f"The selected node has status `{status}` and should not be described as a successful scientific result.",
            "recommended_action": "rewrite_as_limitation_or_rerun",
        }
    if score < 0.75:
        return {
            "critique_id": "tree_critique_low_score",
            "severity": "warning",
            "title": "Selected experiment node has a low local heuristic score",
            "description": f"The selected node score is {score}. Treat it as a weak local signal rather than a result.",
            "recommended_action": "rewrite_as_limitation",
        }
    return None


def _build_critiques(node: dict[str, Any], tree: dict[str, Any], paper_text: str) -> list[dict[str, Any]]:
    critiques: list[dict[str, Any]] = [
        {
            "critique_id": "tree_critique_not_scientific_proof",
            "severity": "warning",
            "title": "Tree best node is a workflow choice, not scientific proof",
            "description": "Experiment tree scores are local heuristics. The manuscript must state that the selected node is not peer-reviewed scientific evidence.",
            "recommended_action": "add_cautious_tree_interpretation",
        }
    ]
    status_issue = _node_status_issue(node)
    if status_issue:
        critiques.append(status_issue)
    if node.get("generated_code_execution") or str(node.get("template_name") or "") == "generated_code_smoke_test":
        critiques.append(
            {
                "critique_id": "tree_critique_generated_code",
                "severity": "blocking" if node.get("status") != "completed" else "warning",
                "title": "Generated-code experiment output requires source and sandbox review",
                "description": "The selected node used generated-code execution. Source hash, static scan, sandbox limits, stdout/stderr, and outputs need human review before manuscript use.",
                "recommended_action": "add_generated_code_review_limitation",
            }
        )
    safety = check_manuscript_safety(paper_text) if paper_text else {"restricted_terms": []}
    restricted_hits = _restricted_hits(paper_text)
    if restricted_hits:
        critiques.append(
            {
                "critique_id": "tree_critique_restricted_wording",
                "severity": "blocking",
                "title": "Manuscript contains restricted strong wording",
                "description": "The draft contains wording that can imply statistical significance, causality, proof, or verified findings without sufficient local evidence.",
                "restricted_terms": restricted_hits,
                "safety": safety,
                "recommended_action": "replace_with_descriptive_or_limitation_language",
            }
        )
    if not tree.get("selected_best_node_id"):
        critiques.append(
            {
                "critique_id": "tree_critique_no_human_selection",
                "severity": "info",
                "title": "No human-selected best node was recorded",
                "description": "The workflow will use the heuristic best node. Human selection and rationale are recommended before manuscript revision.",
                "recommended_action": "select_node_or_review_heuristic_best",
            }
        )
    return critiques


def _tree_interpretation_section(node: dict[str, Any], tree: dict[str, Any]) -> str:
    node_id = node.get("node_id") or "unknown_node"
    template = node.get("template_name") or "unknown_template"
    status = node.get("status") or "unknown"
    score = node.get("score", "not_available")
    selected_reason = tree.get("selected_reason") or "not provided"
    output_files = node.get("output_files") if isinstance(node.get("output_files"), list) else []
    output_lines = "\n".join(f"- `{item}`" for item in output_files[:8]) or "- No output files were recorded for this node."
    return "\n".join(
        [
            "## Selected Experiment Node Interpretation",
            "",
            (
                f"The revision emphasizes experiment tree node `{node_id}` from template `{template}`. "
                f"Its local workflow status is `{status}` and its heuristic score is `{score}`. "
                "This is a local experiment-management signal only; it is not scientific proof, peer review, citation verification, or publication readiness."
            ),
            "",
            f"Human or workflow selection reason: {selected_reason}.",
            "",
            "Relevant local output artifacts:",
            "",
            output_lines,
            "",
            "Required interpretation boundary: describe this node as a local diagnostic result. Do not infer causality, statistical significance, verified performance, or external validity unless a human adds verified evidence.",
            "",
        ]
    )


def _patches_from_critiques(node: dict[str, Any], tree: dict[str, Any], critiques: list[dict[str, Any]]) -> list[dict[str, Any]]:
    patches: list[dict[str, Any]] = [
        {
            "patch_id": "tree_revision_patch_001",
            "source_critique_ids": ["tree_critique_not_scientific_proof"],
            "target_file": AUTONOMOUS_PAPER_MD,
            "patch_type": "insert_or_replace_section",
            "section_title": "Selected Experiment Node Interpretation",
            "original_text": "",
            "suggested_text": _tree_interpretation_section(node, tree),
            "reason": "Add a cautious interpretation of the selected experiment tree node before using it in the manuscript.",
            "risk_level": "medium",
            "requires_human_approval": True,
            "status": "pending_human_approval",
            "review_id": "auto_scientist_tree_revision_patch_tree_revision_patch_001",
        }
    ]
    if any(item.get("critique_id") == "tree_critique_generated_code" for item in critiques):
        patches.append(
            {
                "patch_id": "tree_revision_patch_002",
                "source_critique_ids": ["tree_critique_generated_code"],
                "target_file": AUTONOMOUS_PAPER_MD,
                "patch_type": "append_limitation_bullet",
                "section_title": "Limitations",
                "original_text": "",
                "suggested_text": "- Generated-code experiment outputs require review of source hash, static scan, sandbox policy, stdout/stderr, and output artifacts before being used as evidence.",
                "reason": "Generated-code artifacts are higher risk than registered templates and need explicit manuscript limitations.",
                "risk_level": "high",
                "requires_human_approval": True,
                "status": "pending_human_approval",
                "review_id": "auto_scientist_tree_revision_patch_tree_revision_patch_002",
            }
        )
    if any(item.get("critique_id") in {"tree_critique_status", "tree_critique_low_score"} for item in critiques):
        patches.append(
            {
                "patch_id": "tree_revision_patch_003",
                "source_critique_ids": [item["critique_id"] for item in critiques if item.get("critique_id") in {"tree_critique_status", "tree_critique_low_score"}],
                "target_file": AUTONOMOUS_PAPER_MD,
                "patch_type": "append_limitation_bullet",
                "section_title": "Limitations",
                "original_text": "",
                "suggested_text": "- The selected experiment tree node should be treated as weak or incomplete local evidence until a human reruns, validates, and documents the underlying artifacts.",
                "reason": "Prevent weak or incomplete experiment-tree signals from being presented as findings.",
                "risk_level": "high",
                "requires_human_approval": True,
                "status": "pending_human_approval",
                "review_id": "auto_scientist_tree_revision_patch_tree_revision_patch_003",
            }
        )
    if any(item.get("critique_id") == "tree_critique_restricted_wording" for item in critiques):
        patches.append(
            {
                "patch_id": "tree_revision_patch_004",
                "source_critique_ids": ["tree_critique_restricted_wording"],
                "target_file": AUTONOMOUS_PAPER_MD,
                "patch_type": "append_internal_review_note",
                "section_title": "Internal Review and Revision Needs",
                "original_text": "",
                "suggested_text": "The draft contains restricted strong wording. Replace statistical, causal, or proof-like language with descriptive wording unless verified evidence and human review support it.",
                "reason": "Restricted claims need explicit manuscript review before external use.",
                "risk_level": "high",
                "requires_human_approval": True,
                "status": "pending_human_approval",
                "review_id": "auto_scientist_tree_revision_patch_tree_revision_patch_004",
            }
        )
    return patches


def _plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Auto Scientist Tree Revision Plan",
        "",
        "> This plan critiques the selected experiment tree node and creates human-approved manuscript patch suggestions. It is not peer review or scientific proof.",
        "",
        "## Selected Node",
        "",
        f"- Node ID: `{plan.get('selected_node_id')}`",
        f"- Template: `{(plan.get('selected_node') or {}).get('template_name', 'unknown')}`",
        f"- Score: `{(plan.get('selected_node') or {}).get('score', 'unknown')}`",
        "",
        "## Critiques",
        "",
    ]
    for critique in plan.get("critiques", []):
        lines.extend(
            [
                f"### {critique.get('critique_id')} — {critique.get('severity')}",
                "",
                f"- {critique.get('title')}",
                f"- Recommended action: `{critique.get('recommended_action')}`",
                f"- Description: {critique.get('description')}",
                "",
            ]
        )
    lines.extend(["## Patch Suggestions", ""])
    for patch in plan.get("patch_suggestions", []):
        lines.extend(
            [
                f"### {patch.get('patch_id')} — {patch.get('risk_level')}",
                "",
                f"- Review ID: `{patch.get('review_id')}`",
                f"- Target: `{patch.get('target_file')}`",
                f"- Type: `{patch.get('patch_type')}`",
                f"- Requires human approval: {patch.get('requires_human_approval')}",
                f"- Reason: {patch.get('reason')}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def generate_tree_revision_plan(
    project_dir: Path,
    project_id: str,
    node_id: str | None = None,
    reason: str = "",
) -> dict[str, Any]:
    tree = read_experiment_tree(project_dir)
    if not tree:
        raise FileNotFoundError(EXPERIMENT_TREE_JSON)
    if node_id:
        select_experiment_tree_node(project_dir, project_id, node_id, reason=reason or "Selected for tree revision planning.")
        tree = read_experiment_tree(project_dir)
    node = _selected_node(tree)
    paper_text = _read_text(project_dir, AUTONOMOUS_PAPER_MD)
    if not paper_text:
        rewrite_auto_scientist_paper_from_tree(project_dir, project_id, node_id=str(node.get("node_id") or ""), reason="Create base paper for tree revision plan.")
        paper_text = _read_text(project_dir, AUTONOMOUS_PAPER_MD)
    critiques = _build_critiques(node, tree, paper_text)
    patch_suggestions = _patches_from_critiques(node, tree, critiques)
    plan = {
        "schema_version": f"{SCHEMA_PREFIX}.tree_revision_plan.v1",
        "project_id": project_id,
        "created_at": utc_now(),
        "experiment_tree_file": EXPERIMENT_TREE_JSON,
        "source_paper_file": AUTONOMOUS_PAPER_MD,
        "revision_plan_file": TREE_REVISION_PLAN_JSON,
        "revision_plan_markdown_file": TREE_REVISION_PLAN_MD,
        "patch_suggestions_file": TREE_REVISION_PATCHES_JSON,
        "revised_paper_file": REVISED_AUTONOMOUS_PAPER_MD,
        "revised_latex_file": REVISED_AUTONOMOUS_PAPER_TEX,
        "selected_node_id": node.get("node_id"),
        "selected_node": node,
        "reason": reason.strip(),
        "critiques": critiques,
        "patch_suggestions": patch_suggestions,
        "human_approval_required": True,
        "limitations": [
            "Revision patches are suggestions and do not modify the source manuscript until explicitly applied.",
            "Patch approval records local workflow review only; it is not peer review, citation verification, or scientific proof.",
            "After applying patches, rerun claim audit and review the revised manuscript before external use.",
        ],
    }
    write_project_json(project_dir, TREE_REVISION_PLAN_JSON, plan)
    write_project_json(project_dir, TREE_REVISION_PATCHES_JSON, patch_suggestions)
    write_project_text(project_dir, TREE_REVISION_PLAN_MD, _plan_markdown(plan))
    append_audit_event(
        project_dir,
        project_id,
        "generate_auto_scientist_tree_revision_plan",
        "Auto Scientist generated a best-node-driven manuscript revision plan.",
        {
            "selected_node_id": plan["selected_node_id"],
            "patch_suggestion_count": len(patch_suggestions),
            "revision_plan_file": TREE_REVISION_PLAN_JSON,
        },
        source="api",
        event_category="review",
        risk_level="medium",
        entity_type="auto_scientist_revision",
        entity_id=str(plan["selected_node_id"] or "tree_revision"),
    )
    return plan


def _replace_section(markdown: str, title: str, replacement: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(title)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(markdown)
    if not match:
        insert_before = re.search(r"^##\s+Evidence-Bound Claims\s*$", markdown, re.IGNORECASE | re.MULTILINE)
        if insert_before:
            return markdown[: insert_before.start()] + replacement.strip() + "\n\n" + markdown[insert_before.start() :]
        return markdown.rstrip() + "\n\n" + replacement.strip() + "\n"
    next_heading = re.search(r"^##\s+", markdown[match.end() :], re.MULTILINE)
    end = len(markdown) if not next_heading else match.end() + next_heading.start()
    return markdown[: match.start()] + replacement.strip() + "\n\n" + markdown[end:].lstrip("\n")


def _append_limitation(markdown: str, text: str) -> str:
    pattern = re.compile(r"^##\s+Limitations\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(markdown)
    bullet = text if text.strip().startswith("-") else f"- {text.strip()}"
    if not match:
        return markdown.rstrip() + "\n\n## Limitations\n\n" + bullet + "\n"
    next_heading = re.search(r"^##\s+", markdown[match.end() :], re.MULTILINE)
    end = len(markdown) if not next_heading else match.end() + next_heading.start()
    section = markdown[match.start() : end].rstrip()
    if bullet in section:
        return markdown
    return markdown[:end].rstrip() + "\n" + bullet + "\n\n" + markdown[end:].lstrip("\n")


def _append_internal_note(markdown: str, text: str) -> str:
    title = "Internal Review and Revision Needs"
    pattern = re.compile(rf"^##\s+{re.escape(title)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(markdown)
    note = text.strip()
    if not match:
        return markdown.rstrip() + f"\n\n## {title}\n\n{note}\n"
    next_heading = re.search(r"^##\s+", markdown[match.end() :], re.MULTILINE)
    end = len(markdown) if not next_heading else match.end() + next_heading.start()
    if note in markdown[match.start() : end]:
        return markdown
    return markdown[:end].rstrip() + "\n\n" + note + "\n\n" + markdown[end:].lstrip("\n")


def _apply_patch_text(markdown: str, patch: dict[str, Any]) -> str:
    patch_type = patch.get("patch_type")
    if patch_type == "insert_or_replace_section":
        return _replace_section(markdown, str(patch.get("section_title") or "Selected Experiment Node Interpretation"), str(patch.get("suggested_text") or ""))
    if patch_type == "append_limitation_bullet":
        return _append_limitation(markdown, str(patch.get("suggested_text") or ""))
    if patch_type == "append_internal_review_note":
        return _append_internal_note(markdown, str(patch.get("suggested_text") or ""))
    return markdown.rstrip() + "\n\n" + str(patch.get("suggested_text") or "").strip() + "\n"


def _latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _markdown_to_latex(markdown: str) -> str:
    lines: list[str] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        if line.startswith("# "):
            lines.append(r"\section{" + _latex_escape(line[2:].strip()) + "}")
        elif line.startswith("## "):
            lines.append(r"\subsection{" + _latex_escape(line[3:].strip()) + "}")
        elif line.startswith("- "):
            lines.append(r"\begin{itemize}\item " + _latex_escape(line[2:].strip()) + r"\end{itemize}")
        elif line.startswith(">"):
            lines.append(r"\begin{quote}" + _latex_escape(line.lstrip("> ")) + r"\end{quote}")
        else:
            lines.append(_latex_escape(line))
    return "\n\n".join(lines)


def _write_revised_latex(project_dir: Path, markdown: str) -> None:
    title = "Revised Auto Scientist Paper"
    first_heading = next((line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")), None)
    if first_heading:
        title = first_heading
    latex = "\n".join(
        [
            r"\documentclass[11pt]{article}",
            r"\usepackage[margin=1in]{geometry}",
            r"\usepackage{hyperref}",
            r"\author{ResearchAgent Auto Scientist}",
            r"\date{Local revised draft generated from selected experiment tree node}",
            r"\begin{document}",
            r"\title{" + _latex_escape(title) + "}",
            r"\maketitle",
            _markdown_to_latex(markdown),
            r"\end{document}",
            "",
        ]
    )
    write_project_text(project_dir, REVISED_AUTONOMOUS_PAPER_TEX, latex)


def apply_tree_revision_patches(
    project_dir: Path,
    project_id: str,
    patch_ids: list[str] | None = None,
    reason: str = "",
    require_human_approval: bool = True,
    rerun_claim_audit: bool = True,
    regenerate_trust_package: bool = True,
) -> dict[str, Any]:
    plan = read_tree_revision_plan(project_dir)
    if not plan:
        raise FileNotFoundError(TREE_REVISION_PLAN_JSON)
    patches = [item for item in plan.get("patch_suggestions", []) if isinstance(item, dict)]
    selected_ids = set(patch_ids or [str(item.get("patch_id")) for item in patches])
    selected = [item for item in patches if str(item.get("patch_id")) in selected_ids]
    if not selected:
        raise ValueError("no matching tree revision patches selected")
    approved = _approved_review_ids(project_dir)
    blocked = [patch for patch in selected if patch.get("review_id") not in approved]
    if require_human_approval and blocked:
        raise PermissionError(
            "tree revision patches require approved human review decisions: "
            + ", ".join(str(patch.get("review_id")) for patch in blocked)
        )
    source_file = str(plan.get("source_paper_file") or AUTONOMOUS_PAPER_MD)
    markdown = _read_text(project_dir, source_file)
    if not markdown:
        raise FileNotFoundError(source_file)
    applied_patch_ids: list[str] = []
    for patch in selected:
        markdown = _apply_patch_text(markdown, patch)
        applied_patch_ids.append(str(patch.get("patch_id")))
    markdown = markdown.rstrip() + "\n\n> Tree revision patch application: AI-generated revised manuscript; requires human review before external use.\n"
    write_project_text(project_dir, REVISED_AUTONOMOUS_PAPER_MD, markdown)
    _write_revised_latex(project_dir, markdown)
    claim_audit_result: dict[str, Any] | None = None
    claim_audit_error: str | None = None
    if rerun_claim_audit:
        try:
            claim_audit_result = run_draft_claim_audit(
                project_dir,
                project_id,
                manuscript_text=markdown,
                manuscript_relative_path=REVISED_AUTONOMOUS_PAPER_MD,
                retrieval_mode="local_hybrid_fts",
                top_k=5,
            )
        except Exception as exc:  # keep patch application auditable even if local evidence is absent
            claim_audit_error = exc.__class__.__name__
    binding_payload: dict[str, Any] = {}
    try:
        binding_payload = generate_experiment_claim_bindings(
            project_dir,
            project_id,
            manuscript_relative_path=REVISED_AUTONOMOUS_PAPER_MD,
        )
    except Exception as exc:
        binding_payload = {"error": exc.__class__.__name__, "binding_file": EXPERIMENT_CLAIM_BINDINGS_JSON}
    application = {
        "schema_version": f"{SCHEMA_PREFIX}.tree_revision_application.v1",
        "project_id": project_id,
        "created_at": utc_now(),
        "source_plan_file": TREE_REVISION_PLAN_JSON,
        "source_paper_file": source_file,
        "revised_paper_file": REVISED_AUTONOMOUS_PAPER_MD,
        "revised_latex_file": REVISED_AUTONOMOUS_PAPER_TEX,
        "applied_patch_ids": applied_patch_ids,
        "reason": reason.strip(),
        "human_approval_required": require_human_approval,
        "human_approval_satisfied": not blocked,
        "rerun_claim_audit": rerun_claim_audit,
        "claim_audit_file": "provenance/claim_audit.json" if claim_audit_result else None,
        "claim_audit_summary": claim_audit_result.get("summary") if isinstance(claim_audit_result, dict) else None,
        "claim_audit_error": claim_audit_error,
        "experiment_claim_bindings_file": EXPERIMENT_CLAIM_BINDINGS_JSON if not binding_payload.get("error") else None,
        "experiment_claim_bindings_summary": binding_payload.get("summary") if isinstance(binding_payload, dict) else None,
        "experiment_claim_bindings_error": binding_payload.get("error") if isinstance(binding_payload, dict) else None,
        "trust_package_regenerated": False,
        "limitations": [
            "Applying tree revision patches writes a revised copy and does not overwrite the source Auto Scientist paper.",
            "A revised manuscript remains AI-generated and requires human scientific review.",
            "Human approval records local workflow approval only, not peer review or scientific validity.",
        ],
    }
    append_jsonl(project_dir, TREE_REVISION_APPLICATIONS_JSONL, application)
    write_project_json(project_dir, LATEST_TREE_REVISION_APPLICATION_JSON, application)
    if regenerate_trust_package:
        try:
            package = build_evidence_trust_package(project_dir, project_id)
            application["trust_package_regenerated"] = True
            application["trust_package_file"] = package.get("package_file")
            write_project_json(project_dir, LATEST_TREE_REVISION_APPLICATION_JSON, application)
        except Exception as exc:
            application["trust_package_error"] = exc.__class__.__name__
            write_project_json(project_dir, LATEST_TREE_REVISION_APPLICATION_JSON, application)
    latest = read_json(project_dir / LATEST_RUN_JSON, {})
    if isinstance(latest, dict):
        latest["latest_tree_revision_application"] = application
        latest["latest_tree_revision_application_file"] = LATEST_TREE_REVISION_APPLICATION_JSON
        latest["revised_auto_scientist_paper_file"] = REVISED_AUTONOMOUS_PAPER_MD
        latest["revised_auto_scientist_latex_file"] = REVISED_AUTONOMOUS_PAPER_TEX
        latest["experiment_claim_bindings_file"] = application.get("experiment_claim_bindings_file")
        latest["experiment_claim_bindings_summary"] = application.get("experiment_claim_bindings_summary")
        write_project_json(project_dir, LATEST_RUN_JSON, latest)
    append_audit_event(
        project_dir,
        project_id,
        "apply_auto_scientist_tree_revision_patches",
        "Approved Auto Scientist tree revision patches were applied to a revised manuscript copy.",
        {
            "applied_patch_ids": applied_patch_ids,
            "revised_paper_file": REVISED_AUTONOMOUS_PAPER_MD,
            "claim_audit_error": claim_audit_error,
            "trust_package_regenerated": application.get("trust_package_regenerated"),
        },
        source="api",
        event_category="review",
        risk_level="medium",
        entity_type="auto_scientist_revision",
        entity_id="tree_revision_application",
    )
    return application
