from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("PROJECTS_ROOT", "./projects")
os.environ.setdefault("LLM_MODE", "mock")
os.environ.setdefault("LLM_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.tools.claim_audit import run_draft_claim_audit
from app.tools.literature_rag import build_literature_rag

DEFAULT_EVAL_SET = ROOT / "evals" / "local_evidence_qa" / "claim_audit_cases.jsonl"
DEFAULT_LITERATURE_DIR = ROOT / "evals" / "local_evidence_qa" / "mini_literature"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"line {line_number} must be a JSON object")
        records.append(payload)
    return records


def _must_not_hits(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def _prepare_project(tmp_root: Path, literature_dir: Path) -> Path:
    project_dir = tmp_root / "claim_audit_eval_project"
    (project_dir / "literature").mkdir(parents=True)
    (project_dir / "manuscript").mkdir(parents=True)
    for path in literature_dir.iterdir():
        if path.is_file():
            shutil.copy2(path, project_dir / "literature" / path.name)
    return project_dir


def evaluate_cases(cases: list[dict[str, Any]], literature_dir: Path, retrieval_mode: str) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    status_matches = 0
    unsupported_expected = 0
    unsupported_detected = 0
    unsafe_hits = 0
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = _prepare_project(Path(tmp), literature_dir)
        project_id = "claim_audit_eval_project"
        build_literature_rag(project_dir, project_id)
        for index, case in enumerate(cases, start=1):
            manuscript = str(case.get("manuscript") or "")
            expected_statuses = [str(item) for item in case.get("expected_statuses", [])]
            must_not_contain = [str(item) for item in case.get("must_not_contain", [])]
            audit = run_draft_claim_audit(
                project_dir,
                project_id,
                manuscript_text=manuscript,
                retrieval_mode=retrieval_mode,
            )
            statuses = [str(item.get("answer_support_status")) for item in audit.get("claim_audits", [])]
            status_ok = statuses == expected_statuses
            if status_ok:
                status_matches += 1
            unsupported_expected += expected_statuses.count("unsupported")
            unsupported_detected += statuses.count("unsupported")
            suggestions = " ".join(
                str(item.get("recommended_action", "")) for item in audit.get("claim_audits", [])
            )
            hits = _must_not_hits(suggestions, must_not_contain)
            if hits:
                unsafe_hits += 1
            passed = status_ok and not hits
            record = {
                "case_id": case.get("case_id") or f"case_{index:04d}",
                "expected_statuses": expected_statuses,
                "actual_statuses": statuses,
                "passed": passed,
                "failures": [],
            }
            if not status_ok:
                record["failures"].append("support status sequence mismatch")
            if hits:
                record["failures"].append(f"unsafe wording in suggestions: {', '.join(hits)}")
            results.append(record)
            if not passed:
                failures.append(record)
    total = len(results)
    return {
        "total": total,
        "passed": sum(1 for item in results if item["passed"]),
        "failed": len(failures),
        "support_status_accuracy": round(status_matches / total, 4) if total else 0.0,
        "unsupported_claim_detection_rate": round(unsupported_detected / unsupported_expected, 4) if unsupported_expected else 1.0,
        "unsafe_wording_rate": round(unsafe_hits / total, 4) if total else 0.0,
        "retrieval_mode": retrieval_mode,
        "failures": failures,
        "results": results,
        "limitations": [
            "This is a local regression eval using demo fixtures, not an external benchmark.",
            "Unsupported detection is treated as an integrity success when evidence is insufficient.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate local draft claim audit behavior.")
    parser.add_argument("--eval-set", default=str(DEFAULT_EVAL_SET))
    parser.add_argument("--literature-dir", default=str(DEFAULT_LITERATURE_DIR))
    parser.add_argument("--retrieval-mode", default="local_hybrid_fts")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    cases = _load_jsonl(Path(args.eval_set))
    report = evaluate_cases(cases, Path(args.literature_dir), args.retrieval_mode)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["total", "passed", "failed", "retrieval_mode"]}))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
