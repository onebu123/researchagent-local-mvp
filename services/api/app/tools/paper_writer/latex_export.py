from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.tools.audit_log import append_audit_event
from app.tools.paper_writer.manuscript_contract import AI_DRAFT_NOTICE, read_text, utc_now, write_project_text
from app.tools.paper_writer.section_writer import DRAFT_FULL_MD

DRAFT_FULL_TEX = "manuscript/draft_full.tex"


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
        if line.startswith(">"):
            lines.append(r"\begin{quote}" + _latex_escape(line.lstrip("> ")) + r"\end{quote}")
            continue
        if line.startswith("# "):
            title = _latex_escape(line[2:].strip())
            if not lines:
                lines.append(r"\title{" + title + "}")
            else:
                lines.append(r"\section{" + title + "}")
            continue
        if line.startswith("## "):
            lines.append(r"\subsection{" + _latex_escape(line[3:].strip()) + "}")
            continue
        cleaned = re.sub(r"`([^`]+)`", r"\texttt{\1}", line)
        lines.append(_latex_escape(cleaned))
    return "\n\n".join(lines)


def read_latex_export_status(project_dir: Path) -> dict[str, Any]:
    path = project_dir / DRAFT_FULL_TEX
    return {
        "available": path.exists(),
        "latex_file": DRAFT_FULL_TEX if path.exists() else None,
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def export_draft_latex(project_dir: Path, project_id: str) -> dict[str, Any]:
    draft_markdown = read_text(project_dir / DRAFT_FULL_MD)
    if not draft_markdown:
        raise FileNotFoundError("manuscript/draft_full.md does not exist; generate the auto paper draft first")
    body = _markdown_to_latex(draft_markdown)
    latex = "\n".join(
        [
            r"\documentclass[11pt]{article}",
            r"\usepackage[margin=1in]{geometry}",
            r"\usepackage{hyperref}",
            r"\usepackage{longtable}",
            r"\author{ResearchAgent Auto Paper Writer}",
            r"\date{Draft generated from local project evidence}",
            "",
            r"\begin{document}",
            r"\maketitle",
            r"\begin{quote}",
            _latex_escape(AI_DRAFT_NOTICE),
            r"\end{quote}",
            body,
            r"\section*{References}",
            "Verified references are not automatically generated. Use the local BibTeX and human review workflows before external use.",
            r"\end{document}",
            "",
        ]
    )
    write_project_text(project_dir, DRAFT_FULL_TEX, latex)
    append_audit_event(
        project_dir,
        project_id,
        "export_auto_paper_latex",
        "Auto Paper Writer exported a LaTeX draft from Markdown.",
        {"latex_file": DRAFT_FULL_TEX, "source_markdown_file": DRAFT_FULL_MD},
        source="api",
        event_category="manuscript",
        risk_level="low",
        entity_type="manuscript",
        entity_id="draft_full_latex",
    )
    return {
        "project_id": project_id,
        "created_at": utc_now(),
        "latex_file": DRAFT_FULL_TEX,
        "source_markdown_file": DRAFT_FULL_MD,
        "compiled_pdf": False,
        "limitations": [
            "LaTeX export is a source draft only; PDF compilation is not performed by this endpoint.",
            "References are placeholders until human verification and BibTeX generation are complete.",
        ],
    }
