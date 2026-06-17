from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.file_tools import write_json

PHASE_GATES_JSON = "auto_scientist/phase_gates.json"
DECISIONS_FILE = "trust/human_review_decisions.jsonl"

COPILOT_MODES = {"off", "advisory", "strict"}

PHASE_DEFINITIONS: dict[str, dict[str, str]] = {
    "ideas": {
        "title": "Copilot gate: research ideas",
        "description": "Review generated ideas, rationale, limitations, and local-evidence grounding before continuing.",
        "artifact_path": "auto_scientist/ideas.json",
        "recommended_action": "approve_or_revise_ideas",
    },
    "experiment_plan": {
        "title": "Copilot gate: experiment plan",
        "description": "Review registered templates, generated-code policy, and experiment scope before running experiments.",
        "artifact_path": "auto_scientist/experiment_plan.json",
        "recommended_action": "approve_or_revise_experiment_plan",
    },
    "generated_code": {
        "title": "Copilot gate: generated-code policy",
        "description": "Review generated-code mode, sandbox policy, source provenance, and approval requirements before execution.",
        "artifact_path": "auto_scientist/experiment_plan.json",
        "recommended_action": "review_generated_code_policy",
    },
    "tree_selection": {
        "title": "Copilot gate: experiment tree selection",
        "description": "Review experiment tree candidates, heuristic scores, and best-node rationale before manuscript use.",
        "artifact_path": "auto_scientist/experiment_tree.json",
        "recommended_action": "review_tree_candidates_and_selection",
    },
    "paper_draft": {
        "title": "Copilot gate: paper draft",
        "description": "Review AI-generated draft text, claim scope, and limitations before citation or export steps.",
        "artifact_path": "manuscript/auto_scientist_paper.md",
        "recommended_action": "review_paper_draft",
    },
    "citation_binding": {
        "title": "Copilot gate: citation binding",
        "description": "Review citation/source-passage bindings, weak bindings, and unbound claims before export.",
        "artifact_path": "manuscript/paper_citation_bindings.json",
        "recommended_action": "review_citation_bindings",
    },
    "compile_export": {
        "title": "Copilot gate: compile/export",
        "description": "Review LaTeX/PDF compile status and export warnings before treating artifacts as handoff drafts.",
        "artifact_path": "manuscript/latex_compile_report.json",
        "recommended_action": "review_compile_and_export_artifacts",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_copilot_mode(value: str | None) -> str:
    mode = (value or "off").strip().lower()
    if mode not in COPILOT_MODES:
        raise ValueError("copilot_mode must be one of: off, advisory, strict")
    return mode


def phase_gate_review_id(phase: str) -> str:
    return f"auto_scientist_phase_gate_{phase}"


def expected_phase_names(
    *,
    write_paper: bool,
    export_latex: bool,
    allow_generated_code_experiments: bool,
    enable_experiment_tree_search: bool,
) -> list[str]:
    phases = ["ideas", "experiment_plan"]
    if allow_generated_code_experiments:
        phases.append("generated_code")
    if enable_experiment_tree_search:
        phases.append("tree_selection")
    if write_paper:
        phases.extend(["paper_draft", "citation_binding"])
        if export_latex:
            phases.append("compile_export")
    return phases


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _read_decisions(project_dir: Path) -> dict[str, dict[str, Any]]:
    path = project_dir / DECISIONS_FILE
    if not path.exists():
        return {}
    decisions: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("review_id"), str):
            decisions[str(payload["review_id"])] = payload
    return decisions


def _gate_for_phase(
    phase: str,
    *,
    mode: str,
    active_phase: str | None,
    decisions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    definition = PHASE_DEFINITIONS[phase]
    review_id = phase_gate_review_id(phase)
    decision = decisions.get(review_id)
    decision_value = str(decision.get("decision")) if isinstance(decision, dict) and decision.get("decision") else None
    status = decision_value or "pending"
    return {
        "phase": phase,
        "review_id": review_id,
        "title": definition["title"],
        "description": definition["description"],
        "artifact_path": definition["artifact_path"],
        "recommended_action": definition["recommended_action"],
        "mode": mode,
        "severity": "blocking" if mode == "strict" else "warning",
        "blocking": mode == "strict",
        "status": status,
        "active": phase == active_phase,
        "human_review_required": True,
        "decided_at": decision.get("decided_at") if isinstance(decision, dict) else None,
        "decision_reason": decision.get("reason", "") if isinstance(decision, dict) else "",
    }


def write_phase_gates(
    project_dir: Path,
    project_id: str,
    *,
    mode: str,
    run_id: str,
    expected_phases: list[str],
    active_phase: str | None,
) -> dict[str, Any]:
    normalized_mode = normalize_copilot_mode(mode)
    if normalized_mode == "off":
        return read_phase_gates(project_dir) or {}
    decisions = _read_decisions(project_dir)
    phases = [phase for phase in expected_phases if phase in PHASE_DEFINITIONS]
    gates = [
        _gate_for_phase(phase, mode=normalized_mode, active_phase=active_phase, decisions=decisions)
        for phase in phases
    ]
    blocking_gate = None
    if normalized_mode == "strict" and active_phase:
        active = next((gate for gate in gates if gate["phase"] == active_phase), None)
        if active and active.get("status") != "approved":
            blocking_gate = active
    pending = [gate for gate in gates if gate.get("status") == "pending"]
    payload = {
        "schema_version": "researchagent.auto_scientist.phase_gates.v1",
        "project_id": project_id,
        "generated_at": utc_now(),
        "relative_path": PHASE_GATES_JSON,
        "run_id": run_id,
        "copilot_mode": normalized_mode,
        "active_phase": active_phase,
        "status": "awaiting_human_review" if blocking_gate else "advisory" if normalized_mode == "advisory" else "clear",
        "blocking_gate": blocking_gate,
        "gates": gates,
        "summary": {
            "total": len(gates),
            "pending": len(pending),
            "approved": sum(1 for gate in gates if gate.get("status") == "approved"),
            "rejected": sum(1 for gate in gates if gate.get("status") == "rejected"),
            "blocking_pending": 1 if blocking_gate else 0,
        },
        "limitations": [
            "Copilot phase gates are local workflow controls, not peer review or scientific validation.",
            "Approving a phase gate records local human permission to continue; it does not approve generated code, tree revisions, or citations.",
            "Generated-code approvals, tree revision approvals, and citation review items remain separate gates in the Human Review Queue.",
        ],
    }
    write_json(project_dir / PHASE_GATES_JSON, payload)
    return payload


def read_phase_gates(project_dir: Path) -> dict[str, Any] | None:
    payload = _read_json(project_dir / PHASE_GATES_JSON, None)
    return payload if isinstance(payload, dict) else None
