from __future__ import annotations

import argparse
import json
import os
import sys
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

from app.tools.literature_rag import RETRIEVAL_MODES, ask_literature_rag, build_literature_rag
from scripts.seed_demo import main as seed_demo

DEFAULT_CASES = [
    {
        "question": "What does the demo literature mention about efficiency and stability?",
        "expected_answer_support_status": "weakly_supported",
        "expected_terms": ["efficiency", "stability"],
        "must_not_contain": ["statistically significant", "causal", "p-value"],
    },
    {
        "question": "What exact p-value proves the clinical survival outcome?",
        "expected_answer_support_status": "unsupported",
        "expected_terms": [],
        "must_not_contain": ["statistically significant", "causal", "p-value", "proves"],
    },
]


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return "<external_project_dir>"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"eval set line {line_number} must be a JSON object")
        cases.append(value)
    return cases


def _ensure_demo_project(project_id: str, project_dir: Path) -> None:
    if (project_dir / "literature").exists() and any((project_dir / "literature").iterdir()):
        return
    default_demo_dir = (ROOT / "projects" / "demo_project").resolve()
    if project_id == "demo_project" and project_dir.resolve() == default_demo_dir:
        seed_demo()
        return
    raise FileNotFoundError(
        "project_dir must contain local literature files or use the default demo_project"
    )


def _contains_all_terms(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return all(term.lower() in lowered for term in terms)


def _must_not_hits(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def evaluate_cases(
    project_id: str,
    project_dir: Path,
    cases: list[dict[str, Any]],
    retrieval_mode: str,
) -> dict[str, Any]:
    build_literature_rag(project_dir, project_id)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    unsupported_expected = 0
    unsupported_refusals = 0
    source_passage_answers = 0
    status_matches = 0

    for index, case in enumerate(cases, start=1):
        question = str(case.get("question") or "").strip()
        expected_status = str(case.get("expected_answer_support_status") or "").strip()
        expected_terms = [
            str(term)
            for term in case.get("expected_terms", [])
            if isinstance(term, str) and term.strip()
        ]
        must_not_contain = [
            str(term)
            for term in case.get("must_not_contain", [])
            if isinstance(term, str) and term.strip()
        ]
        answer = ask_literature_rag(
            project_dir,
            project_id,
            question,
            top_k=int(case.get("top_k") or 5),
            retrieval_mode=retrieval_mode,
        )
        answer_text = str(answer.get("answer") or "")
        passage_text = " ".join(
            str(passage.get("text") or "") for passage in answer.get("source_passages", [])
            if isinstance(passage, dict)
        )
        combined_text = f"{answer_text} {passage_text}"
        support_status = str(answer.get("answer_support_status") or "")
        status_ok = support_status == expected_status
        terms_ok = _contains_all_terms(combined_text, expected_terms)
        forbidden_hits = _must_not_hits(answer_text, must_not_contain)
        forbidden_ok = not forbidden_hits
        if expected_status == "unsupported":
            unsupported_expected += 1
            if support_status == "unsupported" and "not contain enough passage support" in answer_text:
                unsupported_refusals += 1
        if answer.get("source_passages"):
            source_passage_answers += 1
        if status_ok:
            status_matches += 1

        passed = status_ok and terms_ok and forbidden_ok
        record = {
            "case_id": case.get("case_id") or f"case_{index:04d}",
            "question": question,
            "expected_answer_support_status": expected_status,
            "answer_support_status": support_status,
            "top_source_score": answer.get("top_source_score", 0),
            "source_passage_count": answer.get("source_passage_count", 0),
            "passed": passed,
            "failures": [],
        }
        if not status_ok:
            record["failures"].append("support status mismatch")
        if not terms_ok:
            record["failures"].append("expected terms missing from answer/source passages")
        if forbidden_hits:
            record["failures"].append(f"answer contained forbidden terms: {', '.join(forbidden_hits)}")
        results.append(record)
        if not passed:
            failures.append(record)

    total = len(results)
    report = {
        "project_id": project_id,
        "project_dir": _relative(project_dir),
        "retrieval_mode": retrieval_mode,
        "llm_mode": os.environ.get("LLM_MODE", "mock"),
        "total": total,
        "passed": sum(1 for result in results if result["passed"]),
        "failed": len(failures),
        "support_status_accuracy": round(status_matches / total, 4) if total else 0.0,
        "unsupported_refusal_rate": round(unsupported_refusals / unsupported_expected, 4)
        if unsupported_expected
        else 1.0,
        "answer_has_source_passage_rate": round(source_passage_answers / total, 4) if total else 0.0,
        "failures": failures,
        "results": results,
        "limitations": [
            "This is an offline local regression check, not an external retrieval benchmark.",
            "FTS/BM25 scores are retrieval signals, not scientific evidence strength.",
            "Mock answers must not be treated as verified research conclusions.",
        ],
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate local Literature RAG Evidence Q&A behavior.")
    parser.add_argument("--project-id", default="demo_project")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--eval-set", default=None, help="Optional JSONL eval set path.")
    parser.add_argument(
        "--retrieval-mode",
        default="local_hybrid",
        choices=sorted(RETRIEVAL_MODES),
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve() if args.project_dir else ROOT / "projects" / args.project_id
    _ensure_demo_project(args.project_id, project_dir)
    cases = _load_jsonl(Path(args.eval_set)) if args.eval_set else DEFAULT_CASES
    report = evaluate_cases(args.project_id, project_dir, cases, args.retrieval_mode)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["total", "passed", "failed", "retrieval_mode"]}))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
