from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], output: Path) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    payload = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    return {"command": command, "returncode": completed.returncode, "stdout": completed.stdout, "report": payload}


def _prepare_rag_project() -> tempfile.TemporaryDirectory[str]:
    tmp = tempfile.TemporaryDirectory()
    project_dir = Path(tmp.name) / "local_evidence_qa_project"
    literature_dir = project_dir / "literature"
    literature_dir.mkdir(parents=True)
    for path in (ROOT / "evals" / "local_evidence_qa" / "mini_literature").iterdir():
        if path.is_file():
            shutil.copy2(path, literature_dir / path.name)
    return tmp


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local ResearchAgent regression evals.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--retrieval-mode", default="local_hybrid_fts")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rag_output = output.with_name(output.stem + "_rag.json")
    claim_output = output.with_name(output.stem + "_claim_audit.json")
    with _prepare_rag_project() as tmp_dir:
        rag_project_dir = Path(tmp_dir) / "local_evidence_qa_project"
        runs = [
            _run(
                [
                    sys.executable,
                    "scripts/evaluate_rag.py",
                    "--project-id",
                    "local_evidence_qa_project",
                    "--project-dir",
                    str(rag_project_dir),
                    "--eval-set",
                    str(ROOT / "evals" / "local_evidence_qa" / "rag_questions.jsonl"),
                    "--retrieval-mode",
                    args.retrieval_mode,
                    "--output",
                    str(rag_output),
                ],
                rag_output,
            ),
            _run(
                [
                    sys.executable,
                    "scripts/evaluate_claim_audit.py",
                    "--retrieval-mode",
                    args.retrieval_mode,
                    "--output",
                    str(claim_output),
                ],
                claim_output,
            ),
        ]
    total = sum(int((run.get("report") or {}).get("total", 0)) for run in runs)
    failed = sum(int((run.get("report") or {}).get("failed", 0)) for run in runs)
    report = {
        "total": total,
        "passed": total - failed,
        "failed": failed,
        "aggregate_pass_rate": round((total - failed) / total, 4) if total else 0.0,
        "retrieval_mode": args.retrieval_mode,
        "runs": runs,
        "limitations": [
            "These are local regression evals over demo fixtures, not external benchmark results.",
        ],
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["total", "passed", "failed", "retrieval_mode"]}))
    if failed or any(run["returncode"] for run in runs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
