# agents/tracking.py
from datetime import datetime

# Stages the app can actually justify: the first two it derives itself, the last
# two a person sets from memory. Finer-grained states (replied, negotiating)
# would need mailbox access the app deliberately does not have.
PIPELINE_STAGES = ["Draft", "Approved", "In progress", "Closed"]


def initialize_pipeline(suppliers: list, messages: dict, intelligence: dict) -> list:
    """
    Build initial pipeline entries for all B and C tier suppliers
    that have an approved message.
    """
    pipeline = []
    for supplier in suppliers:
        if supplier.get("tier") not in ("B", "C"):
            continue
        name = supplier.get("supplier_name", "")
        msg = messages.get(name, {})
        intel = intelligence.get(name, {})

        spend = float(supplier.get("annual_spend_usd", 0))
        savings_low_pct = intel.get("savings_target_low", 3) / 100
        savings_high_pct = intel.get("savings_target_high", 8) / 100

        if msg.get("sent"):
            stage = "In progress"
        elif msg.get("approved"):
            stage = "Approved"
        else:
            stage = "Draft"

        entry = {
            "supplier_name": name,
            "category": supplier.get("category", ""),
            "tier": supplier.get("tier", ""),
            "annual_spend_usd": spend,
            "country": supplier.get("country", ""),
            "contact_name": supplier.get("contact_name", ""),
            "contact_email": supplier.get("contact_email", ""),
            "sole_source_flag": supplier.get("sole_source_flag", False),
            "international_flag": supplier.get("international_flag", False),
            "lever": intel.get("lever", ""),
            "savings_low": round(spend * savings_low_pct),
            "savings_high": round(spend * savings_high_pct),
            "stage": stage,
            "sent_date": msg.get("sent_date"),
            "pipeline_notes": [],
            "timeline": [
                {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "event": f"Entered pipeline at {stage}"}
            ],
            "message_subject": msg.get("subject", ""),
            "message_body": msg.get("body", ""),
        }
        pipeline.append(entry)

    return pipeline


def advance_stage(pipeline: list, supplier_name: str, new_stage: str) -> list:
    """Move a supplier to a new pipeline stage."""
    for entry in pipeline:
        if entry["supplier_name"] == supplier_name:
            old_stage = entry["stage"]
            entry["stage"] = new_stage

            # Starting a conversation stamps the clock the staleness alert reads.
            if new_stage == "In progress" and not entry.get("sent_date"):
                entry["sent_date"] = datetime.now().strftime("%Y-%m-%d")

            entry["timeline"].append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "event": f"Stage changed: {old_stage} → {new_stage}",
            })
    return pipeline


def add_note(pipeline: list, supplier_name: str, note: str) -> list:
    """Add a note to a supplier's pipeline entry."""
    for entry in pipeline:
        if entry["supplier_name"] == supplier_name:
            stamped = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {note}"
            entry["pipeline_notes"].append(stamped)
            entry["timeline"].append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "event": f"Note added: {note[:60]}",
            })
    return pipeline


def get_stale_suppliers(pipeline: list, threshold_days: int = 7) -> list:
    """Return suppliers sitting 'In progress' for longer than threshold_days."""
    stale = []
    for entry in pipeline:
        if entry["stage"] == "In progress" and entry.get("sent_date"):
            try:
                sent = datetime.strptime(entry["sent_date"], "%Y-%m-%d")
                days_elapsed = (datetime.now() - sent).days
                if days_elapsed >= threshold_days:
                    stale.append({**entry, "days_elapsed": days_elapsed})
            except Exception:
                pass
    return stale


def calculate_kpis(pipeline: list) -> dict:
    """Calculate the 4 KPIs for the summary strip."""
    total = len(pipeline)
    stage_counts = {stage: 0 for stage in PIPELINE_STAGES}
    for entry in pipeline:
        stage_counts[entry.get("stage", "Draft")] += 1

    total_low = sum(e.get("savings_low", 0) for e in pipeline)
    total_high = sum(e.get("savings_high", 0) for e in pipeline)

    return {
        "total": total,
        "stage_counts": stage_counts,
        "savings_low": total_low,
        "savings_high": total_high,
        "savings_range": f"${total_low:,.0f} — ${total_high:,.0f} (estimated)",
    }


