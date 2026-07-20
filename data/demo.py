# data/demo.py
# Demo mode loaders — join pre-generated AI outputs to live segmentation results
# so the full 6-step flow works without an API key.
from data.demo_suppliers import DEMO_SUPPLIERS
from data.demo_outputs import DEMO_INTELLIGENCE, DEMO_MESSAGES

DEMO_SENDER_NAME = "Alex Morgan"
DEMO_COMPANY_NAME = "Meridian Manufacturing"


def load_demo_suppliers() -> list:
    """Fresh copies of the sample suppliers for session state."""
    return [dict(s) for s in DEMO_SUPPLIERS]


def load_demo_intelligence(segmented: list) -> dict:
    """
    Build intelligence results for eligible (B/C) suppliers from the
    pre-generated briefs, shaped exactly like run_intelligence_batch output.
    Tier comes from the live segmentation, not the canned data, so the
    demo stays consistent if the user moves the threshold sliders.
    """
    results = {}
    for supplier in segmented:
        name = supplier.get("supplier_name", "")
        if supplier.get("tier") not in ("B", "C") or name not in DEMO_INTELLIGENCE:
            continue
        brief = dict(DEMO_INTELLIGENCE[name])
        brief["tier"] = supplier["tier"]
        brief["parse_success"] = True
        brief["raw_response"] = ""
        brief["supplier"] = supplier
        results[name] = brief
    return results


def load_demo_messages(segmented: list, sender_name: str = DEMO_SENDER_NAME) -> dict:
    """
    Build message results for eligible (B/C) suppliers from the pre-written
    drafts, shaped exactly like run_message_batch output.
    """
    sender_name = sender_name.strip() or DEMO_SENDER_NAME
    results = {}
    for supplier in segmented:
        name = supplier.get("supplier_name", "")
        if supplier.get("tier") not in ("B", "C") or name not in DEMO_MESSAGES:
            continue
        msg = dict(DEMO_MESSAGES[name])
        msg["subject"] = msg["subject"].replace("[Your Company]", DEMO_COMPANY_NAME)
        msg["body"] = (msg["body"]
                       .replace("[Your Name]", sender_name)
                       .replace("[Your Company]", DEMO_COMPANY_NAME))
        msg["supplier"] = supplier
        results[name] = msg
    return results
