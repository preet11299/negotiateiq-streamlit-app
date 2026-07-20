# tests/test_validators.py
from datetime import datetime, timedelta

import pandas as pd

from utils.validators import (
    validate_csv, validate_manual_entry, is_international, is_stale,
)


def make_df(rows=3, **overrides):
    data = {
        "supplier_name": [f"Supplier {i}" for i in range(rows)],
        "category": ["Widgets"] * rows,
        "annual_spend_usd": [1000.0 * (i + 1) for i in range(rows)],
        "country": ["USA"] * rows,
        "contact_name": [f"Contact {i}" for i in range(rows)],
        "contact_email": [f"contact{i}@example.com" for i in range(rows)],
        "sole_source": ["N"] * rows,
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_valid_csv_passes():
    result = validate_csv(make_df())
    assert result["valid"] is True
    assert result["errors"] == []
    assert len(result["cleaned_df"]) == 3


def test_missing_required_column_fails():
    df = make_df().drop(columns=["contact_email"])
    result = validate_csv(df)
    assert result["valid"] is False
    assert any("contact_email" in e for e in result["errors"])


def test_column_names_are_normalized():
    df = make_df().rename(columns={"supplier_name": "Supplier Name"})
    result = validate_csv(df)
    assert result["valid"] is True
    assert "supplier_name" in result["cleaned_df"].columns


def test_non_numeric_spend_fails():
    result = validate_csv(make_df(annual_spend_usd=["abc", 1000, 2000]))
    assert result["valid"] is False
    assert any("must be a number" in e for e in result["errors"])


def test_negative_spend_fails():
    result = validate_csv(make_df(annual_spend_usd=[-5, 1000, 2000]))
    assert result["valid"] is False
    assert any("positive" in e for e in result["errors"])


def test_invalid_sole_source_fails():
    result = validate_csv(make_df(sole_source=["MAYBE", "N", "Y"]))
    assert result["valid"] is False
    assert any("sole_source" in e for e in result["errors"])


def test_yes_no_normalized_to_y_n():
    result = validate_csv(make_df(sole_source=["yes", "NO", "Y"]))
    assert result["valid"] is True
    assert list(result["cleaned_df"]["sole_source"]) == ["Y", "N", "Y"]


def test_bad_email_warns_but_passes():
    result = validate_csv(make_df(contact_email=["not-an-email", "a@b.com", "c@d.com"]))
    assert result["valid"] is True
    assert any("looks invalid" in w for w in result["warnings"])


def test_fewer_than_three_rows_fails():
    result = validate_csv(make_df(rows=2))
    assert result["valid"] is False
    assert any("at least 3 suppliers" in e for e in result["errors"])


def test_manual_entry_valid():
    entry = {
        "supplier_name": "Acme", "category": "Widgets",
        "annual_spend_usd": 5000, "country": "USA",
        "contact_name": "Jo", "contact_email": "jo@acme.com",
        "sole_source": "N",
    }
    assert validate_manual_entry(entry)["valid"] is True


def test_manual_entry_missing_fields_and_bad_spend():
    result = validate_manual_entry({"supplier_name": "Acme", "annual_spend_usd": 0})
    assert result["valid"] is False
    assert any("category" in e for e in result["errors"])
    assert any("positive" in e for e in result["errors"])


def test_is_international():
    for domestic in ["USA", "usa", "United States", "u.s.", "U.S.A."]:
        assert is_international(domestic) is False
    for foreign in ["Germany", "Japan", "Brazil"]:
        assert is_international(foreign) is True


def test_is_stale():
    two_years_ago = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    last_month = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    assert is_stale(two_years_ago) is True
    assert is_stale(last_month) is False
    assert is_stale("") is True          # never negotiated counts as stale
    assert is_stale("not-a-date") is False
