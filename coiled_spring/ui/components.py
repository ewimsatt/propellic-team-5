"""Reusable Streamlit UI components — Propellic branded."""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

from analysis.detection import CoiledSpring
from config import CONFIDENCE_COLORS, CONFIDENCE_BG, BRAND_PINK, BRAND_MIDNIGHT

# ── KPI Summary Bar ──────────────────────────────────────────────────────────

def render_kpi_bar(springs: list[CoiledSpring], kpis: dict) -> None:
    cols = st.columns(4)

    with cols[0]:
        _metric_card(
            label="Active Coiled Springs",
            value=str(len(springs)),
            delta=None,
            accent=BRAND_PINK,
            icon="🌀",
        )
    with cols[1]:
        avg_cvr_delta = kpis.get("avg_cvr_delta_pct", 0)
        _metric_card(
            label="Avg CVR vs Baseline",
            value=f"{avg_cvr_delta:+.1f}%",
            delta="below normal" if avg_cvr_delta < 0 else "above normal",
            accent="#ef4444" if avg_cvr_delta < 0 else "#10b981",
            icon="📉",
        )
    with cols[2]:
        _metric_card(
            label="Spend at Risk (if cut)",
            value=f"${kpis.get('total_spend_at_risk', 0):,.0f}",
            delta="estimated over rebound window",
            accent="#a78bfa",
            icon="💸",
        )
    with cols[3]:
        _metric_card(
            label="Projected Recovery Uplift",
            value=f"{kpis.get('total_projected_uplift', 0):,.0f} conv.",
            delta="if spend is maintained",
            accent="#10b981",
            icon="📈",
        )


def _metric_card(label: str, value: str, delta, accent: str, icon: str) -> None:
    st.markdown(
        f"""
        <div style="
            background: {BRAND_MIDNIGHT};
            border: 1px solid #1e3348;
            border-left: 3px solid {accent};
            border-radius: 8px;
            padding: 16px 18px;
            min-height: 90px;
            font-family: 'Montserrat', sans-serif;
        ">
            <div style="font-size:11px; color:#64748b; text-transform:uppercase;
                        letter-spacing:.08em; margin-bottom:4px;">{icon} {label}</div>
            <div style="font-size:26px; font-weight:700; color:#f1f5f9;
                        line-height:1.2;">{value}</div>
            {f'<div style="font-size:11px; color:#64748b; margin-top:4px;">{delta}</div>'
              if delta else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Confidence badge ─────────────────────────────────────────────────────────

def confidence_badge(level: str) -> str:
    color = CONFIDENCE_COLORS.get(level, "#94a3b8")
    bg    = CONFIDENCE_BG.get(level, "rgba(148,163,184,0.1)")
    label = level.upper()
    return (
        f'<span style="background:{bg}; color:{color}; border:1px solid {color}; '
        f'padding:2px 10px; border-radius:20px; font-size:11px; font-weight:700; '
        f'letter-spacing:.06em; font-family:Montserrat,sans-serif;">{label}</span>'
    )


# ── Opportunity card ─────────────────────────────────────────────────────────

def render_opportunity_card(spring: CoiledSpring, chart_fig: go.Figure) -> None:
    conf_color = CONFIDENCE_COLORS.get(spring.confidence, "#94a3b8")

    with st.container():
        st.markdown(
            f"""
            <div style="
                background:{BRAND_MIDNIGHT};
                border:1px solid #1e3348;
                border-top: 2px solid {conf_color};
                border-radius:10px;
                padding:20px 24px 12px;
                margin-bottom:4px;
                font-family: 'Montserrat', sans-serif;
            ">
                <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                    <span style="font-size:18px; font-weight:700;
                                 color:#f1f5f9;">{spring.campaign_name}</span>
                    {confidence_badge(spring.confidence)}
                </div>
                <div style="display:flex; gap:24px; flex-wrap:wrap; margin-bottom:10px;">
                    {_signal_chips(spring.active_signals)}
                </div>
                <div style="font-size:12px; color:#64748b;">
                    Dip started {spring.start_date} · {spring.duration_days} days active ·
                    CVR is {abs(spring.cvr_z_score):.1f} SD below baseline ·
                    Impressions: <b style="color:{BRAND_PINK};">{spring.impression_trend}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.plotly_chart(chart_fig, use_container_width=True, config={"displayModeBar": False})

        if spring.signal_details:
            with st.expander("Signal details", expanded=False):
                for sig, detail in spring.signal_details.items():
                    icon = _signal_icon(sig)
                    st.markdown(f"**{icon} {sig.capitalize()}:** {detail}")

        st.markdown(
            f"""
            <div style="
                background:rgba(226,26,107,0.07);
                border:1px solid rgba(226,26,107,0.25);
                border-radius:8px;
                padding:12px 16px;
                margin-top:6px;
                margin-bottom:16px;
                font-family: 'Montserrat', sans-serif;
            ">
                <div style="font-size:11px; color:{BRAND_PINK}; font-weight:700;
                            text-transform:uppercase; letter-spacing:.08em;
                            margin-bottom:4px;">Recommended Action</div>
                <div style="font-size:13px; color:#cbd5e1;">{spring.recommendation}</div>
                <div style="margin-top:8px; display:flex; gap:24px; flex-wrap:wrap;">
                    <span style="font-size:11px; color:#64748b;">
                        📅 Rebound window: <b style="color:#e2e8f0;">
                        {spring.rebound_min_days}–{spring.rebound_max_days} days</b>
                    </span>
                    <span style="font-size:11px; color:#64748b;">
                        💸 Spend at risk: <b style="color:#a78bfa;">
                        ${spring.estimated_spend_at_risk:,.0f}</b>
                    </span>
                    <span style="font-size:11px; color:#64748b;">
                        📈 Recovery uplift: <b style="color:#10b981;">
                        +{spring.projected_recovery_uplift:,.0f} conv.</b>
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _signal_chips(signals: list[str]) -> str:
    colors = {
        "weather":  ("#60a5fa",  "rgba(96,165,250,0.12)"),
        "news":     ("#EB669C",  "rgba(235,102,156,0.12)"),
        "seasonal": ("#34d399",  "rgba(52,211,153,0.12)"),
        "economic": ("#a78bfa",  "rgba(167,139,250,0.12)"),
    }
    icons = {"weather": "🌧", "news": "📰", "seasonal": "📅", "economic": "📊"}
    chips = ""
    for s in signals:
        c, bg = colors.get(s, ("#94a3b8", "rgba(148,163,184,0.1)"))
        icon  = icons.get(s, "⚡")
        chips += (
            f'<span style="background:{bg}; color:{c}; border:1px solid {c}; '
            f'padding:2px 10px; border-radius:20px; font-size:11px; '
            f'font-family:Montserrat,sans-serif;">'
            f'{icon} {s.capitalize()}</span> '
        )
    return chips


def _signal_icon(sig: str) -> str:
    return {"weather": "🌧", "news": "📰", "seasonal": "📅", "economic": "📊"}.get(sig, "⚡")


# ── Demo mode banner ─────────────────────────────────────────────────────────

def render_demo_banner() -> None:
    st.info(
        "🎯 **Demo Mode** — Running on realistic mock data. "
        "Connect Google Ads credentials in `.env` to enable live data pulls.",
    )
