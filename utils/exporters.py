# utils/exporters.py
import io
import csv
import pandas as pd


def export_audit_log_csv(audit_log: list) -> bytes:
    """Export audit log as CSV bytes."""
    if not audit_log:
        return b"timestamp,action_type,supplier_name,detail\n"

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["timestamp", "action_type", "supplier_name", "detail"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for entry in audit_log:
        writer.writerow(entry)
    return output.getvalue().encode("utf-8")


def export_pipeline_csv(suppliers: list) -> bytes:
    """Export tracking pipeline as CSV bytes."""
    if not suppliers:
        return b"No pipeline data\n"

    rows = []
    for s in suppliers:
        rows.append({
            "Supplier": s.get("supplier_name", ""),
            "Category": s.get("category", ""),
            "Tier": s.get("tier", ""),
            "Annual Spend ($)": s.get("annual_spend_usd", ""),
            "Country": s.get("country", ""),
            "Contact": s.get("contact_name", ""),
            "Email": s.get("contact_email", ""),
            "Stage": s.get("stage", "Draft"),
            "Lever": s.get("lever", ""),
            "Savings Low ($)": s.get("savings_low", ""),
            "Savings High ($)": s.get("savings_high", ""),
            "Started": s.get("sent_date", ""),
            "Notes": "; ".join(s.get("pipeline_notes", [])),
        })

    df = pd.DataFrame(rows)
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue().encode("utf-8")
