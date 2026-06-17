from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, relative_posix, write_json, write_text

LATEX_COMPILE_REPORT_JSON = "manuscript/latex_compile_report.json"
LATEX_COMPILE_REPORT_MD = "manuscript/latex_compile_report.md"
DEFAULT_PDF_FILE = "manuscript/auto_scientist_paper.pdf"
PREVIEW_PDF_FILE = "manuscript/auto_scientist_paper_preview.pdf"
STDOUT_FILE = "manuscript/latex_build/stdout.txt"
STDERR_FILE = "manuscript/latex_build/stderr.txt"

DANGEROUS_LATEX_PATTERNS = [
    r"\\write18",
    r"\\input\s*\{\s*\.\.",
    r"\\include\s*\{\s*\.\.",
    r"\\openout",
    r"\\read",
    r"\\catcode",
    r"\\usepackage\s*\{\s*minted\s*\}",
    r"\\lstinputlisting",
    r"shell-escape",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _safe_tex_path(project_dir: Path, relative_path: str | None) -> str:
    candidates = [
        relative_path,
        "manuscript/auto_scientist_paper_revised.tex",
        "manuscript/auto_scientist_paper.tex",
        "manuscript/draft_full.tex",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        cleaned = candidate.strip().replace("\\", "/").lstrip("/")
        if not cleaned or ".." in cleaned.split("/"):
            raise ValueError("manuscript_tex_relative_path must stay inside project")
        if not cleaned.startswith("manuscript/") or not cleaned.endswith(".tex"):
            raise ValueError("manuscript_tex_relative_path must be a .tex file under manuscript/")
        if (project_dir / cleaned).exists():
            return cleaned
    raise FileNotFoundError("No Auto Scientist LaTeX manuscript exists to compile")


def _latex_safety_findings(tex: str) -> list[str]:
    findings: list[str] = []
    for pattern in DANGEROUS_LATEX_PATTERNS:
        if re.search(pattern, tex, flags=re.IGNORECASE):
            findings.append(f"blocked pattern: {pattern}")
    return findings


def _select_engine(engine: str) -> str | None:
    if engine == "none":
        return None
    if engine in {"pdflatex", "tectonic"}:
        return engine if shutil.which(engine) else None
    for candidate in ["tectonic", "pdflatex"]:
        if shutil.which(candidate):
            return candidate
    return None


def _pdf_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _write_preview_pdf(path: Path, title: str, lines: list[str]) -> None:
    ensure_dir(path.parent)
    content_lines = [
        "BT",
        "/F1 12 Tf",
        "72 740 Td",
        f"({_pdf_escape(title[:90])}) Tj",
    ]
    y_step = 16
    for line in lines[:38]:
        safe = re.sub(r"[^\x20-\x7E]", "?", line)[:92]
        content_lines.append(f"0 -{y_step} Td ({_pdf_escape(safe)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")
    objects: list[bytes] = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n")
    objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    objects.append(b"5 0 obj\n<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream\nendobj\n")
    offsets: list[int] = []
    payload = bytearray(b"%PDF-1.4\n")
    for obj in objects:
        offsets.append(len(payload))
        payload.extend(obj)
    xref_start = len(payload)
    payload.extend(f"xref\n0 {len(objects)+1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("ascii"))
    path.write_bytes(bytes(payload))


def _run_latex_engine(
    project_dir: Path,
    source_tex: str,
    engine: str,
    timeout_seconds: int,
) -> tuple[str, str, str | None]:
    build_dir = ensure_dir(project_dir / "manuscript" / "latex_build")
    source_path = project_dir / source_tex
    working_tex = build_dir / "paper.tex"
    working_tex.write_text(source_path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    if engine == "pdflatex":
        command = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", "paper.tex"]
    elif engine == "tectonic":
        command = ["tectonic", "--keep-logs", "--keep-intermediates", "paper.tex"]
    else:
        raise ValueError(f"unsupported LaTeX engine: {engine}")
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(build_dir)}
    completed = subprocess.run(
        command,
        cwd=build_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        env=env,
        check=False,
    )
    write_text(project_dir / STDOUT_FILE, completed.stdout or "")
    write_text(project_dir / STDERR_FILE, completed.stderr or "")
    pdf_path = build_dir / "paper.pdf"
    if completed.returncode == 0 and pdf_path.exists():
        target = project_dir / DEFAULT_PDF_FILE
        shutil.copyfile(pdf_path, target)
        return "compiled", "", DEFAULT_PDF_FILE
    warning = f"{engine} exited with status {completed.returncode}"
    return "compile_failed", warning, None


def _markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Paper Compile Report",
        "",
        "> This report records a local LaTeX/PDF pipeline result. A fallback preview PDF is not a publication-ready LaTeX compilation.",
        "",
        f"- Source TeX: {payload.get('source_tex_file')}",
        f"- Engine requested: {payload.get('engine_requested')}",
        f"- Engine used: {payload.get('engine_used')}",
        f"- Compile status: {payload.get('compile_status')}",
        f"- Compiled PDF: {payload.get('pdf_file')}",
        f"- Preview PDF: {payload.get('preview_pdf_file')}",
        "",
        "## Warnings",
        "",
    ]
    warnings = payload.get("warnings") or []
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in payload.get("limitations", []))
    return "\n".join(lines).rstrip() + "\n"


def compile_auto_scientist_paper(
    project_dir: Path,
    project_id: str,
    manuscript_tex_relative_path: str | None = None,
    engine: str = "auto",
    timeout_seconds: int = 30,
    generate_preview_pdf: bool = True,
) -> dict[str, Any]:
    ensure_dir(project_dir / "manuscript")
    source_tex = _safe_tex_path(project_dir, manuscript_tex_relative_path)
    tex = (project_dir / source_tex).read_text(encoding="utf-8", errors="replace")
    findings = _latex_safety_findings(tex)
    warnings: list[str] = []
    compile_status = "not_run"
    engine_used: str | None = None
    pdf_file: str | None = None
    preview_pdf_file: str | None = None

    if findings:
        compile_status = "unsafe_latex_rejected"
        warnings.extend(findings)
    else:
        selected_engine = _select_engine(engine)
        if selected_engine is None:
            compile_status = "tool_unavailable" if engine != "none" else "compile_skipped"
            warnings.append("No supported local LaTeX engine was available; generated a safe preview PDF if requested.")
        else:
            engine_used = selected_engine
            try:
                compile_status, warning, pdf_file = _run_latex_engine(
                    project_dir,
                    source_tex,
                    selected_engine,
                    timeout_seconds=timeout_seconds,
                )
                if warning:
                    warnings.append(warning)
            except subprocess.TimeoutExpired:
                compile_status = "compile_timeout"
                warnings.append(f"LaTeX engine timed out after {timeout_seconds} seconds.")
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                compile_status = "compile_failed"
                warnings.append(f"LaTeX engine failed: {exc.__class__.__name__}")

    if pdf_file is None and generate_preview_pdf:
        preview_pdf_file = PREVIEW_PDF_FILE
        _write_preview_pdf(
            project_dir / preview_pdf_file,
            "ResearchAgent Auto Scientist PDF Preview",
            [
                "This is a deterministic local preview PDF, not a LaTeX-compiled publication file.",
                f"Source TeX: {source_tex}",
                f"Compile status: {compile_status}",
                "Use a reviewed local LaTeX toolchain before external submission.",
            ],
        )

    payload = {
        "schema_version": "researchagent.auto_scientist.paper_compile.v1",
        "project_id": project_id,
        "created_at": _utc_now(),
        "relative_path": LATEX_COMPILE_REPORT_JSON,
        "markdown_report_file": LATEX_COMPILE_REPORT_MD,
        "source_tex_file": source_tex,
        "engine_requested": engine,
        "engine_used": engine_used,
        "compile_status": compile_status,
        "compiled_pdf": bool(pdf_file),
        "pdf_file": pdf_file,
        "preview_pdf_generated": bool(preview_pdf_file),
        "preview_pdf_file": preview_pdf_file,
        "stdout_file": STDOUT_FILE if (project_dir / STDOUT_FILE).exists() else None,
        "stderr_file": STDERR_FILE if (project_dir / STDERR_FILE).exists() else None,
        "latex_safety_findings": findings,
        "warnings": warnings,
        "limitations": [
            "A compiled PDF or preview PDF is not evidence of scientific correctness, citation verification, or peer review.",
            "The pipeline rejects dangerous LaTeX patterns and does not use shell escape.",
            "Fallback preview PDFs are clearly marked and are not equivalent to LaTeX compilation.",
        ],
    }
    write_json(project_dir / LATEX_COMPILE_REPORT_JSON, payload)
    write_text(project_dir / LATEX_COMPILE_REPORT_MD, _markdown_report(payload))
    append_audit_event(
        project_dir,
        project_id,
        "compile_auto_scientist_paper",
        "Auto Scientist paper LaTeX/PDF compile pipeline was run locally.",
        {
            "source_tex_file": source_tex,
            "compile_status": compile_status,
            "compiled_pdf": bool(pdf_file),
            "preview_pdf_generated": bool(preview_pdf_file),
        },
        source="api",
        event_category="manuscript",
        risk_level="medium" if compile_status not in {"compiled", "tool_unavailable", "compile_skipped"} else "low",
        entity_type="manuscript",
        entity_id="auto_scientist_paper_compile",
    )
    return payload


def read_paper_compile_report(project_dir: Path) -> dict[str, Any]:
    payload = _read_json(project_dir / LATEX_COMPILE_REPORT_JSON, {})
    return payload if isinstance(payload, dict) else {}
