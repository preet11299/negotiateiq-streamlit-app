# agents/intelligence.py
import json
import re
import time
import streamlit as st
from utils.api_handler import call_llm_with_retry, RateLimitError, AuthError, APIError, TimeoutError
from utils.validators import is_stale


INTELLIGENCE_PROMPT = """You are a procurement analyst building a prenegotiation fact base for the following supplier.

Supplier: {supplier_name}
Category: {category}
Annual spend: ${annual_spend_usd:,.0f}
Tier: {tier}
Sole source: {sole_source}
International: {international} — Country: {country}
Last negotiation: {last_negotiation_date}
Notes: {notes}

Based on this profile:
1. Summarize the commercial relationship in 2 sentences
2. Identify the single best negotiation lever (payment terms, price reduction, or lead time — choose ONE)
3. Suggest a realistic savings target as an integer percentage range (e.g., 5 to 8)
4. Flag any risks in 1–2 sentences
5. Recommend negotiation tone (choose from: Direct/firm | Collaborative but clear | Formal/relationship-aware | Formal/collaborative | Professional/partnership-oriented | Collaborative/long-term | Formal/mutual-benefit | Formal/strategic)

Be specific to this supplier. No generic advice. Keep each answer to 1–3 sentences max.

Respond with a single JSON object matching exactly this schema:
{{
  "summary": "<2 sentences on the commercial relationship>",
  "lever": "<single lever name and brief rationale>",
  "savings_target_low": <integer percent>,
  "savings_target_high": <integer percent>,
  "risks": "<1-2 sentences>",
  "tone": "<tone recommendation>"
}}"""


def build_intelligence_prompt(supplier: dict) -> str:
    international = supplier.get("international_flag", False)
    last_neg = supplier.get("last_negotiation_date", "Not on record")
    if not last_neg or str(last_neg).strip() in ["", "nan", "None"]:
        last_neg = "Not on record"

    return INTELLIGENCE_PROMPT.format(
        supplier_name=supplier.get("supplier_name", ""),
        category=supplier.get("category", ""),
        annual_spend_usd=float(supplier.get("annual_spend_usd", 0)),
        tier=supplier.get("tier", ""),
        sole_source=supplier.get("sole_source", "N"),
        international="Yes" if international else "No",
        country=supplier.get("country", ""),
        last_negotiation_date=last_neg,
        notes=supplier.get("notes", "None provided"),
    )


def parse_intelligence_response(raw_text: str, supplier: dict) -> dict:
    """Parse the JSON brief returned by the intelligence agent."""
    result = {
        "spend_summary": "",
        "lever": "",
        "savings_target_low": 3,
        "savings_target_high": 8,
        "risk_summary": "",
        "tone_recommendation": "",
        "relationship_staleness": is_stale(supplier.get("last_negotiation_date", "")),
        "raw_response": raw_text,
        "parse_success": True,
    }

    try:
        cleaned = raw_text.strip()
        # Strip markdown fences if the model wrapped its JSON anyway
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
        if fence:
            cleaned = fence.group(1)
        data = json.loads(cleaned)

        result["spend_summary"] = str(data.get("summary", "")).strip()
        result["lever"] = str(data.get("lever", "")).strip()
        result["risk_summary"] = str(data.get("risks", "")).strip()
        result["tone_recommendation"] = str(data.get("tone", "")).strip()

        low = int(data.get("savings_target_low", 3))
        high = int(data.get("savings_target_high", 8))
        if low > high:
            low, high = high, low
        result["savings_target_low"] = low
        result["savings_target_high"] = high

    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        result["parse_success"] = False

    # Fallback if parsing failed or the JSON was missing the summary
    if not result["spend_summary"]:
        result["spend_summary"] = raw_text[:300]
        result["parse_success"] = False

    return result


def run_intelligence_batch(
    suppliers: list,
    api_key: str,
    progress_bar=None,
    status_text=None,
    model_name: str = None,
) -> dict:
    """
    Run intelligence agent on all B and C tier suppliers.
    Returns dict keyed by supplier_name.
    Tracks successes and failures separately.
    """
    eligible = [s for s in suppliers if s.get("tier") in ("B", "C")]
    results = {}
    failed = []

    for i, supplier in enumerate(eligible):
        name = supplier.get("supplier_name", f"Supplier {i+1}")

        if status_text:
            status_text.text(f"Analyzing {name}... ({i+1}/{len(eligible)})")
        if progress_bar:
            progress_bar.progress((i) / len(eligible))

        try:
            prompt = build_intelligence_prompt(supplier)
            # Small delay between calls to avoid rate limits
            if i > 0:
                time.sleep(0.5)

            retry_placeholder = st.empty() if st else None
            raw = call_llm_with_retry(prompt, api_key, retry_placeholder,
                                      model_name, json_mode=True)
            parsed = parse_intelligence_response(raw, supplier)
            results[name] = {**parsed, "supplier": supplier}

        except (RateLimitError, AuthError, APIError, TimeoutError) as e:
            failed.append({"name": name, "error": str(e), "supplier": supplier})
        except Exception as e:
            failed.append({"name": name, "error": f"Unexpected error: {str(e)}", "supplier": supplier})

    if progress_bar:
        progress_bar.progress(1.0)

    return {"results": results, "failed": failed, "total": len(eligible)}


def run_intelligence_single(supplier: dict, api_key: str,
                            model_name: str = None) -> dict:
    """Run intelligence agent on a single supplier (for retry)."""
    prompt = build_intelligence_prompt(supplier)
    raw = call_llm_with_retry(prompt, api_key, model_name=model_name, json_mode=True)
    return parse_intelligence_response(raw, supplier)


ASK_AGENT_PROMPT = """You are a procurement analyst explaining the reasoning behind a prenegotiation analysis you generated.

Supplier: {supplier_name}
Category: {category}
Annual Spend: ${annual_spend_usd:,.0f}
Tier: {tier} — Country: {country}
Sole Source: {sole_source}
Last Negotiation: {last_negotiation_date}

Generated Brief:
- Summary: {spend_summary}
- Negotiation Lever: {lever}
- Savings Target: {savings_low}–{savings_high}%
- Risk: {risk_summary}
- Recommended Tone: {tone_recommendation}
{message_section}
Question: {question}

Answer in 2–4 sentences. Ground your reasoning in the specific supplier data above. Be direct and specific — no generic advice."""


def ask_intel_agent(
    supplier: dict,
    brief: dict,
    question: str,
    api_key: str,
    model_name: str = None,
    message: dict = None,
) -> str:
    """Answer a follow-up question about a generated intelligence brief or outreach message."""
    s = supplier
    last_neg = s.get("last_negotiation_date", "Not on record")
    if not last_neg or str(last_neg).strip() in ["", "nan", "None"]:
        last_neg = "Not on record"

    message_section = ""
    if message:
        message_section = f"\nGenerated Outreach Message:\nSubject: {message.get('subject','')}\n\n{message.get('body','')}\n"

    prompt = ASK_AGENT_PROMPT.format(
        supplier_name=s.get("supplier_name", ""),
        category=s.get("category", ""),
        annual_spend_usd=float(s.get("annual_spend_usd", 0)),
        tier=s.get("tier", ""),
        country=s.get("country", ""),
        sole_source=s.get("sole_source", "N"),
        last_negotiation_date=last_neg,
        spend_summary=brief.get("spend_summary", ""),
        lever=brief.get("lever", ""),
        savings_low=brief.get("savings_target_low", ""),
        savings_high=brief.get("savings_target_high", ""),
        risk_summary=brief.get("risk_summary", ""),
        tone_recommendation=brief.get("tone_recommendation", ""),
        message_section=message_section,
        question=question,
    )
    return call_llm_with_retry(prompt, api_key, model_name=model_name)
