# tests/test_intelligence_parsing.py
import json

from agents.intelligence import parse_intelligence_response

SUPPLIER = {"supplier_name": "Acme", "last_negotiation_date": ""}

BRIEF = {
    "summary": "Acme supplies widgets at $50,000 annually. Relationship is stable.",
    "lever": "Price reduction — competitive category",
    "savings_target_low": 5,
    "savings_target_high": 9,
    "risks": "Low risk. Multiple alternative vendors available.",
    "tone": "Direct/firm",
}


def test_valid_json_is_parsed():
    result = parse_intelligence_response(json.dumps(BRIEF), SUPPLIER)
    assert result["parse_success"] is True
    assert result["spend_summary"] == BRIEF["summary"]
    assert result["lever"] == BRIEF["lever"]
    assert result["savings_target_low"] == 5
    assert result["savings_target_high"] == 9
    assert result["risk_summary"] == BRIEF["risks"]
    assert result["tone_recommendation"] == BRIEF["tone"]


def test_json_wrapped_in_markdown_fences_is_parsed():
    fenced = f"```json\n{json.dumps(BRIEF)}\n```"
    result = parse_intelligence_response(fenced, SUPPLIER)
    assert result["parse_success"] is True
    assert result["spend_summary"] == BRIEF["summary"]


def test_reversed_savings_range_is_swapped():
    brief = {**BRIEF, "savings_target_low": 9, "savings_target_high": 4}
    result = parse_intelligence_response(json.dumps(brief), SUPPLIER)
    assert result["savings_target_low"] == 4
    assert result["savings_target_high"] == 9


def test_invalid_json_falls_back_to_raw_text():
    raw = "The supplier looks negotiable but I cannot produce JSON today."
    result = parse_intelligence_response(raw, SUPPLIER)
    assert result["parse_success"] is False
    assert result["spend_summary"] == raw[:300]
    assert result["savings_target_low"] == 3   # defaults preserved
    assert result["savings_target_high"] == 8


def test_staleness_computed_from_supplier():
    result = parse_intelligence_response(json.dumps(BRIEF), {"last_negotiation_date": ""})
    assert result["relationship_staleness"] is True
