from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_v16_frontend_ux_panel_is_static_and_mock_safe() -> None:
    panel_path = ROOT / "apps" / "web" / "components" / "UXConsolidationPanel.tsx"
    page_path = ROOT / "apps" / "web" / "app" / "page.tsx"
    e2e_path = ROOT / "apps" / "web" / "e2e" / "v16-ux-consolidation.spec.ts"

    panel_text = panel_path.read_text(encoding="utf-8")
    page_text = page_path.read_text(encoding="utf-8")
    e2e_text = e2e_path.read_text(encoding="utf-8")

    assert "v1.6 UX consolidation" in panel_text
    assert "Mock fallback active" in panel_text
    assert "Demo remains usable without API or network" in panel_text
    assert "onOpenWorkspaceExport" in panel_text
    assert "UXConsolidationPanel" in page_text
    assert "ux-consolidation-panel" in e2e_text

    assert "fetch(" not in panel_text
    assert "axios" not in panel_text
    assert "localStorage" not in panel_text
    assert "dangerouslySetInnerHTML" not in panel_text


def test_v16_ux_does_not_add_backend_routes_or_secrets() -> None:
    export_api = (ROOT / "services" / "api" / "app" / "api" / "export.py").read_text(
        encoding="utf-8"
    )
    panel_text = (ROOT / "apps" / "web" / "components" / "UXConsolidationPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "/export/workspace" in export_api
    assert "/ux" not in export_api.lower()
    assert "sk_live_" not in panel_text
    assert "OPENAI_API_KEY" not in panel_text
