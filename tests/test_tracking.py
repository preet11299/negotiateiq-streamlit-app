# tests/test_tracking.py
from datetime import datetime, timedelta

from agents.tracking import (
    PIPELINE_STAGES, initialize_pipeline, advance_stage, add_note,
    get_stale_suppliers, calculate_kpis,
)


def make_supplier(name="Acme", tier="C", spend=100000):
    return {
        "supplier_name": name, "category": "MRO", "tier": tier,
        "annual_spend_usd": spend, "country": "USA",
        "contact_name": "Jo", "contact_email": "jo@acme.com",
    }


def build(messages=None, intelligence=None, **supplier_kwargs):
    supplier = make_supplier(**supplier_kwargs)
    return initialize_pipeline(
        [supplier],
        messages or {},
        intelligence or {supplier["supplier_name"]: {"savings_target_low": 5, "savings_target_high": 10}},
    )


def test_stages_are_the_four_honest_ones():
    assert PIPELINE_STAGES == ["Draft", "Approved", "In progress", "Closed"]


def test_unapproved_message_starts_as_draft():
    assert build(messages={"Acme": {"approved": False}})[0]["stage"] == "Draft"


def test_approved_message_starts_as_approved():
    assert build(messages={"Acme": {"approved": True}})[0]["stage"] == "Approved"


def test_sent_message_starts_in_progress():
    pipeline = build(messages={"Acme": {"approved": True, "sent": True, "sent_date": "2026-01-05"}})
    assert pipeline[0]["stage"] == "In progress"
    assert pipeline[0]["sent_date"] == "2026-01-05"


def test_a_tier_suppliers_are_excluded_from_pipeline():
    assert build(tier="A", messages={"Acme": {"approved": True}}) == []


def test_savings_derived_from_spend_and_targets():
    entry = build(spend=100000)[0]
    assert entry["savings_low"] == 5000
    assert entry["savings_high"] == 10000


def test_advancing_to_in_progress_stamps_the_start_date():
    pipeline = build(messages={"Acme": {"approved": True}})
    pipeline = advance_stage(pipeline, "Acme", "In progress")
    assert pipeline[0]["stage"] == "In progress"
    assert pipeline[0]["sent_date"] == datetime.now().strftime("%Y-%m-%d")


def test_advancing_records_a_timeline_event():
    pipeline = advance_stage(build(), "Acme", "Closed")
    assert any("Closed" in e["event"] for e in pipeline[0]["timeline"])


def test_add_note_stamps_and_appends():
    pipeline = add_note(build(), "Acme", "Called the rep")
    assert "Called the rep" in pipeline[0]["pipeline_notes"][0]


def test_stale_flags_only_long_running_in_progress():
    pipeline = build(messages={"Acme": {"approved": True}})
    pipeline = advance_stage(pipeline, "Acme", "In progress")
    pipeline[0]["sent_date"] = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

    assert get_stale_suppliers(pipeline, 7)[0]["days_elapsed"] == 10
    assert get_stale_suppliers(pipeline, 30) == []


def test_closed_suppliers_are_never_stale():
    pipeline = build(messages={"Acme": {"approved": True}})
    pipeline = advance_stage(pipeline, "Acme", "In progress")
    pipeline[0]["sent_date"] = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    pipeline = advance_stage(pipeline, "Acme", "Closed")
    assert get_stale_suppliers(pipeline, 7) == []


def test_kpis_count_every_stage():
    kpis = calculate_kpis(build(messages={"Acme": {"approved": True}}))
    assert kpis["total"] == 1
    assert kpis["stage_counts"] == {"Draft": 0, "Approved": 1, "In progress": 0, "Closed": 0}
    assert set(kpis["stage_counts"]) == set(PIPELINE_STAGES)
