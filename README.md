# NegotiateIQ

**AI-assisted procurement negotiation for tail spend** — segments a supplier base, builds a prenegotiation brief for every low-stakes supplier, drafts the outreach email, and holds it all behind a human approval gate.

🔗 **[Live demo](https://YOUR-APP-URL.streamlit.app)** · no API key needed — click **Try Demo** on the first screen.

<!-- Add a screenshot or GIF here: drag an image into a GitHub issue, copy the generated URL, paste below.
![NegotiateIQ walkthrough](https://user-images.githubusercontent.com/...)
-->

---

## The problem

In most companies the bottom ~80% of suppliers account for ~20% of spend — and almost none of them ever get negotiated. Not because the savings aren't there, but because the labour doesn't pay for itself: a buyer spends hours researching and drafting for a supplier worth a few thousand dollars a year. Multiplied across hundreds of vendors, that's **3–8% of tail spend left on the table annually**.

NegotiateIQ attacks the labour cost, not the buyer's judgement. It automates the *preparation* — the spend analysis, the lever selection, the first draft — for suppliers where the stakes are low enough to justify it, and routes strategic suppliers to a human instead. Nothing is ever sent automatically.

## How it works

A six-step pipeline, each step gating the next:

| Step | What happens |
|------|-------------|
| **1 · Input** | Upload a supplier CSV or enter records manually (validated on the way in) |
| **2 · Segment** | ABC classification by cumulative spend — thresholds adjustable |
| **3 · Intelligence** | For each B/C supplier, an LLM builds a brief: spend summary, single best negotiation lever, savings target, risks, recommended tone |
| **4 · Messages** | Drafts the outreach email per supplier, tone-matched to tier and relationship |
| **5 · Review gate** | Pre-send checklist, per-message approve/revoke, manual copy-out to your mail client |
| **6 · Track** | Pipeline dashboard with stage management and follow-up alerts |

### Design decisions worth calling out

**A-tier suppliers never enter the AI flow.** Segmentation splits the base by cumulative spend; only B and C tier suppliers get generated briefs and drafts. Strategic suppliers are flagged human-led, because that's where relationship judgement actually matters.

**The app never sends an email.** Step 5 is a hard gate: you approve each message individually, then copy it into your own mail client. There is no send button and no mailbox integration — an AI that can email your suppliers unsupervised is a liability, not a feature.

**Only four pipeline stages.** `Draft → Approved → In progress → Closed`. Earlier versions had *Sent / Replied / Negotiating*, but with no mailbox access the app can't know whether a supplier replied — those stages were asking the user to hand-maintain state that merely looked like tracking. The app now models what it can actually justify: two stages it derives itself, two a person sets from memory.

**Structured output, not regex.** The intelligence agent requests a JSON object and calls Gemini with `response_mime_type: application/json`, so the model is constrained to valid JSON rather than emitting labelled text that gets scraped. Parsing falls back gracefully — markdown fences are stripped, an inverted savings range is corrected, and unparseable output degrades to raw text with `parse_success: False` instead of crashing the batch.

**Demo mode.** Pre-generated briefs and drafts for 15 synthetic suppliers let anyone walk the entire flow with no API key and zero API calls. Features that genuinely require the model — brief Q&A, message regeneration — are disabled with an explanation rather than failing.

## Quick start

```bash
git clone https://github.com/YOUR-USERNAME/negotiateiq.git
cd negotiateiq

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py
```

The app opens at `http://localhost:8501`. Click **Try Demo** to explore without a key, or paste a [Google Gemini API key](https://aistudio.google.com/apikey) into the sidebar to run it live (the free tier is enough).

The key is held in session state only — it is never written to disk, logged, or committed.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

39 tests covering the deterministic core: ABC tier boundaries and flag derivation, CSV/manual-entry validation and normalization, staleness rules, pipeline stage transitions, and the intelligence agent's JSON parser (valid, fenced, inverted-range, and malformed input).

## Architecture

```
app.py                      Streamlit UI — 6-step router, session state, styling
agents/
  segmentation.py           ABC classification by cumulative spend
  intelligence.py           Prenegotiation briefs (Gemini JSON mode) + follow-up Q&A
  message_gen.py            Outreach drafting, tone matrix, regeneration
  tracking.py               Pipeline stages, KPIs, staleness alerts
utils/
  api_handler.py            Gemini client, retry/backoff, typed errors
  validators.py             CSV + manual-entry validation
  exporters.py              Audit log + pipeline CSV export
data/
  demo.py                   Demo-mode loaders
  demo_suppliers.py         15 synthetic suppliers
  demo_outputs.py           Pre-generated briefs and drafts
  sample_template.csv       Downloadable CSV template
tests/                      pytest suite
other/                      Planning docs (not used at runtime)
```

Business logic is deliberately kept out of `app.py` — the agent and util modules are pure functions with no Streamlit imports where possible, which is what makes them testable.

## Tech stack

Python · Streamlit · pandas · Google Gemini (`google-genai`) · pytest

## Notes

Built as a portfolio project to explore LLM integration, procurement domain logic, and human-in-the-loop product design. It is not a production system: state lives in the Streamlit session and is lost on refresh, and there is no auth, persistence, or multi-user support.
