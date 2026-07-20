# app.py — NegotiateIQ main entry point
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import time

# Resolve bundled assets relative to this file, not the working directory,
# so the app runs the same locally and on Streamlit Cloud.
APP_DIR = Path(__file__).parent

from utils.api_handler import PROVIDERS, DEFAULT_PROVIDER, MODEL_REGISTRIES, get_default_model, estimate_token_cost
from utils.exporters import export_audit_log_csv, export_pipeline_csv
from utils.validators import validate_csv, validate_manual_entry
from agents.segmentation import run_segmentation, get_segmentation_summary
from agents.intelligence import run_intelligence_batch, run_intelligence_single, ask_intel_agent
from agents.message_gen import run_message_batch, regenerate_message
from agents.tracking import (
    initialize_pipeline, calculate_kpis, get_stale_suppliers,
    advance_stage, add_note, PIPELINE_STAGES,
)
from data.demo import (
    load_demo_suppliers, load_demo_intelligence, load_demo_messages,
    DEMO_SENDER_NAME,
)

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NegotiateIQ",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS — Slate Pro dark theme ──────────────────────────────────────
st.markdown("""
<style>
  /* Base */
  .stApp { background-color: #0D1117; color: #E6EDF3; }
  .main .block-container { padding-top: 1.5rem; max-width: 1100px; }

  /* Cards */
  .niq-card {
    background: #161B22; border: 1px solid #30363D;
    border-radius: 10px; padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
  }
  .niq-card-accent { border-left: 4px solid #2F81F7; }

  /* Tier badges */
  .badge-a { background:#3D1C1C; color:#FF7B72; padding:2px 10px;
    border-radius:12px; font-size:0.78rem; font-weight:700; }
  .badge-b { background:#1C2D3D; color:#58A6FF; padding:2px 10px;
    border-radius:12px; font-size:0.78rem; font-weight:700; }
  .badge-c { background:#1C3D2D; color:#3FB950; padding:2px 10px;
    border-radius:12px; font-size:0.78rem; font-weight:700; }

  /* Flag badges */
  .flag-ss { background:#3D2B1C; color:#FFA657; padding:1px 8px;
    border-radius:8px; font-size:0.72rem; }
  .flag-intl { background:#2B1C3D; color:#BC8CFF; padding:1px 8px;
    border-radius:8px; font-size:0.72rem; }
  .flag-stale { background:#3D3D1C; color:#E3B341; padding:1px 8px;
    border-radius:8px; font-size:0.72rem; }

  /* KPI strip */
  .kpi-box {
    background:#161B22; border:1px solid #30363D; border-radius:8px;
    padding:1rem; text-align:center;
  }
  .kpi-num { font-size:1.8rem; font-weight:700; color:#2F81F7; }
  .kpi-label { font-size:0.78rem; color:#8B949E; margin-top:2px; }

  /* Progress steps */
  .step-bar { display:flex; gap:0.5rem; margin-bottom:1.5rem; flex-wrap:wrap; }
  .step-pill {
    padding:4px 14px; border-radius:16px; font-size:0.78rem; font-weight:600;
    border: 1px solid #30363D; color:#8B949E; background:#161B22;
  }
  .step-pill.active { background:#2F81F7; color:#fff; border-color:#2F81F7; }
  .step-pill.done { background:#238636; color:#fff; border-color:#238636; }

  /* Message box */
  .msg-box {
    background:#0D1117; border:1px solid #30363D; border-radius:6px;
    padding:1rem; font-family:monospace; font-size:0.85rem;
    white-space:pre-wrap; color:#E6EDF3;
  }

  /* Pipeline stage funnel */
  .funnel { display:flex; align-items:center; gap:6px; flex-wrap:wrap;
    margin-bottom:1.2rem; }
  .funnel-pill {
    padding:4px 12px; border-radius:6px; font-size:0.78rem;
    color:#8B949E; background:transparent; border:1px solid transparent;
  }
  .funnel-pill.active {
    color:#58A6FF; background:#1C2D3D; border-color:#1F3A57; font-weight:600;
  }
  .funnel-sep { color:#30363D; font-size:0.8rem; }

  /* Sidebar */
  .css-1d391kg { background:#161B22 !important; }
  section[data-testid="stSidebar"] { background:#161B22; }
  section[data-testid="stSidebar"] .stButton button {
    width:100%; background:#21262D; border:1px solid #30363D;
    color:#E6EDF3; border-radius:6px;
  }

  /* Buttons */
  .stButton button { border-radius:6px !important; }
  .stButton button[kind="primary"] {
    background:#2F81F7 !important; border:none !important; }

  /* Supplier list buttons */
  div[data-testid="stVerticalBlock"] button.supplier-btn {
    background: transparent !important;
    border: none !important;
    text-align: left !important;
    padding: 0 !important;
  }

  /* Hide Streamlit branding */
  #MainMenu {visibility:hidden;}
  footer {visibility:hidden;}
  header {visibility:hidden;}
</style>
""", unsafe_allow_html=True)


# ── Session state init ──────────────────────────────────────────────────────
def init_session():
    defaults = {
        "model_name": get_default_model(DEFAULT_PROVIDER),
        "api_key": "",
        "provider": DEFAULT_PROVIDER,
        "demo_mode": False,
        "current_step": 1,
        "suppliers": [],
        "segmented": [],
        "intelligence": {},
        "selected_intel_supplier": None,
        "messages": {},
        "pipeline": [],
        "audit_log": [],
        "threshold_a": 70,
        "threshold_b": 90,
        "staleness_days": 7,
        "intel_qa": {},
        "msg_qa": {},
        "sender_name": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ── Audit log helper ────────────────────────────────────────────────────────
def log_action(action_type: str, supplier_name: str = "", detail: str = ""):
    st.session_state.audit_log.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action_type": action_type,
        "supplier_name": supplier_name,
        "detail": detail,
    })


# ── Formatting helpers ──────────────────────────────────────────────────────
def fmt_money_short(amount: float) -> str:
    """Compact currency for metric tiles: 31720 → $32K, 1250000 → $1.3M."""
    amount = float(amount or 0)
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if abs(amount) >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount:,.0f}"


# ── Intel brief section helper ──────────────────────────────────────────────
def intel_section(label: str, value: str, divider: bool = True, value_color: str = "#E6EDF3") -> str:
    hr = '<hr style="border:none;border-top:1px solid #21262D;margin-bottom:1.2rem;">' if divider else ""
    return f"""<div style="margin-bottom:1.2rem;">
  <div style="color:#8B949E;font-size:0.7rem;font-weight:600;text-transform:uppercase;
  letter-spacing:0.08em;margin-bottom:6px;">{label}</div>
  <div style="color:{value_color};font-size:0.85rem;line-height:1.7;">{value}</div>
</div>{hr}"""


# ── Demo mode helper ────────────────────────────────────────────────────────
def exit_demo():
    """Clear all demo data and return to a fresh session."""
    for key, value in {
        "demo_mode": False, "suppliers": [], "segmented": [],
        "intelligence": {}, "messages": {}, "pipeline": [],
        "audit_log": [], "intel_qa": {}, "msg_qa": {},
        "selected_intel_supplier": None, "sender_name": "", "current_step": 1,
    }.items():
        st.session_state[key] = value


# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ NegotiateIQ")
    st.markdown("---")

    if st.session_state.demo_mode:
        st.info("🎬 **Demo mode active**\n\nAll AI outputs are pre-generated — no API key or API calls needed.")
        if st.button("✕ Exit Demo Mode"):
            exit_demo()
            st.rerun()
    else:
        provider = st.selectbox("AI Provider", PROVIDERS, index=PROVIDERS.index(st.session_state.get("provider", DEFAULT_PROVIDER)))
        st.session_state.provider = provider

        api_key = st.text_input(f"{provider} API Key", type="password",
                                placeholder=f"Enter your {provider} API key",
                                value=st.session_state.get("api_key", ""))
        st.session_state.api_key = api_key

        if api_key:
            if provider == "Google Gemini" and (api_key.startswith("AIza") or api_key.startswith("AQ.")):
                st.success("✓ Gemini API key detected")
            elif provider == "Groq" and api_key.startswith("gsk_"):
                st.success("✓ Groq API key detected")
            elif provider == "OpenAI" and api_key.startswith("sk-"):
                st.success("✓ OpenAI API key detected")
            elif provider == "Anthropic" and api_key.startswith("sk-ant-"):
                st.success("✓ Anthropic API key detected")
            else:
                st.info("✓ API key set")

            models_dict = MODEL_REGISTRIES.get(provider, {})
            model_ids = list(models_dict.keys())
            model_names = list(models_dict.values())
            
            cur_model_id = st.session_state.get("model_name")
            cur_model_idx = model_ids.index(cur_model_id) if cur_model_id in model_ids else 0
            
            selected_model_name = st.selectbox("Model", model_names, index=cur_model_idx)
            st.session_state.model_name = model_ids[model_names.index(selected_model_name)]
        else:
            st.warning(f"⚠ {provider} API key required")
            st.session_state.model_name = get_default_model(provider)

    st.markdown("---")
    st.markdown("**Segmentation Thresholds**")
    threshold_a = st.slider("A-tier cutoff (%)", 50, 85, st.session_state.threshold_a, step=5)
    threshold_b = st.slider("B-tier cutoff (%)", threshold_a + 5, 95,
                            max(st.session_state.threshold_b, threshold_a + 5), step=5)
    st.session_state.threshold_a = threshold_a
    st.session_state.threshold_b = threshold_b
    st.caption(f"A: 0–{threshold_a}% · B: {threshold_a}–{threshold_b}% · C: {threshold_b}–100%")

    st.markdown("---")
    staleness = st.slider("Staleness alert (days)", 3, 30, st.session_state.staleness_days)
    st.session_state.staleness_days = staleness
    st.caption("Flags suppliers not negotiated within this period with a 🕐 Stale badge.")

    # Export options
    if st.session_state.audit_log:
        st.markdown("**Export**")
        st.download_button("📋 Audit Log (CSV)",
                           data=export_audit_log_csv(st.session_state.audit_log),
                           file_name="negotiateiq_audit.csv", mime="text/csv")
        if st.session_state.pipeline:
            st.download_button("📊 Pipeline (CSV)",
                               data=export_pipeline_csv(st.session_state.pipeline),
                               file_name="negotiateiq_pipeline.csv", mime="text/csv")

    # Token cost estimate
    if st.session_state.segmented:
        st.markdown("---")
        if st.session_state.demo_mode:
            st.caption("**Est. API cost:** $0.00 — demo mode makes no API calls")
        else:
            eligible = [s for s in st.session_state.segmented if s.get("tier") in ("B", "C")]
            est = estimate_token_cost(len(eligible), st.session_state.provider, st.session_state.model_name)
            st.caption(f"**Est. API cost:** {est['cost_str']}\n\n~{est['total_tokens']:,} tokens · {est['suppliers']} suppliers")


# ── Step progress bar ────────────────────────────────────────────────────────
STEPS = ["1 · Input", "2 · Segment", "3 · Intelligence", "4 · Messages", "5 · Review", "6 · Track"]

def render_step_bar(current: int):
    pills = ""
    for i, label in enumerate(STEPS, start=1):
        if i < current:
            pills += f'<span class="step-pill done">✓ {label}</span>'
        elif i == current:
            pills += f'<span class="step-pill active">{label}</span>'
        else:
            pills += f'<span class="step-pill">{label}</span>'
    st.markdown(f'<div class="step-bar">{pills}</div>', unsafe_allow_html=True)


# ── Navigation helpers ────────────────────────────────────────────────────────
def go_to(step: int):
    st.session_state.current_step = step


# ════════════════════════════════════════════════════════════════════════════
# STEP 1 — DATA INPUT
# ════════════════════════════════════════════════════════════════════════════
def render_step1():
    render_step_bar(1)
    st.markdown("## Step 1 · Supplier Data Input")
    st.markdown("Upload a CSV or enter suppliers manually. You need at least 3 suppliers to run segmentation.")

    # ── Demo mode entry point ─────────────────────────────────────────────────
    if not st.session_state.demo_mode:
        demo_l, demo_r = st.columns([4, 1], vertical_alignment="center")
        with demo_l:
            st.markdown("""
<div class="niq-card niq-card-accent" style="margin-bottom:0;">
  <div style="font-weight:700;font-size:0.95rem;">🎬 Just exploring?</div>
  <div style="color:#8B949E;font-size:0.85rem;margin-top:4px;">
    Load 15 sample suppliers with pre-generated AI briefs and outreach drafts —
    experience the full 6-step flow with no API key required.
  </div>
</div>""", unsafe_allow_html=True)
        with demo_r:
            if st.button("Try Demo →", type="primary", use_container_width=True):
                st.session_state.demo_mode = True
                st.session_state.suppliers = load_demo_suppliers()
                log_action("demo_started", detail=f"{len(st.session_state.suppliers)} sample suppliers loaded")
                go_to(2)
                st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📁 Upload CSV", "✏️ Manual Entry"])

    with tab1:
        template_csv = (APP_DIR / "data" / "sample_template.csv").read_bytes()
        st.download_button("📥 Download CSV Template", data=template_csv,
                           file_name="negotiateiq_template.csv", mime="text/csv")
        st.caption("Download this template first to ensure your data is formatted correctly.")
        uploaded = st.file_uploader("Upload supplier CSV", type=["csv"])
        if uploaded:
            df = pd.read_csv(uploaded)
            result = validate_csv(df)

            if result["warnings"]:
                for w in result["warnings"]:
                    st.warning(w)

            if not result["valid"]:
                st.error("**Validation errors — please fix before continuing:**")
                for err in result["errors"]:
                    st.markdown(f"- {err}")
            else:
                cleaned = result["cleaned_df"]
                st.success(f"✓ {len(cleaned)} suppliers validated successfully")
                st.dataframe(cleaned, use_container_width=True, hide_index=True)
                if st.button("Use this data →", type="primary"):
                    st.session_state.suppliers = cleaned.to_dict("records")
                    log_action("uploaded", detail=f"{len(cleaned)} suppliers from CSV")
                    go_to(2)
                    st.rerun()

    with tab2:
        st.markdown("Add one supplier at a time.")
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Supplier Name *")
                category = st.text_input("Category *")
                spend = st.number_input("Annual Spend (USD) *", min_value=0.0, step=1000.0)
                country = st.text_input("Country *", value="USA")
            with col2:
                contact_name = st.text_input("Contact Name *")
                contact_email = st.text_input("Contact Email *")
                sole_source = st.selectbox("Sole Source? *", ["N", "Y"])
                payment_terms = st.text_input("Payment Terms (optional)", placeholder="Net 30")

            col3, col4 = st.columns(2)
            with col3:
                last_neg = st.text_input("Last Negotiation Date (optional)", placeholder="YYYY-MM-DD")
            with col4:
                notes = st.text_area("Notes (optional)", height=68)

        if st.button("Add Supplier"):
            entry = {
                "supplier_name": name, "category": category,
                "annual_spend_usd": spend, "country": country,
                "contact_name": contact_name, "contact_email": contact_email,
                "sole_source": sole_source, "current_payment_terms": payment_terms,
                "last_negotiation_date": last_neg, "notes": notes,
            }
            val = validate_manual_entry(entry)
            if val["valid"]:
                st.session_state.suppliers.append(entry)
                log_action("manual_entry", supplier_name=name, detail=f"Added manually — ${spend:,.0f}")
                st.success(f"✓ {name} added ({len(st.session_state.suppliers)} total)")
            else:
                for e in val["errors"]:
                    st.error(e)

        if st.session_state.suppliers:
            st.markdown(f"**{len(st.session_state.suppliers)} suppliers in session:**")
            df_s = pd.DataFrame(st.session_state.suppliers)
            st.dataframe(df_s[["supplier_name", "category", "annual_spend_usd", "country"]],
                         use_container_width=True, hide_index=True)

            if len(st.session_state.suppliers) >= 3:
                if st.button("Continue to Segmentation →", type="primary"):
                    go_to(2)
                    st.rerun()
            else:
                st.warning(f"Add {3 - len(st.session_state.suppliers)} more supplier(s) to continue.")


# ════════════════════════════════════════════════════════════════════════════
# STEP 2 — SEGMENTATION
# ════════════════════════════════════════════════════════════════════════════
def render_step2():
    render_step_bar(2)
    st.markdown("## Step 2 · ABC Segmentation")

    if not st.session_state.suppliers:
        st.warning("No suppliers loaded. Go back to Step 1.")
        if st.button("← Back to Input"):
            go_to(1); st.rerun()
        return

    # Run segmentation
    try:
        segmented = run_segmentation(
            st.session_state.suppliers,
            st.session_state.threshold_a,
            st.session_state.threshold_b,
        )
        st.session_state.segmented = segmented
        log_action("segmented", detail=f"{len(segmented)} suppliers → A/B/C tiers")
    except ValueError as e:
        st.error(str(e))
        return

    summary = get_segmentation_summary(segmented)

    st.caption(f"A-tier threshold: {st.session_state.threshold_a}% · B-tier: {st.session_state.threshold_b}% · Adjust sliders in sidebar")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tier summary strip ────────────────────────────────────────────────────
    st.markdown("### Supplier Classification")
    tier_colors  = {"A": "#FF7B72", "B": "#58A6FF", "C": "#3FB950"}
    tier_labels  = {"A": "Human-led", "B": "AI-managed", "C": "AI-managed"}
    total_spend = segmented[0]["total_spend"] if segmented else 1
    sc1, sc2, sc3 = st.columns(3)
    for col, tier in zip([sc1, sc2, sc3], ["A", "B", "C"]):
        t_count = summary[tier]["count"]
        t_spend = summary[tier]["spend"]
        t_pct   = round((t_spend / total_spend) * 100, 1) if total_spend else 0
        with col:
            st.markdown(f"""
<div class="niq-card" style="border-left:4px solid {tier_colors[tier]};text-align:center;">
  <div style="font-size:0.72rem;color:{tier_colors[tier]};font-weight:700;letter-spacing:0.08em;text-transform:uppercase;">
    Tier {tier} · {tier_labels[tier]}
  </div>
  <div style="font-size:1.6rem;font-weight:700;color:#E6EDF3;margin:0.3rem 0;">{t_count}</div>
  <div style="font-size:0.82rem;color:#8B949E;">{t_count} suppliers · ${t_spend:,.0f} · {t_pct}% of spend</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Search + filter controls ──────────────────────────────────────────────
    fc1, fc2 = st.columns([3, 1])
    with fc1:
        search_query = st.text_input("🔍 Search suppliers", placeholder="Type supplier name...", label_visibility="collapsed")
    with fc2:
        tier_filter = st.selectbox("Tier", ["All", "A", "B", "C"], label_visibility="collapsed")

    # ── Build filtered dataframe ──────────────────────────────────────────────
    df_seg = pd.DataFrame(segmented)
    if tier_filter != "All":
        df_seg = df_seg[df_seg["tier"] == tier_filter]
    if search_query:
        df_seg = df_seg[df_seg["supplier_name"].str.contains(search_query, case=False, na=False)]

    def fmt_flags(row):
        flags = []
        if row.get("sole_source_flag"):
            flags.append("⚠ Sole Source")
        if row.get("international_flag"):
            flags.append("🌐 Intl")
        if row.get("relationship_staleness"):
            flags.append("🕐 Stale")
        return " · ".join(flags) if flags else "—"

    def fmt_flow(row):
        return "Human-led" if row["tier"] == "A" else "✓ AI"

    display_df = pd.DataFrame({
        "Supplier":  df_seg["supplier_name"],
        "Category":  df_seg["category"],
        "Country":   df_seg["country"],
        "Spend":     df_seg["annual_spend_usd"].apply(lambda x: f"${float(x):,.0f}"),
        "% Total":   df_seg["spend_pct"].apply(lambda x: f"{x}%"),
        "Tier":      df_seg["tier"],
        "Flags":     df_seg.apply(fmt_flags, axis=1),
        "Flow":      df_seg.apply(fmt_flow, axis=1),
    })

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Tier": st.column_config.TextColumn("Tier", width="small"),
            "Spend": st.column_config.TextColumn("Spend", width="medium"),
            "% Total": st.column_config.TextColumn("% Total", width="small"),
            "Flow": st.column_config.TextColumn("Flow", width="small"),
        },
    )
    st.caption(f"Showing {len(display_df)} of {len(segmented)} suppliers")

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1, 5])
    with col_a:
        if st.button("← Back"):
            go_to(1); st.rerun()
    with col_b:
        if st.button("Continue to Intelligence Agent →", type="primary"):
            go_to(3); st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# STEP 3 — INTELLIGENCE AGENT
# ════════════════════════════════════════════════════════════════════════════
def render_step3():
    render_step_bar(3)
    st.markdown("## Step 3 · Intelligence Agent")
    st.markdown("Generating prenegotiation fact bases for all B and C tier suppliers.")

    if not st.session_state.segmented:
        st.warning("Run segmentation first.")
        if st.button("← Back to Segmentation"):
            go_to(2); st.rerun()
        return

    eligible = [s for s in st.session_state.segmented if s.get("tier") in ("B", "C")]

    if not st.session_state.intelligence:
        if st.session_state.demo_mode:
            # Demo mode — load pre-generated briefs with simulated progress
            st.caption("🎬 Demo mode — briefs are pre-generated; no API calls are made.")
            if st.button("▶ Run Intelligence Agent", type="primary"):
                progress = st.progress(0)
                status = st.empty()
                for i, s in enumerate(eligible):
                    status.text(f"Analyzing {s.get('supplier_name', '')}... ({i+1}/{len(eligible)})")
                    progress.progress((i + 1) / len(eligible))
                    time.sleep(0.12)
                st.session_state.intelligence = load_demo_intelligence(st.session_state.segmented)
                log_action("intelligence_generated", detail=f"{len(st.session_state.intelligence)} demo briefs loaded")
                st.rerun()
        else:
            # Live mode — run agent
            if not st.session_state.api_key:
                st.error(f"⚠ {st.session_state.provider} API key required. Enter it in the sidebar — or load the demo from Step 1.")
                return

            if st.button("▶ Run Intelligence Agent", type="primary"):
                progress = st.progress(0)
                status = st.empty()
                retry_area = st.empty()

                output = run_intelligence_batch(
                    eligible, st.session_state.api_key, progress, status,
                    provider=st.session_state.provider, model_name=st.session_state.model_name,
                )
                st.session_state.intelligence = output["results"]
                log_action("intelligence_generated", detail=f"{len(output['results'])} briefs · {len(output['failed'])} failed")

                if output["failed"]:
                    st.warning(f"✅ {len(output['results'])} suppliers processed · ⚠ {len(output['failed'])} failed")
                    for f in output["failed"]:
                        st.markdown(f"- **{f['name']}**: {f['error']}")
                    # Retry individual failures
                    for f in output["failed"]:
                        if st.button(f"Retry {f['name']}"):
                            try:
                                result = run_intelligence_single(f["supplier"],
                                                                 st.session_state.api_key,
                                                                 provider=st.session_state.provider,
                                                                 model_name=st.session_state.model_name)
                                st.session_state.intelligence[f["name"]] = result
                                st.success(f"✓ {f['name']} retried successfully")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                else:
                    status.success(f"✓ All {len(output['results'])} briefs generated")

    # ── Two-panel intelligence view ───────────────────────────────────────────
    if st.session_state.intelligence:
        intel_names = list(st.session_state.intelligence.keys())

        # Init selected supplier
        if "selected_intel_supplier" not in st.session_state or \
           st.session_state.selected_intel_supplier not in intel_names:
            st.session_state.selected_intel_supplier = intel_names[0]

        # Legend
        st.markdown("""
<div style="display:flex;gap:1.2rem;margin-bottom:1rem;">
  <span style="font-size:0.78rem;color:#8B949E;">
    <span style="display:inline-block;width:10px;height:3px;background:#58A6FF;border-radius:2px;vertical-align:middle;margin-right:5px;"></span>Tier B
  </span>
  <span style="font-size:0.78rem;color:#8B949E;">
    <span style="display:inline-block;width:10px;height:3px;background:#3FB950;border-radius:2px;vertical-align:middle;margin-right:5px;"></span>Tier C
  </span>
</div>""", unsafe_allow_html=True)

        left_col, right_col = st.columns([1, 2], gap="medium")

        # ── Left: supplier list ───────────────────────────────────────────────
        with left_col:
            for name in intel_names:
                intel = st.session_state.intelligence[name]
                s = intel.get("supplier", {})
                tier = s.get("tier", "")
                is_selected = name == st.session_state.selected_intel_supplier
                tier_dot = "🔵" if tier == "B" else "🟢"
                if st.button(
                    f"{tier_dot}  {name}",
                    key=f"sel_{name}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.selected_intel_supplier = name
                    st.rerun()

        # ── Right: detail panel ───────────────────────────────────────────────
        with right_col:
            name  = st.session_state.selected_intel_supplier
            intel = st.session_state.intelligence[name]
            s     = intel.get("supplier", {})
            tier  = s.get("tier", "")
            tier_color = {"A": "#FF7B72", "B": "#58A6FF", "C": "#3FB950"}.get(tier, "#8B949E")

            st.markdown(f"""<div class="niq-card">
<div style="margin-bottom:1.2rem;">
  <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.25rem;">
    <span style="font-size:1.15rem;font-weight:700;color:#E6EDF3;">{name}</span>
    <span style="background:#1C2D3D;color:{tier_color};padding:1px 10px;
    border-radius:10px;font-size:0.75rem;font-weight:600;">Tier {tier}</span>
  </div>
  <div style="color:#8B949E;font-size:0.8rem;display:flex;gap:0.8rem;flex-wrap:wrap;align-items:center;">
    <span>{s.get('category','')} · {s.get('country','')} · ${float(s.get('annual_spend_usd',0)):,.0f}</span>
    {"<span style='color:#E3B341;font-size:0.75rem;'>🕐 Stale</span>" if intel.get('relationship_staleness') else ""}
    {"<span style='color:#BC8CFF;font-size:0.75rem;'>🌐 Intl</span>" if s.get('international_flag') else ""}
    {"<span style='color:#FFA657;font-size:0.75rem;'>⚠ Sole Source</span>" if s.get('sole_source_flag') else ""}
  </div>
</div>
<hr style="border:none;border-top:1px solid #21262D;margin-bottom:1.2rem;">
{intel_section("Summary", intel.get("spend_summary", "—"), value_color="#C9D1D9")}
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1.2rem;">
  <div style="flex:1;padding-right:2rem;">
    <div style="color:#8B949E;font-size:0.7rem;font-weight:600;text-transform:uppercase;
    letter-spacing:0.08em;margin-bottom:6px;">Lever</div>
    <div style="color:#E6EDF3;font-size:0.85rem;line-height:1.6;">{intel.get('lever','—')}</div>
  </div>
  <div style="text-align:right;flex-shrink:0;">
    <div style="color:#8B949E;font-size:0.7rem;font-weight:600;text-transform:uppercase;
    letter-spacing:0.08em;margin-bottom:6px;">Savings Target</div>
    <div style="color:#3FB950;font-weight:700;font-size:1.3rem;line-height:1;">
      {intel.get('savings_target_low','?')}–{intel.get('savings_target_high','?')}%
    </div>
  </div>
</div>
<hr style="border:none;border-top:1px solid #21262D;margin-bottom:1.2rem;">
{intel_section("Risk", intel.get("risk_summary", "—"))}
{intel_section("Recommended Tone", intel.get("tone_recommendation", "—"), divider=False)}
</div>""", unsafe_allow_html=True)

            # ── Ask the agent ─────────────────────────────────────────────────
            st.markdown("""<div style="margin-top:1rem;border-top:1px solid #21262D;padding-top:1rem;">
  <div style="color:#8B949E;font-size:0.72rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.6rem;">
    Ask about this brief
  </div>
</div>""", unsafe_allow_html=True)

            qa_history = st.session_state.intel_qa.get(name, [])
            for qa in qa_history:
                st.markdown(f"""
<div style="margin-bottom:0.8rem;">
  <div style="background:#1C2D3D;border-radius:6px;padding:0.5rem 0.8rem;font-size:0.83rem;color:#E6EDF3;margin-bottom:4px;">{qa['question']}</div>
  <div style="background:#161B22;border:1px solid #30363D;border-radius:6px;padding:0.6rem 0.8rem;font-size:0.83rem;color:#C9D1D9;line-height:1.6;">{qa['answer']}</div>
</div>""", unsafe_allow_html=True)

            if st.session_state.demo_mode:
                st.caption("💬 Q&A about briefs requires a live API key — disabled in demo mode.")
            else:
                ask_col, btn_col = st.columns([5, 1])
                with ask_col:
                    question = st.text_input(
                        "Ask", key=f"ask_intel_{name}",
                        placeholder="e.g. Why price reduction over payment terms?",
                        label_visibility="collapsed",
                    )
                with btn_col:
                    ask_clicked = st.button("Ask →", key=f"ask_intel_btn_{name}", use_container_width=True)

                if ask_clicked:
                    if question.strip():
                        with st.spinner("Thinking..."):
                            answer = ask_intel_agent(
                                s, intel, question,
                                st.session_state.api_key,
                                provider=st.session_state.provider,
                                model_name=st.session_state.model_name,
                            )
                        if name not in st.session_state.intel_qa:
                            st.session_state.intel_qa[name] = []
                        st.session_state.intel_qa[name].append({"question": question, "answer": answer})
                        st.rerun()
                    else:
                        st.warning("Enter a question first.")

        st.markdown("<br>", unsafe_allow_html=True)
        col_a, col_b = st.columns([1, 5])
        with col_a:
            if st.button("← Back"):
                go_to(2); st.rerun()
        with col_b:
            if st.button("Continue to Message Generation →", type="primary"):
                go_to(4); st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# STEP 4 — MESSAGE GENERATION
# ════════════════════════════════════════════════════════════════════════════
def render_step4():
    render_step_bar(4)
    st.markdown("## Step 4 · Message Generation")

    if not st.session_state.intelligence:
        st.warning("Run Intelligence Agent first.")
        if st.button("← Back"):
            go_to(3); st.rerun()
        return

    eligible = [s for s in st.session_state.segmented if s.get("tier") in ("B", "C")]

    if not st.session_state.messages:
        if st.session_state.demo_mode:
            # Demo mode — load pre-written drafts with simulated progress
            st.caption("🎬 Demo mode — outreach drafts are pre-written; no API calls are made.")
            sender_name = st.text_input("Your Name (for message sign-offs)",
                                        value=st.session_state.get("sender_name", "") or DEMO_SENDER_NAME)

            if st.button("▶ Generate All Messages", type="primary"):
                st.session_state.sender_name = sender_name.strip() or DEMO_SENDER_NAME
                progress = st.progress(0)
                status = st.empty()
                for i, s in enumerate(eligible):
                    status.text(f"Drafting message for {s.get('supplier_name', '')}... ({i+1}/{len(eligible)})")
                    progress.progress((i + 1) / len(eligible))
                    time.sleep(0.12)
                st.session_state.messages = load_demo_messages(
                    st.session_state.segmented, st.session_state.sender_name)
                log_action("messages_generated", detail=f"{len(st.session_state.messages)} demo drafts loaded")
                st.rerun()
        else:
            if not st.session_state.api_key:
                st.error(f"⚠ {st.session_state.provider} API key required.")
                return

            sender_name = st.text_input("Your Name (for message sign-offs) *", value=st.session_state.get('sender_name', ''))

            if st.button("▶ Generate All Messages", type="primary"):
                if not sender_name.strip():
                    st.warning("Please enter your name first. For example, 'Emily Chen'.")
                    return
                st.session_state.sender_name = sender_name.strip()

                progress = st.progress(0)
                status = st.empty()
                output = run_message_batch(
                    eligible, st.session_state.intelligence,
                    st.session_state.api_key,
                    progress, status,
                    provider=st.session_state.provider,
                    model_name=st.session_state.model_name,
                    sender_name=st.session_state.sender_name,
                )
                st.session_state.messages = output["results"]
                log_action("messages_generated", detail=f"{len(output['results'])} messages · {len(output['failed'])} failed")
                st.rerun()

    # Display messages with approve/reject/regenerate
    if st.session_state.messages:
        approved_count = sum(1 for m in st.session_state.messages.values() if m.get("approved"))
        total_msgs = len(st.session_state.messages)

        st.markdown(f"**{approved_count}/{total_msgs} messages approved**")

        # Bulk approve
        col_bulk, _ = st.columns([2, 5])
        with col_bulk:
            if approved_count < total_msgs:
                if st.button("✓ Bulk Approve All", help="Approves all messages including unreviewed ones"):
                    unreviewed = [n for n, m in st.session_state.messages.items() if not m.get("approved")]
                    if unreviewed:
                        st.warning(f"⚠ {len(unreviewed)} messages have not been individually reviewed. Approving all anyway.")
                    for name in st.session_state.messages:
                        st.session_state.messages[name]["approved"] = True
                        log_action("approved", supplier_name=name, detail="Bulk approved")
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        for name, msg in st.session_state.messages.items():
            s = msg.get("supplier", {})
            approved = msg.get("approved", False)
            status_color = "#238636" if approved else "#30363D"
            status_label = "✓ Approved" if approved else "Pending review"

            with st.expander(f"{'✓ ' if approved else ''}{name} — {msg.get('subject','')[:60]}", expanded=not approved):
                # ── Action row ────────────────────────────────────────────────
                st.markdown(f"**Subject:** {msg.get('subject','')}")
                wc = msg.get("word_count", 0)
                wc_color = "#FF7B72" if wc > 200 else "#3FB950"
                act_l, act_r = st.columns([5, 1])
                with act_l:
                    st.markdown(f"<span style='color:{wc_color};font-size:0.78rem;'>{wc}/200 words</span>",
                                unsafe_allow_html=True)
                with act_r:
                    if not approved:
                        if st.button("✓ Approve", key=f"approve_{name}", type="primary", use_container_width=True):
                            st.session_state.messages[name]["approved"] = True
                            log_action("approved", supplier_name=name)
                            st.rerun()
                    else:
                        if st.button("✗ Revoke", key=f"revoke_{name}", use_container_width=True):
                            st.session_state.messages[name]["approved"] = False
                            log_action("rejected", supplier_name=name, detail="Approval revoked")
                            st.rerun()

                # ── Message body (readable preview) ───────────────────────────
                body_raw = msg.get('body', '')
                body_escaped = body_raw.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                body_html = ''.join(
                    f'<p style="margin:0 0 0.5rem 0;">{p.replace(chr(10), "<br>")}</p>'
                    for p in body_escaped.split('\n\n')
                )
                st.markdown(
                    f"<div style='background:#0D1117;border:1px solid #30363D;border-radius:6px;"
                    f"padding:1rem;font-size:0.85rem;color:#E6EDF3;line-height:1.6;"
                    f"margin:0.5rem 0 1rem;'>{body_html}</div>",
                    unsafe_allow_html=True,
                )

                # ── Tabbed actions ────────────────────────────────────────────
                tab_regen, tab_ask = st.tabs(["↺ Regenerate", "💬 Ask"])

                with tab_regen:
                    if st.session_state.demo_mode:
                        st.caption("↺ Regeneration requires a live API key — disabled in demo mode.")
                    else:
                        reason = st.text_input(
                            "Reason", key=f"regen_{name}",
                            placeholder="e.g. Too formal, soften the tone",
                            label_visibility="collapsed",
                        )
                        if st.button("↺ Regenerate", key=f"regen_btn_{name}"):
                            if reason:
                                intel = st.session_state.intelligence.get(name, {})
                                new_msg = regenerate_message(s, intel, reason,
                                                             st.session_state.api_key,
                                                             provider=st.session_state.provider,
                                                             model_name=st.session_state.model_name,
                                                             sender_name=st.session_state.get('sender_name', ''))
                                st.session_state.messages[name].update(new_msg)
                                log_action("regenerated", supplier_name=name, detail=f"Reason: {reason}")
                                st.rerun()
                            else:
                                st.warning("Enter a reason for regeneration.")

                with tab_ask:
                    if st.session_state.demo_mode:
                        st.caption("💬 Q&A about drafts requires a live API key — disabled in demo mode.")
                    else:
                        msg_qa_history = st.session_state.msg_qa.get(name, [])
                        for qa in msg_qa_history:
                            st.markdown(f"""
<div style="margin-bottom:0.8rem;">
  <div style="background:#1C2D3D;border-radius:6px;padding:0.5rem 0.8rem;font-size:0.83rem;color:#E6EDF3;margin-bottom:4px;">{qa['question']}</div>
  <div style="background:#161B22;border:1px solid #30363D;border-radius:6px;padding:0.6rem 0.8rem;font-size:0.83rem;color:#C9D1D9;line-height:1.6;">{qa['answer']}</div>
</div>""", unsafe_allow_html=True)

                        mq_col, mbtn_col = st.columns([5, 1])
                        with mq_col:
                            msg_question = st.text_input(
                                "Ask", key=f"ask_msg_{name}",
                                placeholder="e.g. Why did you open with the spend figure?",
                                label_visibility="collapsed",
                            )
                        with mbtn_col:
                            msg_ask_clicked = st.button("Ask →", key=f"ask_msg_btn_{name}", use_container_width=True)

                        if msg_ask_clicked:
                            if msg_question.strip():
                                intel = st.session_state.intelligence.get(name, {})
                                with st.spinner("Thinking..."):
                                    answer = ask_intel_agent(
                                        s, intel, msg_question,
                                        st.session_state.api_key,
                                        provider=st.session_state.provider,
                                        model_name=st.session_state.model_name,
                                        message=msg,
                                    )
                                if name not in st.session_state.msg_qa:
                                    st.session_state.msg_qa[name] = []
                                st.session_state.msg_qa[name].append({"question": msg_question, "answer": answer})
                                st.rerun()
                            else:
                                st.warning("Enter a question first.")

        st.markdown("<br>", unsafe_allow_html=True)
        col_a, col_b = st.columns([1, 5])
        with col_a:
            if st.button("← Back"):
                go_to(3); st.rerun()
        with col_b:
            if approved_count > 0:
                if st.button("Continue to Human Review Gate →", type="primary"):
                    go_to(5); st.rerun()
            else:
                st.warning("Approve at least one message to continue.")


# ════════════════════════════════════════════════════════════════════════════
# STEP 5 — HUMAN REVIEW GATE
# ════════════════════════════════════════════════════════════════════════════
def render_step5():
    render_step_bar(5)
    st.markdown("## Step 5 · Human Review Gate")

    approved_msgs = {n: m for n, m in st.session_state.messages.items() if m.get("approved")}
    if not approved_msgs:
        st.warning("No approved messages to review.")
        if st.button("← Back to Messages"):
            go_to(4); st.rerun()
        return

    # Campaign summary
    st.markdown("### Campaign Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="kpi-box">
            <div class="kpi-num">{len(approved_msgs)}</div>
            <div class="kpi-label">Messages ready to send</div></div>""", unsafe_allow_html=True)
    with col2:
        total_spend = sum(float(m.get("supplier", {}).get("annual_spend_usd", 0)) for m in approved_msgs.values())
        st.markdown(f"""<div class="kpi-box">
            <div class="kpi-num">${total_spend/1000:.0f}K</div>
            <div class="kpi-label">Total spend addressed</div></div>""", unsafe_allow_html=True)
    with col3:
        intel_data = st.session_state.intelligence
        total_savings_low = sum(
            float(m.get("supplier", {}).get("annual_spend_usd", 0)) *
            intel_data.get(n, {}).get("savings_target_low", 3) / 100
            for n, m in approved_msgs.items()
        )
        total_savings_high = sum(
            float(m.get("supplier", {}).get("annual_spend_usd", 0)) *
            intel_data.get(n, {}).get("savings_target_high", 8) / 100
            for n, m in approved_msgs.items()
        )
        st.markdown(f"""<div class="kpi-box">
            <div class="kpi-num">${total_savings_low/1000:.0f}K–${total_savings_high/1000:.0f}K</div>
            <div class="kpi-label">Estimated savings pipeline</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Pre-send checklist
    st.markdown("### Pre-Send Checklist")
    msgs_list = list(approved_msgs.values())
    emails = [m.get("supplier", {}).get("contact_email", "") for m in msgs_list]
    duplicate_emails = len(emails) != len(set(emails))
    all_under_200 = all(m.get("word_count", 0) <= 200 for m in msgs_list)
    sole_source_msgs = [n for n, m in approved_msgs.items() if m.get("supplier", {}).get("sole_source_flag")]
    intl_msgs = [n for n, m in approved_msgs.items() if m.get("supplier", {}).get("international_flag")]
    missing_contacts = [n for n, m in approved_msgs.items()
                        if not m.get("supplier", {}).get("contact_name", "").strip()]

    checks = [
        (all_under_200, "All messages under 200 words"),
        (not duplicate_emails, "No duplicate contact emails"),
        (True, f"Sole source suppliers using collaborative tone: {', '.join(sole_source_msgs) if sole_source_msgs else 'None'}"),
        (True, f"International messages using formal tone: {', '.join(intl_msgs) if intl_msgs else 'None'}"),
        (not missing_contacts, f"Contact names present: {'Missing for ' + ', '.join(missing_contacts) if missing_contacts else 'All present'}"),
    ]

    for ok, label in checks:
        icon = "✅" if ok else "⚠️"
        st.markdown(f"{icon} {label}")

    st.markdown("---")

    # Per-message send panel
    st.markdown("### Send Messages")
    for name, msg in approved_msgs.items():
        s = msg.get("supplier", {})
        sent = msg.get("sent", False)

        with st.expander(f"{'✉ Sent — ' if sent else ''}{name} → {s.get('contact_email', '')}"):
            if sent:
                st.success("✓ Marked as sent")
            else:
                st.markdown(f"""
<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:1rem;font-size:0.85rem;">
<strong>Next step: Send this email manually</strong><br><br>
1. Copy the subject line below<br>
2. Copy the message body below<br>
3. Open your email client (Outlook / Gmail)<br>
4. Paste into a new email to: <code>{s.get('contact_email','')}</code><br>
5. Review once more before hitting send<br>
6. Come back here and mark as "Sent" — tracking moves it to In progress<br><br>
<em>⚠ Do not forward or share the generated message outside your email client without review.</em>
</div>""", unsafe_allow_html=True)

            subject = msg.get("subject", "")
            body = msg.get("body", "")

            st.markdown(f"**Subject:** `{subject}`")
            st.code(subject, language=None)
            st.markdown("**Body:**")
            st.code(body, language=None)

            if not sent:
                if st.button(f"✓ Mark as Sent", key=f"sent_{name}", type="primary"):
                    st.session_state.messages[name]["sent"] = True
                    st.session_state.messages[name]["sent_date"] = datetime.now().strftime("%Y-%m-%d")
                    log_action("sent", supplier_name=name, detail="Manually marked as sent")
                    st.success("✓ Marked as sent — will appear in tracking")
                    st.rerun()

    st.markdown("---")

    # Audit log preview
    with st.expander("📋 Session Audit Log"):
        if st.session_state.audit_log:
            df_log = pd.DataFrame(st.session_state.audit_log)
            st.dataframe(df_log, use_container_width=True, hide_index=True)
        else:
            st.caption("No actions logged yet.")

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1, 5])
    with col_a:
        if st.button("← Back"):
            go_to(4); st.rerun()
    with col_b:
        if st.button("Go to Tracking Dashboard →", type="primary"):
            # Build/update pipeline
            st.session_state.pipeline = initialize_pipeline(
                st.session_state.segmented,
                st.session_state.messages,
                st.session_state.intelligence,
            )
            go_to(6); st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# STEP 6 — TRACKING
# ════════════════════════════════════════════════════════════════════════════
def render_step6():
    render_step_bar(6)
    st.markdown("## Step 6 · Tracking Dashboard")

    if not st.session_state.pipeline:
        # Try to build pipeline from existing data
        if st.session_state.messages and st.session_state.segmented:
            st.session_state.pipeline = initialize_pipeline(
                st.session_state.segmented,
                st.session_state.messages,
                st.session_state.intelligence,
            )
        else:
            st.warning("No pipeline data. Complete steps 1–5 first.")
            if st.button("← Back"):
                go_to(5); st.rerun()
            return

    pipeline = st.session_state.pipeline
    kpis = calculate_kpis(pipeline)
    sc = kpis["stage_counts"]

    # ── Metric tiles ──────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="kpi-box">
            <div class="kpi-num">{kpis['total']}</div>
            <div class="kpi-label">In pipeline</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="kpi-box">
            <div class="kpi-num" style="font-size:1.15rem;">{fmt_money_short(kpis['savings_low'])}–{fmt_money_short(kpis['savings_high'])}</div>
            <div class="kpi-label">Est. savings</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="kpi-box">
            <div class="kpi-num">{sc['In progress']} · {sc['Closed']}</div>
            <div class="kpi-label">In progress · closed</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Stage funnel ──────────────────────────────────────────────────────────
    pills = []
    for stage in PIPELINE_STAGES:
        count = sc.get(stage, 0)
        cls = "funnel-pill active" if count else "funnel-pill"
        pills.append(f'<span class="{cls}">{stage} {count}</span>')
    funnel_html = '<span class="funnel-sep">›</span>'.join(pills)
    st.markdown(f'<div class="funnel">{funnel_html}</div>', unsafe_allow_html=True)

    # ── Follow-up alerts ──────────────────────────────────────────────────────
    stale = get_stale_suppliers(pipeline, st.session_state.staleness_days)
    for s in stale:
        col_info, col_btn = st.columns([5, 1], vertical_alignment="center")
        with col_info:
            st.warning(f"**{s['supplier_name']}** — open for {s['days_elapsed']} days. Worth a follow-up?")
        with col_btn:
            if st.button("Close", key=f"stale_close_{s['supplier_name']}", use_container_width=True):
                st.session_state.pipeline = advance_stage(pipeline, s["supplier_name"], "Closed")
                log_action("stage_change", supplier_name=s["supplier_name"], detail="In progress → Closed (from alert)")
                st.rerun()

    # ── Pipeline table (select a row to see detail) ───────────────────────────
    table_df = pd.DataFrame([{
        "Supplier": e["supplier_name"],
        "Tier": e["tier"],
        "Spend": f"${e['annual_spend_usd']:,.0f}",
        "Stage": e["stage"],
        "Est. savings": f"${e.get('savings_low', 0):,.0f} – ${e.get('savings_high', 0):,.0f}",
    } for e in pipeline])

    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Tier": st.column_config.TextColumn("Tier", width="small"),
            "Stage": st.column_config.TextColumn("Stage", width="small"),
        },
    )

    # ── Detail for one supplier ───────────────────────────────────────────────
    sel_l, sel_r = st.columns([2, 3], vertical_alignment="center")
    with sel_l:
        selected = st.selectbox(
            "Manage supplier",
            [e["supplier_name"] for e in pipeline],
            label_visibility="collapsed",
        )

    entry = next((e for e in pipeline if e["supplier_name"] == selected), None)

    if entry is None:
        st.caption("Select a supplier to view its detail and advance its stage.")
    else:

        st.markdown(f"""<div class="niq-card niq-card-accent" style="margin-bottom:0.8rem;">
  <div style="font-weight:700;font-size:0.95rem;">{selected}</div>
  <div style="color:#8B949E;font-size:0.82rem;margin-top:4px;">
    {entry['stage']} · {entry.get('lever','—')} ·
    Est. ${entry.get('savings_low',0):,.0f}–${entry.get('savings_high',0):,.0f}
  </div>
</div>""", unsafe_allow_html=True)

        # Advance stage — primary next step, remaining stages as compact secondaries
        current_idx = PIPELINE_STAGES.index(entry["stage"]) if entry["stage"] in PIPELINE_STAGES else 0
        next_stages = PIPELINE_STAGES[current_idx + 1:]

        if next_stages:
            adv_cols = st.columns(len(next_stages))
            for i, (ns, col) in enumerate(zip(next_stages, adv_cols)):
                with col:
                    label = f"Advance to {ns} →" if i == 0 else ns
                    if st.button(label, key=f"advance_{selected}_{ns}",
                                 type="primary" if i == 0 else "secondary",
                                 use_container_width=True):
                        st.session_state.pipeline = advance_stage(pipeline, selected, ns)
                        log_action("stage_change", supplier_name=selected, detail=f"{entry['stage']} → {ns}")
                        st.rerun()
        else:
            st.caption("This supplier has reached the final stage.")

        det_l, det_r = st.columns(2)
        with det_l:
            if entry.get("message_body"):
                with st.expander("✉ View message"):
                    st.markdown(f"**Subject:** {entry.get('message_subject','')}")
                    st.code(entry.get("message_body", ""), language=None)
            with st.expander("🕐 Timeline"):
                for event in entry.get("timeline", []):
                    st.markdown(f"- `{event['timestamp']}` — {event['event']}")
        with det_r:
            with st.expander("📝 Notes", expanded=bool(entry.get("pipeline_notes"))):
                for note in entry.get("pipeline_notes", []):
                    st.markdown(f"- {note}")
                new_note = st.text_input("Add note", key=f"note_{selected}",
                                         label_visibility="collapsed",
                                         placeholder="Add a note...")
                if st.button("Add note", key=f"add_note_{selected}"):
                    if new_note:
                        st.session_state.pipeline = add_note(pipeline, selected, new_note)
                        log_action("note_added", supplier_name=selected, detail=new_note[:60])
                        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Back to Review Gate"):
        go_to(5); st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# ROUTER
# ════════════════════════════════════════════════════════════════════════════
step = st.session_state.current_step

if step == 1:
    render_step1()
elif step == 2:
    render_step2()
elif step == 3:
    render_step3()
elif step == 4:
    render_step4()
elif step == 5:
    render_step5()
elif step == 6:
    render_step6()
