from __future__ import annotations

from pathlib import Path

from app.tools.audit_log import append_audit_event, read_audit_log, verify_audit_hash_chain


def test_new_audit_entry_contains_event_classification_and_hash_chain_stays_valid(
    demo_project_dir: Path,
) -> None:
    entry = append_audit_event(
        demo_project_dir,
        "demo_project",
        "generate_analysis_comparison",
        "Pytest v0.8 audit classification event.",
        {"comparison_id": "analysis_compare_pytest"},
        source="test",
    )

    for field in ["event_category", "risk_level", "entity_type", "entity_id"]:
        assert entry.get(field)

    records = read_audit_log(demo_project_dir, limit=1)
    assert records[-1]["audit_id"] == entry["audit_id"]
    assert records[-1]["event_category"] == "analysis"
    assert records[-1]["risk_level"] in {"low", "medium", "high"}
    assert verify_audit_hash_chain(demo_project_dir)["valid"] is True

