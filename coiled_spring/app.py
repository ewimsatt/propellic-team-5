"""Coiled Spring Opportunity Forecasting Tool — Streamlit entry point."""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import date, timedelta

# ── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Coiled Spring™ — Opportunity Forecaster",
    page_icon="🌀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inline CSS overrides ─────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');

    /* Global font */
    html, body, [class*="css"] { font-family: 'Montserrat', sans-serif; }

    /* Main background — dark midnight */
    .stApp { background-color: #0a1118; }

    /* Sidebar — midnight brand color */
    [data-testid="stSidebar"] {
        background-color: #152534;
        border-right: 1px solid #1e3348;
    }
    [data-testid="stSidebar"] .stMarkdown { color: #94a3b8; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background-color: #0a1118; }
    .stTabs [data-baseweb="tab"] {
        color: #64748b; background-color: #152534;
        border-radius: 6px 6px 0 0; padding: 8px 20px;
        border: 1px solid #1e3348; border-bottom: none;
        font-family: 'Montserrat', sans-serif; font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #f1f5f9 !important; background-color: #1e3348 !important;
        border-color: #E21A6B !important; border-top: 2px solid #E21A6B !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: #152534 !important;
        border: 1px solid #1e3348 !important;
    }

    /* Buttons — Propellic pink */
    .stButton > button {
        background-color: #E21A6B !important;
        color: white !important;
        border: none !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        border-radius: 6px !important;
        letter-spacing: .04em;
    }
    .stButton > button:hover { background-color: #c01559 !important; }

    /* Download button */
    .stDownloadButton > button {
        background-color: #152534 !important;
        color: #E21A6B !important;
        border: 1px solid #E21A6B !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0a1118; }
    ::-webkit-scrollbar-thumb { background: #E21A6B; border-radius: 3px; }

    /* Divider */
    hr { border-color: #1e3348 !important; }

    /* Headings */
    h1, h2, h3 { font-family: 'Montserrat', sans-serif !important; font-weight: 700 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Imports (after page config) ──────────────────────────────────────────────
from config import USE_MOCK_DATA, USE_BIGQUERY, CONFIDENCE_COLORS

if USE_BIGQUERY:
    @st.cache_data(ttl=3600, show_spinner=False)
    def _get_data_date_range():
        from data.bigquery import get_data_date_range
        return get_data_date_range()
    _data_min_date, _data_max_date = _get_data_date_range()
else:
    _data_max_date = date.today()
    _data_min_date = _data_max_date - timedelta(days=365)
from mock_data import MockDataGenerator
from data.google_ads import get_campaigns, get_campaign_timeseries
from data.weather import get_weather_signal
from data.news import get_news_signal
from data.economic import get_economic_signal
from data.trends import get_trends_signal
from analysis.detection import CoiledSpringDetector
from analysis.correlation import compute_correlations
from analysis.forecast import project_recovery_uplift
from ui.components import render_kpi_bar, render_opportunity_card, render_demo_banner
from ui.charts import (
    build_divergence_chart, build_signal_overlay,
    build_correlation_heatmap, build_historical_tracker,
)
from ui.executive_summary import generate_executive_summary
from export.pdf_report import generate_pdf

_mock = MockDataGenerator()
detector = CoiledSpringDetector()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    import os
    _logo = "coiled_spring/assets/propellic-logo.png"
    if os.path.exists(_logo):
        st.image(_logo, use_container_width=True)
    else:
        st.markdown(
            '<div style="padding:16px 0 4px; text-align:center; font-family:Montserrat,sans-serif;">'
            '<span style="font-size:20px; font-weight:700; color:#f1f5f9;">Propellic</span>'
            "</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        """
        <div style="text-align:center; font-family:'Montserrat',sans-serif; padding-bottom:12px;">
            <div style="font-size:11px; color:#E21A6B; text-transform:uppercase;
                        letter-spacing:.12em; font-weight:600;">
                Coiled Spring™ Forecaster
            </div>
        </div>
        <hr style="margin: 4px 0 16px; border-color:#1e3348;">
        """,
        unsafe_allow_html=True,
    )

    # Campaign selector
    st.markdown("**Campaigns**")
    all_campaigns = get_campaigns()
    campaign_options = {c["name"]: c["id"] for c in all_campaigns}
    selected_names = st.multiselect(
        "Select campaigns",
        options=list(campaign_options.keys()),
        default=list(campaign_options.keys()),
        label_visibility="collapsed",
    )
    selected_ids = [campaign_options[n] for n in selected_names]

    st.markdown("---")

    # Date range
    st.markdown("**Date Range**")
    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input(
            "From",
            value=_data_max_date - timedelta(days=89),
            min_value=_data_min_date,
            max_value=_data_max_date,
            label_visibility="visible",
        )
    with col_e:
        end_date = st.date_input(
            "To",
            value=_data_max_date,
            min_value=_data_min_date,
            max_value=_data_max_date,
            label_visibility="visible",
        )

    st.markdown("---")

    # Signal toggles
    st.markdown("**Signal Toggles**")
    use_weather  = st.checkbox("🌧 Weather",  value=True)
    use_news     = st.checkbox("📰 News / Political", value=True)
    use_seasonal = st.checkbox("📅 Seasonal", value=True)
    use_economic = st.checkbox("📊 Economic", value=True)

    active_signal_cols: list[str] = []
    if use_weather:  active_signal_cols += ["weather_composite"]
    if use_news:     active_signal_cols += ["news_score"]
    if use_seasonal: active_signal_cols += ["seasonal_index"]
    if use_economic: active_signal_cols += ["economic_pressure"]

    st.markdown("---")

    # Confidence filter
    st.markdown("**Minimum Confidence**")
    conf_filter = st.radio(
        "Confidence filter",
        options=["Low", "Medium", "High"],
        index=0,
        label_visibility="collapsed",
        horizontal=True,
    )
    conf_rank = {"Low": 1, "Medium": 2, "High": 3}
    min_conf  = conf_rank[conf_filter]

    st.markdown("---")
    st.markdown(
        '<div style="font-size:10px; color:#334155; text-align:center;">'
        'Data refreshes every 5 min</div>',
        unsafe_allow_html=True,
    )


# ── Data loading ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_campaign_data(campaign_id: str, _start: date, _end: date) -> pd.DataFrame:
    return get_campaign_timeseries(campaign_id, _start, _end)


@st.cache_data(ttl=300, show_spinner=False)
def load_signals(campaign_id: str, _start: date, _end: date) -> pd.DataFrame:
    if USE_MOCK_DATA:
        return _mock.get_all_signals(campaign_id)
    weather  = get_weather_signal(_start, _end)
    news     = get_news_signal(_start, _end)
    economic = get_economic_signal(_start, _end)
    trends   = get_trends_signal(campaign_id, _start, _end)
    seasonal = _mock.get_seasonal_signal(campaign_id)   # seasonal is always computed locally
    return pd.concat([weather, news, economic, trends, seasonal], axis=1)


@st.cache_data(ttl=300, show_spinner=False)
def load_historical_outcomes() -> list[dict]:
    return _mock.get_historical_outcomes()


# ── Detect springs ────────────────────────────────────────────────────────────

def run_detection(
    campaign_ids: list[str],
    min_conf_rank: int,
) -> tuple[list, dict]:
    all_campaigns_map = {c["id"]: c["name"] for c in all_campaigns}
    springs = []

    with st.spinner("Analysing campaigns…"):
        for cid in campaign_ids:
            name = all_campaigns_map.get(cid, cid)
            df   = load_campaign_data(cid, start_date, end_date)
            sig  = load_signals(cid, start_date, end_date)
            sp   = detector.detect(cid, name, df, sig)
            if sp is None:
                continue
            rank = conf_rank.get(sp.confidence.capitalize(), 1)
            if rank >= min_conf_rank:
                springs.append(sp)

    # KPIs
    if springs:
        cvr_deltas = [
            (sp.cvr_current - sp.cvr_baseline) / sp.cvr_baseline * 100 for sp in springs
        ]
        avg_delta    = sum(cvr_deltas) / len(cvr_deltas)
        total_risk   = sum(sp.estimated_spend_at_risk for sp in springs)
        total_uplift = sum(sp.projected_recovery_uplift for sp in springs)
    else:
        avg_delta    = 0.0
        total_risk   = 0.0
        total_uplift = 0.0

    kpis = {
        "spring_count":           len(springs),
        "avg_cvr_delta_pct":      round(avg_delta, 1),
        "total_spend_at_risk":    round(total_risk, 2),
        "total_projected_uplift": round(total_uplift, 1),
    }
    return springs, kpis


# ── Main render ───────────────────────────────────────────────────────────────

if USE_BIGQUERY:
    st.success("🔗 **Live Mode** — Connected to Propellic BigQuery data lake (propellic-data-lake)")
elif USE_MOCK_DATA:
    render_demo_banner()

if not selected_ids:
    st.info("Select at least one campaign in the sidebar to begin.")
    st.stop()

springs, kpis = run_detection(selected_ids, min_conf)

# ── KPI Bar ───────────────────────────────────────────────────────────────────
st.markdown("### Account Overview")
render_kpi_bar(springs, kpis)
st.markdown("")

# ── Executive Summary (collapsible) ──────────────────────────────────────────
with st.expander("📋 Executive Summary — plain English, shareable with clients", expanded=True):
    summary_text = generate_executive_summary(springs, kpis)
    for para in summary_text.split("\n\n"):
        if para.strip():
            st.markdown(
                f'<p style="font-size:14px; color:#cbd5e1; line-height:1.7; margin-bottom:12px;">'
                f'{para.strip()}</p>',
                unsafe_allow_html=True,
            )

st.markdown("")

# ── PDF Export ────────────────────────────────────────────────────────────────
if springs:
    divergence_charts = {sp.campaign_id: build_divergence_chart(sp) for sp in springs}

    if st.button("📄 Export Report", type="primary", use_container_width=False):
        with st.spinner("Generating PDF…"):
            try:
                pdf_bytes = generate_pdf(
                    springs=springs,
                    kpis=kpis,
                    executive_summary=summary_text,
                    divergence_charts=divergence_charts,
                    report_title="Propellic",
                )
                st.download_button(
                    label="⬇ Download PDF",
                    data=pdf_bytes,
                    file_name=f"coiled_spring_report_{date.today()}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}. Ensure `kaleido` is installed.")

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🌀 Opportunity Alerts", "🔍 Signal Explorer"])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1 — Opportunity Alerts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab1:
    if not springs:
        st.markdown(
            """
            <div style="text-align:center; padding:60px 20px; color:#475569;">
                <div style="font-size:48px; margin-bottom:16px;">✅</div>
                <div style="font-size:18px; font-weight:600; color:#94a3b8;">
                    No Coiled Springs Detected</div>
                <div style="font-size:13px; margin-top:8px;">
                    All selected campaigns are performing within normal ranges.
                    Try lowering the confidence threshold or adjusting the date range.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Sort: high → medium → low
        sort_order = {"high": 0, "medium": 1, "low": 2}
        sorted_springs = sorted(springs, key=lambda s: sort_order.get(s.confidence, 9))

        st.markdown(
            f'<div style="font-size:13px; color:#64748b; margin-bottom:16px;">'
            f'Showing {len(sorted_springs)} active coiled spring '
            f'opportunit{"ies" if len(sorted_springs) != 1 else "y"} — '
            f'sorted by confidence</div>',
            unsafe_allow_html=True,
        )

        for spring in sorted_springs:
            fig = divergence_charts.get(spring.campaign_id) or build_divergence_chart(spring)
            render_opportunity_card(spring, fig)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2 — Signal Explorer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab2:
    st.markdown("#### Campaign Signal Explorer")

    if not selected_ids:
        st.info("Select a campaign in the sidebar.")
    else:
        explore_name = st.selectbox(
            "Select campaign to explore",
            options=selected_names,
            index=0,
        )
        explore_id = campaign_options[explore_name]

        explore_df  = load_campaign_data(explore_id, start_date, end_date)
        explore_sig = load_signals(explore_id, start_date, end_date)

        # Map toggle names → column names
        signal_col_map = {
            "weather_composite": use_weather,
            "news_score":        use_news,
            "seasonal_index":    use_seasonal,
            "economic_pressure": use_economic,
            "trends_index":      True,
        }
        selected_sig_cols = [k for k, v in signal_col_map.items() if v]

        overlay_fig = build_signal_overlay(explore_df, explore_sig, selected_sig_cols)
        st.plotly_chart(overlay_fig, use_container_width=True, config={"displayModeBar": False})

        # Correlation heatmap
        st.markdown("#### Cross-Signal Correlation Heatmap")
        corr_df = compute_correlations(explore_df, explore_sig)
        heatmap_fig = build_correlation_heatmap(corr_df)
        st.plotly_chart(heatmap_fig, use_container_width=True, config={"displayModeBar": False})

        # Historical accuracy tracker
        st.markdown("#### Historical Accuracy Tracker")
        outcomes = load_historical_outcomes()
        tracker_fig = build_historical_tracker(outcomes)
        st.plotly_chart(tracker_fig, use_container_width=True, config={"displayModeBar": False})

        # Raw data toggle
        with st.expander("View raw campaign data"):
            st.dataframe(
                explore_df.style.format({
                    "cvr": "{:.2%}",
                    "cost": "${:,.2f}",
                    "cpc": "${:.2f}",
                    "impression_share": "{:.1f}%",
                }),
                use_container_width=True,
                height=320,
            )
