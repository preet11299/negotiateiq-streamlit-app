# data/demo_outputs.py
# Pre-generated intelligence agent outputs and negotiation messages for demo mode.
# Keyed by supplier_name. Only B and C tier suppliers have outputs.
# A tier suppliers are flagged as human-led and excluded from AI flow.

DEMO_INTELLIGENCE = {
    "BuildRight Facilities": {
        "spend_summary": "BuildRight Facilities provides facilities management services (janitorial and HVAC) across 3 sites at $142,000 annually, representing approximately 6.7% of total addressable spend.",
        "category_context": "Facilities management is a competitive market with multiple qualified vendors in most metro areas. Service quality and reliability are primary switching costs, not proprietary capability.",
        "lever": "Price reduction (5–8% target via competitive rebid threat)",
        "savings_target_low": 5,
        "savings_target_high": 8,
        "risk_summary": "Low risk. Multiple-source category. Last negotiated May 2023 — relationship not stale but no uplift since.",
        "relationship_staleness": False,
        "tone_recommendation": "Professional, partnership-oriented",
        "tier": "B",
    },
    "Delta MRO Supply": {
        "spend_summary": "Delta MRO Supply provides maintenance, repair, and operations materials at $98,000 annually (~4.6% of total spend). High transaction volume with low average order size — classic tail spend profile.",
        "category_context": "MRO is highly competitive. Catalog pricing is rarely the best available rate. Consolidation rebates and volume commitments routinely unlock 7–12% reductions with incumbent vendors.",
        "lever": "Price reduction via volume consolidation rebate",
        "savings_target_low": 7,
        "savings_target_high": 12,
        "risk_summary": "Low risk. Not sole source. Last negotiated Aug 2022 — over 18 months stale. Strong leverage position.",
        "relationship_staleness": True,
        "tone_recommendation": "Direct, firm",
        "tier": "B",
    },
    "EuroLogix BV": {
        "spend_summary": "EuroLogix BV handles all EU cross-border freight at $87,000 annually (~4.1% of total spend). International exposure with Netherlands-based operations.",
        "category_context": "International freight rates fluctuate with fuel surcharges and lane capacity. Payment terms extension is typically an easier win than rate reduction for cross-border freight providers.",
        "lever": "Payment terms extension (Net 45 → Net 60)",
        "savings_target_low": 2,
        "savings_target_high": 4,
        "risk_summary": "Moderate. International supplier — currency and lead-time risk. Formal tone required. Terms improvement reduces cash flow exposure.",
        "relationship_staleness": False,
        "tone_recommendation": "Formal, relationship-aware",
        "tier": "B",
    },
    "SteadyPower Industrial": {
        "spend_summary": "SteadyPower Industrial supplies electrical components at $74,000 annually (~3.5% of total spend). Current Net 15 payment terms are unusually short for this category.",
        "category_context": "Electrical MRO is moderately competitive. Net 15 terms are atypical and represent an unnecessary cash flow burden. Extending to Net 30 is a standard industry norm that most vendors will accept.",
        "lever": "Payment terms extension (Net 15 → Net 30 or Net 45)",
        "savings_target_low": 3,
        "savings_target_high": 5,
        "risk_summary": "Low risk. Not sole source. Terms improvement is low-friction ask — no pricing confrontation required.",
        "relationship_staleness": False,
        "tone_recommendation": "Direct, firm",
        "tier": "B",
    },
    "Bright Office Supplies": {
        "spend_summary": "Bright Office Supplies provides office consumables at $52,000 annually (~2.5% of total spend). No formal negotiation has ever taken place — currently on default catalog pricing.",
        "category_context": "Office supplies is one of the most competitive procurement categories. Catalog pricing is almost always 10–20% above negotiated rates. GPO alternatives and e-procurement platforms have commoditized pricing.",
        "lever": "Price reduction (off-catalog negotiated rate or volume discount)",
        "savings_target_low": 10,
        "savings_target_high": 18,
        "risk_summary": "Very low risk. Not sole source. Never negotiated. Maximum leverage available — any reduction is pure gain.",
        "relationship_staleness": True,
        "tone_recommendation": "Direct, firm",
        "tier": "C",
    },
    "IndoPack Solutions": {
        "spend_summary": "IndoPack Solutions is the sole source for bio-degradable inner packaging at $43,000 annually (~2.0% of total spend). India-based with currency risk exposure.",
        "category_context": "Specialty sustainable packaging from sole-source international suppliers carries switching costs and compliance risk. Price negotiation is inadvisable. Payment terms and lead time flexibility are the appropriate levers.",
        "lever": "Payment terms extension (Net 60 → Net 75) + lead time buffer agreement",
        "savings_target_low": 2,
        "savings_target_high": 3,
        "risk_summary": "High complexity. Sole source + international. Currency fluctuation risk flagged. Price negotiation off the table. Relationship preservation critical.",
        "relationship_staleness": True,
        "tone_recommendation": "Formal, collaborative, escalate flag",
        "tier": "C",
    },
    "ClearView Cleaning Co": {
        "spend_summary": "ClearView Cleaning provides secondary janitorial services on a month-to-month contract at $38,000 annually (~1.8% of total spend).",
        "category_context": "Month-to-month janitorial contracts offer strong renegotiation leverage. Committing to a 12-month term can unlock 8–12% rate reductions as the vendor gains revenue visibility.",
        "lever": "Price reduction in exchange for 12-month contract commitment",
        "savings_target_low": 8,
        "savings_target_high": 12,
        "risk_summary": "Low risk. Multiple source. Month-to-month structure gives buyer full leverage. Easy to rebid if needed.",
        "relationship_staleness": False,
        "tone_recommendation": "Direct, firm",
        "tier": "C",
    },
    "FastPrint Media": {
        "spend_summary": "FastPrint Media supplies marketing print materials at $29,000 annually (~1.4% of total spend). Spend is declining as digital channels grow, reducing vendor leverage.",
        "category_context": "Print media is a shrinking category facing structural demand decline. Vendors in this space are under margin pressure and typically willing to sharpen pricing to retain existing accounts.",
        "lever": "Price reduction (7–10% off current rates)",
        "savings_target_low": 7,
        "savings_target_high": 10,
        "risk_summary": "Low risk. Category in structural decline — buyer has strong hand. Last negotiated Oct 2022.",
        "relationship_staleness": True,
        "tone_recommendation": "Direct, firm",
        "tier": "C",
    },
    "Solaris Raw Materials": {
        "spend_summary": "Solaris Raw Materials is a secondary resin supplier based in Brazil at $21,000 annually (~1.0% of total spend). Exchange rate fluctuations create cost unpredictability.",
        "category_context": "Secondary raw material suppliers operating in emerging markets often accept payment terms flexibility in lieu of price reduction as it improves their cash flow in USD terms.",
        "lever": "Payment terms extension (Net 45 → Net 60) + fixed-rate pricing agreement",
        "savings_target_low": 3,
        "savings_target_high": 5,
        "risk_summary": "Moderate. International. Currency risk. Secondary supplier so switching is possible but adds sourcing complexity.",
        "relationship_staleness": False,
        "tone_recommendation": "Formal, relationship-aware",
        "tier": "C",
    },
    "TechRent Equipment": {
        "spend_summary": "TechRent Equipment provides laptop and monitor leasing for temporary staff at $17,000 annually (~0.8% of total spend). Rates have not been reviewed in over 3 years.",
        "category_context": "IT equipment leasing rates have declined significantly since 2021 due to market normalization post-pandemic. Three-year-old rates are likely 15–20% above current market.",
        "lever": "Price reduction via rate benchmarking (current rates significantly above market)",
        "savings_target_low": 12,
        "savings_target_high": 18,
        "risk_summary": "Low risk. Not sole source. Rates severely stale. High savings probability on first contact.",
        "relationship_staleness": True,
        "tone_recommendation": "Direct, firm",
        "tier": "C",
    },
}

DEMO_MESSAGES = {
    "BuildRight Facilities": {
        "subject": "Partnership Review — BuildRight & [Your Company]",
        "body": """Hi Tom,

I hope you're doing well. I wanted to reach out as we're conducting a structured review of our facilities management partnerships for the coming fiscal year.

BuildRight has been a reliable partner across our three sites, and we genuinely value the consistency your team brings to our operations. As part of this review, we're aligning our vendor agreements with current market rates for comparable service scopes.

I'd like to discuss a modest adjustment to our annual service rate — in the range of 5–8% — to bring us in line with market benchmarks. This would allow us to continue investing in the partnership rather than opening a competitive rebid process.

Could we schedule a 30-minute call in the next two weeks to work through this together?

Looking forward to it.

Best regards,
[Your Name]""",
        "word_count": 131,
        "approved": False,
        "sent": False,
        "regeneration_reason": None,
    },
    "Delta MRO Supply": {
        "subject": "MRO Volume Review — Consolidation Opportunity",
        "body": """Hi Sandra,

Our team has been reviewing MRO spend patterns, and Delta MRO Supply consistently comes up as our most reliable supplier in this category.

Given our annual volume of approximately $98,000 — and our intention to consolidate further through a preferred vendor arrangement — I'd like to revisit our current pricing structure. It's been over 18 months since we last aligned on rates, and our volume has grown.

We're looking for a volume-based rebate or consolidated pricing that reflects our commitment level — targeting a 7–10% improvement on current catalog rates.

Can we connect this week or next to discuss? I'd like to move quickly as we're finalizing our vendor roster for the next 12 months.

Thanks,
[Your Name]""",
        "word_count": 120,
        "approved": False,
        "sent": False,
        "regeneration_reason": None,
    },
    "EuroLogix BV": {
        "subject": "Payment Terms Discussion — EuroLogix & [Your Company]",
        "body": """Dear Erik,

I hope this message finds you well. On behalf of [Your Company], I wanted to reach out regarding our ongoing freight partnership covering EU cross-border logistics.

We deeply value the reliability EuroLogix has provided across our European lanes, and we view this as a long-term strategic relationship. As part of our treasury and working capital optimization initiatives this year, we are reviewing payment term structures across our international supplier base.

We would like to propose adjusting our current terms from Net 45 to Net 60. This adjustment would be consistent with the terms we maintain with the majority of our international logistics partners.

I would welcome the opportunity to discuss this at your earliest convenience. Please let me know a time that works for you.

With best regards,
[Your Name]""",
        "word_count": 125,
        "approved": False,
        "sent": False,
        "regeneration_reason": None,
    },
    "SteadyPower Industrial": {
        "subject": "Payment Terms Adjustment — SteadyPower Account Review",
        "body": """Hi Brian,

Quick note as we do our annual vendor account review — SteadyPower has been a solid supplier for our electrical components needs, and we want to keep that going.

One thing that's come up in our review is our current Net 15 payment terms. For a category like electrical components, Net 30 is the standard across our supplier base, and the current structure creates unnecessary friction on our AP side.

We'd like to align SteadyPower to Net 30 — ideally effective next billing cycle. This isn't a reflection of any service issues; it's just getting our terms consistent with industry norms.

Happy to discuss if you have any questions. Otherwise, let me know if we can make this adjustment going forward.

Thanks,
[Your Name]""",
        "word_count": 118,
        "approved": False,
        "sent": False,
        "regeneration_reason": None,
    },
    "Bright Office Supplies": {
        "subject": "Pricing Review — Office Supplies Account",
        "body": """Hi Amy,

I'm reaching out as we review our office supply procurement setup for the year ahead. Bright Office Supplies has been our go-to for a while now, and we'd like to keep it that way.

That said, we've never formally reviewed our pricing arrangement, and we're currently on standard catalog rates. Given our annual spend of approximately $52,000, we believe there's room for a volume-based discount or negotiated rate card that better reflects our purchasing commitment.

We're targeting a 10–15% improvement on current pricing. I'd love to get on a call to understand what's possible — it would help us avoid having to go through a competitive sourcing process.

Are you available this week?

Best,
[Your Name]""",
        "word_count": 116,
        "approved": False,
        "sent": False,
        "regeneration_reason": None,
    },
    "IndoPack Solutions": {
        "subject": "Commercial Terms Discussion — IndoPack & [Your Company]",
        "body": """Dear Rajesh,

I hope this message finds you well. I am writing on behalf of [Your Company] to continue building on the strong partnership we have developed with IndoPack Solutions over the years.

Your bio-degradable packaging has been integral to our sustainability commitments, and we greatly value the quality and consistency your team has maintained.

As part of our working capital planning for the coming year, we are reviewing payment term structures across our international supplier base. We would like to explore whether an adjustment from our current Net 60 terms to Net 75, alongside a mutually agreed lead time buffer protocol, might be feasible for IndoPack.

We recognize this requires thoughtful discussion and would appreciate the opportunity to connect at your convenience to explore options together.

Warm regards,
[Your Name]""",
        "word_count": 130,
        "approved": False,
        "sent": False,
        "regeneration_reason": None,
    },
    "ClearView Cleaning Co": {
        "subject": "Contract Renewal Discussion — Cleaning Services",
        "body": """Hi Diana,

Hope you're well. We've been happy with the service ClearView has provided, and we'd like to continue the relationship going forward.

As we plan our facilities budget for the next 12 months, we're looking to move away from month-to-month arrangements and into annual contracts for consistency on both sides.

We'd like to commit to a 12-month agreement with ClearView — and in exchange, we're looking for a rate that reflects that volume commitment. We're targeting an 8–10% reduction on our current monthly rate as part of locking in the annual term.

Can we get on a quick call this week to put something together?

Thanks,
[Your Name]""",
        "word_count": 110,
        "approved": False,
        "sent": False,
        "regeneration_reason": None,
    },
    "FastPrint Media": {
        "subject": "Print Rates Review — FastPrint Account",
        "body": """Hi Gary,

I wanted to connect as we review our print spend for the year. FastPrint has been our supplier of record for marketing materials, and we'd like to keep that relationship in place.

Our print volume has shifted somewhat as we've moved more marketing activity online, but we still have consistent recurring needs. Given that we haven't revisited pricing since October 2022, and the market has moved meaningfully since then, we'd like to align on updated rates.

We're looking for a 7–10% reduction on our current rate card to bring us in line with current market. This would help us justify continuing with FastPrint rather than going to market.

Happy to discuss at your convenience.

Best,
[Your Name]""",
        "word_count": 118,
        "approved": False,
        "sent": False,
        "regeneration_reason": None,
    },
    "Solaris Raw Materials": {
        "subject": "Commercial Terms Review — Solaris & [Your Company]",
        "body": """Dear Carlos,

I hope all is well. I wanted to reach out regarding our ongoing raw materials partnership and a couple of items we'd like to discuss as we plan ahead.

First, given recent currency fluctuations affecting our USD-BRL exposure, we'd like to explore a fixed-rate pricing agreement for the next 12 months to provide predictability for both parties.

Second, as part of a broader working capital review, we'd like to discuss adjusting our payment terms from Net 45 to Net 60, which is more consistent with our standard international supplier terms.

We value the flexibility Solaris has provided as a secondary supplier and are committed to maintaining a strong relationship. Please let me know when you'd be available to discuss.

With best regards,
[Your Name]""",
        "word_count": 128,
        "approved": False,
        "sent": False,
        "regeneration_reason": None,
    },
    "TechRent Equipment": {
        "subject": "Equipment Leasing Rate Review — TechRent Account",
        "body": """Hi Lisa,

Hope you're doing well. We've been using TechRent for our temp staff equipment leasing for a few years now, and the service has been smooth.

That said, I realized we haven't formally reviewed our leasing rates since late 2021 — the market for IT equipment has changed significantly since then, and current rates are well below what we're paying.

I'd like to schedule a brief call to discuss bringing our rates in line with the current market. Based on our review, we're looking for a 12–18% reduction on our current leasing fees. Given our consistent volume, I believe this is a reasonable ask.

Can we find time this week?

Thanks,
[Your Name]""",
        "word_count": 114,
        "approved": False,
        "sent": False,
        "regeneration_reason": None,
    },
}
