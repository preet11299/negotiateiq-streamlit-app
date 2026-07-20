# agents/segmentation.py
from utils.validators import is_international


def run_segmentation(suppliers: list, threshold_a: float = 70.0, threshold_b: float = 90.0) -> list:
    """
    Assign ABC tiers based on cumulative spend %.
    threshold_a: cumulative % cutoff for A tier (default 70)
    threshold_b: cumulative % cutoff for B tier (default 90), rest = C

    Sole source and international are flags only — do NOT change tier assignment.

    Returns enriched supplier list with tier, cumulative %, rank, flags.
    """
    if len(suppliers) < 3:
        raise ValueError(
            "Please add at least 3 suppliers to run segmentation. "
            "ABC classification requires a minimum supplier base to be meaningful."
        )

    # Sort by spend descending
    sorted_suppliers = sorted(suppliers, key=lambda x: float(x.get("annual_spend_usd", 0)), reverse=True)
    total_spend = sum(float(s.get("annual_spend_usd", 0)) for s in sorted_suppliers)

    if total_spend == 0:
        raise ValueError("Total spend is zero — cannot run segmentation.")

    cumulative = 0.0
    result = []

    for rank, supplier in enumerate(sorted_suppliers, start=1):
        spend = float(supplier.get("annual_spend_usd", 0))
        cumulative += spend
        cumulative_pct = (cumulative / total_spend) * 100

        # Tier assignment
        if cumulative_pct - (spend / total_spend * 100) < threshold_a:
            tier = "A"
        elif cumulative_pct - (spend / total_spend * 100) < threshold_b:
            tier = "B"
        else:
            tier = "C"

        # Flags (informational only)
        sole_source = str(supplier.get("sole_source", "N")).strip().upper() == "Y"
        international = is_international(supplier.get("country", "USA"))
        ai_managed = tier in ("B", "C")

        enriched = {
            **supplier,
            "tier": tier,
            "spend_rank": rank,
            "cumulative_pct": round(cumulative_pct, 1),
            "spend_pct": round((spend / total_spend) * 100, 2),
            "sole_source_flag": sole_source,
            "international_flag": international,
            "ai_managed": ai_managed,
            "total_spend": total_spend,
        }
        result.append(enriched)

    return result


def get_segmentation_summary(segmented: list) -> dict:
    """Return summary counts and spend by tier for visualization."""
    summary = {"A": {"count": 0, "spend": 0}, "B": {"count": 0, "spend": 0}, "C": {"count": 0, "spend": 0}}
    for s in segmented:
        tier = s.get("tier", "C")
        summary[tier]["count"] += 1
        summary[tier]["spend"] += float(s.get("annual_spend_usd", 0))
    return summary


