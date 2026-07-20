# agents/message_gen.py
import time
import streamlit as st
from utils.api_handler import call_llm_with_retry, RateLimitError, AuthError, APIError, TimeoutError

# Tone matrix: (tier, sole_source, international) → tone
TONE_MATRIX = {
    ("C", False, False): "Direct, firm",
    ("C", True,  False): "Collaborative but clear",
    ("C", False, True):  "Formal, relationship-aware",
    ("C", True,  True):  "Formal, collaborative — flag for escalation review",
    ("B", False, False): "Professional, partnership-oriented",
    ("B", True,  False): "Collaborative, long-term framing",
    ("B", False, True):  "Formal, mutual benefit framing",
    ("B", True,  True):  "Formal, strategic relationship framing",
}


def get_tone(supplier: dict) -> str:
    tier = supplier.get("tier", "C")
    sole = supplier.get("sole_source_flag", False)
    intl = supplier.get("international_flag", False)
    return TONE_MATRIX.get((tier, sole, intl), "Professional, direct")


MESSAGE_PROMPT = """You are a senior procurement manager writing a real email to a supplier contact you know professionally.

Supplier profile:
- Name: {supplier_name}
- Category: {category}
- Annual spend: ${annual_spend_usd:,.0f}
- Tier: {tier}
- Sole source: {sole_source}
- Country: {country}
- Last negotiation: {last_negotiation_date}
- Negotiation lever: {lever}
- Savings target: {savings_target}
- Tone: {tone}
- Notes: {notes}

Write the email as a real person would — direct, warm where appropriate, and specific to this supplier. Get to the point quickly. Use short sentences. Vary sentence length.

Format: Start with the greeting, followed by an empty line, then paragraph 1, followed by an empty line, then paragraph 2, followed by an empty line, then the sign-off. Ensure there is exactly one empty line between each part to provide a single space. No line breaks within a paragraph — sentences flow together as prose.

Greeting: "{greeting_text}" on its own line.
Paragraph 1: Write 1–2 sentences of genuine context specific to this supplier, then the ask stated clearly — all as one flowing block of prose.
Paragraph 2: One brief reason the ask makes sense for both sides, then a concrete next step (call, reply, meeting) — all as one flowing block of prose.
Sign-off: "Best regards," followed by "{sender_name}" on the next line.

Do not put a line break between sentences within a paragraph. Each paragraph is a block of flowing prose.

The SUBJECT line must be 6–8 words maximum. It is a short email subject, not a sentence from the body.

Banned phrases — never use any of these:
"I hope this email finds you well"
"I wanted to reach out"
"touch base"
"mutually beneficial"
"synergies" / "value-add" / "leverage"
"solid foundation"
"explore opportunities"
"in today's dynamic environment"
"I am writing to"
"As per our"
"Please do not hesitate"
"I look forward to hearing from you"

Rules:
- Maximum 200 words for the body
- Never mention AI or automation
- Never be aggressive or threatening
- No corporate filler — every sentence must carry meaning
- Write the subject line like a human would, not a press release

Respond in this exact format — follow the example below precisely. The SUBJECT line is short (3–6 words). The greeting "{greeting_text}" always goes inside BODY, never on the SUBJECT line.

SUBJECT: [3–6 word subject]
BODY:
{greeting_text}

[Paragraph 1 — context + ask as flowing prose]

[Paragraph 2 — reasoning + next step as flowing prose]

Best regards,
{sender_name}

Example output (do not copy this — write a new one based on the supplier profile above):
SUBJECT: Payment Terms Discussion
BODY:
{greeting_text}

We've been sourcing packaging from you for two years and the consistency has been appreciated. I'd like to open a conversation about moving our terms from Net 30 to Net 45 — it would improve our cash position while keeping our annual spend with you stable.

That's a straightforward change that costs you nothing upfront, and I think it's worth a quick call to work through. Are you free this week or next?

Best regards,
{sender_name}"""

REGENERATE_SUFFIX = """
Previous draft was rejected. Reason given by user: "{reason}"
Adjust the draft accordingly. Keep all other parameters the same."""


def build_message_prompt(supplier: dict, intelligence: dict, regeneration_reason: str = None, sender_name: str = "") -> str:
    tone = intelligence.get("tone_recommendation") or get_tone(supplier)
    lever = intelligence.get("lever", "price reduction")
    savings_low = intelligence.get("savings_target_low", 5)
    savings_high = intelligence.get("savings_target_high", 8)
    savings_str = f"{savings_low}–{savings_high}%"

    last_neg = supplier.get("last_negotiation_date", "Not on record")
    if not last_neg or str(last_neg).strip() in ["", "nan", "None"]:
        last_neg = "Not on record"

    contact_name = str(supplier.get("contact_name", "")).strip()
    if contact_name and contact_name.lower() != "nan":
        greeting_text = f"Hi {contact_name},"
    else:
        greeting_text = "Hi,"

    prompt = MESSAGE_PROMPT.format(
        supplier_name=supplier.get("supplier_name", ""),
        category=supplier.get("category", ""),
        annual_spend_usd=float(supplier.get("annual_spend_usd", 0)),
        tier=supplier.get("tier", ""),
        sole_source=supplier.get("sole_source", "N"),
        country=supplier.get("country", ""),
        last_negotiation_date=last_neg,
        lever=lever,
        savings_target=savings_str,
        tone=tone,
        notes=supplier.get("notes", "None provided"),
        greeting_text=greeting_text,
        sender_name=sender_name,
    )

    if regeneration_reason:
        prompt += REGENERATE_SUFFIX.format(reason=regeneration_reason)

    return prompt


def parse_message_response(raw_text: str) -> dict:
    """Extract subject and body from structured response."""
    subject = ""
    body = ""
    subject_overflow = ""

    lines = raw_text.strip().split("\n")
    body_lines = []
    in_body = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("SUBJECT:"):
            raw_subject = stripped.replace("SUBJECT:", "").strip()
            # Safety net: if greeting leaked onto the subject line, split it off
            hi_idx = raw_subject.find(" Hi ")
            if hi_idx != -1:
                subject_overflow = raw_subject[hi_idx:].strip()
                raw_subject = raw_subject[:hi_idx].strip()
            subject = raw_subject
        elif stripped == "BODY:":
            in_body = True
            if subject_overflow:
                body_lines.append(subject_overflow)
        elif in_body:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()

    # Fallback if parsing failed
    if not subject or not body:
        parts = raw_text.split("\n\n", 1)
        subject = parts[0].replace("Subject:", "").replace("SUBJECT:", "").strip()
        body = parts[1].strip() if len(parts) > 1 else raw_text.strip()

    word_count = len(body.split())
    return {
        "subject": subject,
        "body": body,
        "word_count": word_count,
        "over_limit": word_count > 200,
    }


def run_message_batch(
    suppliers: list,
    intelligence_results: dict,
    api_key: str,
    progress_bar=None,
    status_text=None,
    model_name: str = None,
    sender_name: str = "",
) -> dict:
    """
    Generate messages for all B and C tier suppliers.
    Returns dict keyed by supplier_name.
    """
    eligible = [s for s in suppliers if s.get("tier") in ("B", "C")]
    results = {}
    failed = []

    for i, supplier in enumerate(eligible):
        name = supplier.get("supplier_name", f"Supplier {i+1}")
        intel = intelligence_results.get(name, {})

        if status_text:
            status_text.text(f"Drafting message for {name}... ({i+1}/{len(eligible)})")
        if progress_bar:
            progress_bar.progress(i / len(eligible))

        try:
            prompt = build_message_prompt(supplier, intel, sender_name=sender_name)
            if i > 0:
                time.sleep(0.5)

            retry_placeholder = st.empty() if st else None
            raw = call_llm_with_retry(prompt, api_key, retry_placeholder, model_name)
            parsed = parse_message_response(raw)
            results[name] = {
                **parsed,
                "approved": False,
                "sent": False,
                "regeneration_reason": None,
                "supplier": supplier,
            }

        except (RateLimitError, AuthError, APIError, TimeoutError) as e:
            failed.append({"name": name, "error": str(e), "supplier": supplier})
        except Exception as e:
            failed.append({"name": name, "error": f"Unexpected error: {str(e)}", "supplier": supplier})

    if progress_bar:
        progress_bar.progress(1.0)

    return {"results": results, "failed": failed, "total": len(eligible)}


def regenerate_message(
    supplier: dict,
    intelligence: dict,
    reason: str,
    api_key: str,
    model_name: str = None,
    sender_name: str = "",
) -> dict:
    """Regenerate a single message with a user-provided reason."""
    prompt = build_message_prompt(supplier, intelligence, regeneration_reason=reason, sender_name=sender_name)
    raw = call_llm_with_retry(prompt, api_key, model_name=model_name)
    parsed = parse_message_response(raw)
    return {
        **parsed,
        "approved": False,
        "sent": False,
        "regeneration_reason": reason,
    }
