from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_ROOT))

from app.database import initialize_database
from app.schemas import ProjectCreate
from app.services.project_service import project_service
from app.services.storage_service import storage_service
from app.tools.literature_index import build_literature_index


def reset_demo_project_dir() -> None:
    project_dir = storage_service.project_dir("demo_project").resolve()
    expected_dir = (ROOT / "projects" / "demo_project").resolve()
    if project_dir != expected_dir:
        raise RuntimeError("refuse to reset unexpected demo project path")
    if project_dir.exists():
        shutil.rmtree(project_dir)


def write_demo_literature(project_dir: Path) -> None:
    path = project_dir / "literature" / "demo_literature.md"
    path.write_text(
        """# Demo Literature Summary

This is a placeholder literature summary for materials science. It describes a mock research context around perovskite-like materials, process temperature, precursor concentration, efficiency, stability, and band gap. It is not a verified reference and must not be cited as a real paper.

## Key Ideas

- Process parameters may influence efficiency and stability.
- Data analysis should be traceable to CSV files and scripts.
- Any real manuscript must replace this placeholder with verified literature.
""",
        encoding="utf-8",
    )


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_simple_demo_pdf(project_dir: Path) -> None:
    path = project_dir / "literature" / "demo_pdf_literature.pdf"
    lines = [
        "Demo PDF Literature Placeholder",
        "This PDF is created for ResearchAgent v0.2 parser validation.",
        "It is a placeholder and not a verified reference.",
        "It mentions process temperature, concentration, efficiency, stability, and band gap.",
        "Manual verification is required before citation or submission.",
    ]
    stream_text = "\n".join(
        [
            "BT",
            "/F1 12 Tf",
            "72 740 Td",
            "16 TL",
            *[f"({_escape_pdf_text(line)}) Tj\nT*" for line in lines],
            "ET",
        ]
    )
    stream = stream_text.encode("latin-1", errors="replace")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\n"
            b"endobj\n"
        ),
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        b"5 0 obj\n<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream
        + b"\nendstream\nendobj\n",
    ]
    content = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(content))
        content.extend(obj)
    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    path.write_bytes(bytes(content))


def write_demo_csv(project_dir: Path) -> None:
    path = project_dir / "data" / "demo_data.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["sample_id", "temperature", "concentration", "efficiency", "stability", "band_gap"]
        )
        for index in range(60):
            temperature = 300 + index * 1.7
            concentration = 0.08 + (index % 12) * 0.012
            efficiency = 18.0 + index * 0.09 - concentration * 10
            stability = 76.0 + (index % 8) * 0.7 - concentration * 5
            band_gap = 1.52 + (index % 10) * 0.006 - concentration * 0.04
            writer.writerow(
                [
                    f"S{index + 1:03d}",
                    round(temperature, 3),
                    round(concentration, 4),
                    round(efficiency, 3),
                    round(stability, 3),
                    round(band_gap, 4),
                ]
            )


def main() -> None:
    initialize_database()
    reset_demo_project_dir()
    payload = ProjectCreate(
        name="新型钙钛矿材料研究",
        domain="materials",
        language="zh",
        output_format="markdown",
    )
    project_service.create_project(payload, project_id="demo_project", overwrite=True)
    project_dir = storage_service.ensure_project_structure("demo_project")
    write_demo_literature(project_dir)
    write_simple_demo_pdf(project_dir)
    write_demo_csv(project_dir)
    build_literature_index(project_dir)
    print(f"Demo project seeded at {project_dir}")


if __name__ == "__main__":
    main()
