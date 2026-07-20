# tests/test_segmentation.py
import pytest
from agents.segmentation import run_segmentation, get_segmentation_summary


def make_supplier(name, spend, country="USA", sole_source="N"):
    return {
        "supplier_name": name,
        "category": "Test Category",
        "annual_spend_usd": spend,
        "country": country,
        "contact_name": "Test Contact",
        "contact_email": "test@example.com",
        "sole_source": sole_source,
    }


def test_tiers_follow_cumulative_spend():
    # Total 1,000: cumulative % before each supplier is 0 / 70 / 90 / 95
    suppliers = [
        make_supplier("Big", 700),
        make_supplier("Mid", 200),
        make_supplier("Small", 50),
        make_supplier("Tiny", 50),
    ]
    result = run_segmentation(suppliers, threshold_a=70, threshold_b=90)
    tiers = {s["supplier_name"]: s["tier"] for s in result}
    assert tiers == {"Big": "A", "Mid": "B", "Small": "C", "Tiny": "C"}


def test_result_sorted_by_spend_with_ranks():
    suppliers = [
        make_supplier("Small", 10),
        make_supplier("Big", 500),
        make_supplier("Mid", 100),
    ]
    result = run_segmentation(suppliers)
    assert [s["supplier_name"] for s in result] == ["Big", "Mid", "Small"]
    assert [s["spend_rank"] for s in result] == [1, 2, 3]


def test_custom_thresholds_change_boundaries():
    suppliers = [
        make_supplier("Big", 700),
        make_supplier("Mid", 200),
        make_supplier("Small", 50),
        make_supplier("Tiny", 50),
    ]
    # Lower thresholds push everyone after the first supplier into C
    result = run_segmentation(suppliers, threshold_a=50, threshold_b=60)
    tiers = [s["tier"] for s in result]
    assert tiers == ["A", "C", "C", "C"]


def test_sole_source_and_international_flags():
    suppliers = [
        make_supplier("Domestic", 500, country="usa", sole_source="Y"),
        make_supplier("Foreign", 300, country="Germany", sole_source="n"),
        make_supplier("Other", 200),
    ]
    result = {s["supplier_name"]: s for s in run_segmentation(suppliers)}
    assert result["Domestic"]["sole_source_flag"] is True
    assert result["Domestic"]["international_flag"] is False
    assert result["Foreign"]["sole_source_flag"] is False
    assert result["Foreign"]["international_flag"] is True


def test_ai_managed_only_for_b_and_c_tiers():
    suppliers = [
        make_supplier("Big", 700),
        make_supplier("Mid", 200),
        make_supplier("Small", 100),
    ]
    for s in run_segmentation(suppliers, threshold_a=70, threshold_b=90):
        assert s["ai_managed"] == (s["tier"] in ("B", "C"))


def test_spend_pct_sums_to_100():
    suppliers = [make_supplier(f"S{i}", spend) for i, spend in enumerate([300, 200, 100, 50])]
    result = run_segmentation(suppliers)
    assert sum(s["spend_pct"] for s in result) == pytest.approx(100, abs=0.1)


def test_fewer_than_three_suppliers_raises():
    suppliers = [make_supplier("One", 100), make_supplier("Two", 50)]
    with pytest.raises(ValueError, match="at least 3 suppliers"):
        run_segmentation(suppliers)


def test_zero_total_spend_raises():
    suppliers = [make_supplier(f"S{i}", 0) for i in range(3)]
    with pytest.raises(ValueError, match="zero"):
        run_segmentation(suppliers)


def test_segmentation_summary_counts_and_spend():
    suppliers = [
        make_supplier("Big", 700),
        make_supplier("Mid", 200),
        make_supplier("Small", 50),
        make_supplier("Tiny", 50),
    ]
    summary = get_segmentation_summary(run_segmentation(suppliers, 70, 90))
    assert summary["A"] == {"count": 1, "spend": 700}
    assert summary["B"] == {"count": 1, "spend": 200}
    assert summary["C"] == {"count": 2, "spend": 100}
