"""Plotly chart builders — all return go.Figure objects with the dark theme applied."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import (
    COLOR_INTENT, COLOR_CVR,
    COLOR_SIGNAL_WEATHER, COLOR_SIGNAL_NEWS,
    COLOR_SIGNAL_SEASONAL, COLOR_SIGNAL_ECONOMIC,
    COLOR_SPRING_ZONE, CHART_BG, CHART_GRID, CHART_TEXT, CHART_AXIS,
    CONFIDENCE_COLORS,
)
from analysis.detection import CoiledSpring


# ── Shared theme helper ──────────────────────────────────────────────────────

def _dark_layout(**kwargs) -> dict:
    base = dict(
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(color=CHART_TEXT, size=12),
        xaxis=dict(
            gridcolor=CHART_GRID, linecolor=CHART_AXIS, tickcolor=CHART_AXIS,
            showgrid=True, zeroline=False,
        ),
        yaxis=dict(
            gridcolor=CHART_GRID, linecolor=CHART_AXIS, tickcolor=CHART_AXIS,
            showgrid=True, zeroline=False,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=CHART_GRID,
            borderwidth=1,
        ),
        margin=dict(l=48, r=48, t=40, b=40),
        hovermode="x unified",
    )
    base.update(kwargs)
    return base


# ── 1. Divergence chart ──────────────────────────────────────────────────────

def build_divergence_chart(spring: CoiledSpring) -> go.Figure:
    """
    Dual-axis chart: impression share (left, blue) + CVR (right, amber).
    Spring window is highlighted with a shaded region.
    """
    df = spring.campaign_df

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Impression share
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["impression_share"],
            name="Impression Share (%)",
            line=dict(color=COLOR_INTENT, width=2.5),
            fill="tozeroy",
            fillcolor=f"rgba(59,130,246,0.08)",
            hovertemplate="%{y:.1f}%<extra>Imp. Share</extra>",
        ),
        secondary_y=False,
    )

    # CVR
    fig.add_trace(
        go.Scatter(
            x=df.index, y=(df["cvr"] * 100),
            name="Conv. Rate (%)",
            line=dict(color=COLOR_CVR, width=2.5),
            hovertemplate="%{y:.2f}%<extra>CVR</extra>",
        ),
        secondary_y=True,
    )

    # Baseline CVR dashed line
    baseline_cvr = spring.cvr_baseline * 100
    fig.add_hline(
        y=baseline_cvr,
        line=dict(color=COLOR_CVR, width=1, dash="dash"),
        secondary_y=True,
        annotation_text=f"CVR baseline {baseline_cvr:.2f}%",
        annotation_font=dict(color=COLOR_CVR, size=10),
        annotation_position="top right",
    )

    # Spring zone shading
    spring_start = str(spring.start_date)
    spring_end   = str(spring.end_date)
    conf_color   = CONFIDENCE_COLORS.get(spring.confidence, "#f59e0b")

    fig.add_vrect(
        x0=spring_start, x1=spring_end,
        fillcolor=COLOR_SPRING_ZONE,
        layer="below",
        line_width=0,
    )
    fig.add_vline(
        x=spring_start,
        line=dict(color=conf_color, width=1.5, dash="dot"),
        annotation_text="Spring starts",
        annotation_font=dict(color=conf_color, size=10),
    )

    layout = _dark_layout(
        title=dict(
            text=f"<b>{spring.campaign_name}</b> — Intent vs. Conversion Rate",
            font=dict(size=14, color="#e2e8f0"),
            x=0,
        ),
        height=320,
        xaxis=dict(gridcolor=CHART_GRID, linecolor=CHART_AXIS, tickcolor=CHART_AXIS),
        yaxis=dict(
            title=dict(text="Impression Share (%)", font=dict(color=COLOR_INTENT)),
            gridcolor=CHART_GRID, linecolor=CHART_AXIS, tickcolor=CHART_AXIS,
            tickfont=dict(color=COLOR_INTENT),
        ),
        yaxis2=dict(
            title=dict(text="Conv. Rate (%)", font=dict(color=COLOR_CVR)),
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(color=COLOR_CVR),
            overlaying="y",
            side="right",
        ),
    )
    fig.update_layout(**layout)
    return fig


# ── 2. Signal overlay chart ──────────────────────────────────────────────────

SIGNAL_STYLE = {
    "cvr":               dict(color=COLOR_CVR,             name="Conv. Rate (norm.)"),
    "impression_share":  dict(color=COLOR_INTENT,          name="Imp. Share (norm.)"),
    "weather_composite": dict(color=COLOR_SIGNAL_WEATHER,  name="Weather Anomaly"),
    "news_score":        dict(color=COLOR_SIGNAL_NEWS,     name="News Intensity"),
    "seasonal_index":    dict(color=COLOR_SIGNAL_SEASONAL, name="Seasonal Index"),
    "economic_pressure": dict(color=COLOR_SIGNAL_ECONOMIC, name="Econ. Pressure"),
    "trends_index":      dict(color="#fb923c",             name="Search Trends"),
}


def build_signal_overlay(
    campaign_df: pd.DataFrame,
    signals_df: pd.DataFrame,
    selected_signals: list[str],
) -> go.Figure:
    """Normalised (0–1) overlay of CVR, impression share, and selected signals."""
    fig = go.Figure()

    combined = pd.concat([campaign_df, signals_df], axis=1).dropna(how="all")

    cols_to_plot = ["cvr", "impression_share"] + [
        s for s in selected_signals
        if s in combined.columns
    ]

    for col in cols_to_plot:
        if col not in combined.columns:
            continue
        series = combined[col].fillna(method="ffill")
        mn, mx = series.min(), series.max()
        normed = (series - mn) / (mx - mn) if mx != mn else series * 0

        style = SIGNAL_STYLE.get(col, dict(color="#94a3b8", name=col))
        fig.add_trace(
            go.Scatter(
                x=combined.index,
                y=normed,
                name=style["name"],
                line=dict(color=style["color"], width=2),
                hovertemplate=f"%{{y:.2f}} (norm.)<extra>{style['name']}</extra>",
            )
        )

    fig.update_layout(
        **_dark_layout(
            title=dict(
                text="Signal Overlay — Normalised (0–1)",
                font=dict(size=14, color="#e2e8f0"), x=0,
            ),
            height=400,
            yaxis=dict(
                title="Normalised Value",
                gridcolor=CHART_GRID, linecolor=CHART_AXIS,
                range=[-0.05, 1.1],
            ),
        )
    )
    return fig


# ── 3. Correlation heatmap ───────────────────────────────────────────────────

def build_correlation_heatmap(corr_df: pd.DataFrame) -> go.Figure:
    if corr_df.empty:
        fig = go.Figure()
        fig.update_layout(**_dark_layout(height=300))
        return fig

    fig = go.Figure(
        data=go.Heatmap(
            z=corr_df.values,
            x=corr_df.columns.tolist(),
            y=corr_df.index.tolist(),
            colorscale=[
                [0.0,  "#ef4444"],
                [0.5,  CHART_BG],
                [1.0,  "#3b82f6"],
            ],
            zmin=-1, zmax=1,
            text=corr_df.values.round(2),
            texttemplate="%{text}",
            hovertemplate="Correlation: %{z:.2f}<extra>%{y} × %{x}</extra>",
            showscale=True,
            colorbar=dict(
                tickfont=dict(color=CHART_TEXT),
                outlinecolor=CHART_GRID,
                thickness=12,
            ),
        )
    )
    fig.update_layout(
        **_dark_layout(
            title=dict(
                text="Signal × Campaign KPI Correlation",
                font=dict(size=14, color="#e2e8f0"), x=0,
            ),
            height=360,
            xaxis=dict(
                tickangle=-30,
                gridcolor="rgba(0,0,0,0)",
                linecolor=CHART_AXIS,
            ),
            yaxis=dict(
                gridcolor="rgba(0,0,0,0)",
                linecolor=CHART_AXIS,
            ),
        )
    )
    return fig


# ── 4. Historical accuracy tracker ──────────────────────────────────────────

def build_historical_tracker(outcomes: list[dict]) -> go.Figure:
    if not outcomes:
        return go.Figure()

    rebounded     = [o for o in outcomes if o.get("outcome") == "rebounded"]
    no_rebound    = [o for o in outcomes if o.get("outcome") == "no_rebound"]

    signal_labels = sorted({o.get("signal", "unknown") for o in outcomes})

    def count_by_signal(subset):
        return [sum(1 for o in subset if o.get("signal") == s) for s in signal_labels]

    fig = go.Figure()
    fig.add_bar(
        name="Rebounded ✓",
        x=signal_labels,
        y=count_by_signal(rebounded),
        marker_color="#10b981",
        hovertemplate="%{y} rebounds<extra></extra>",
    )
    fig.add_bar(
        name="No Rebound ✗",
        x=signal_labels,
        y=count_by_signal(no_rebound),
        marker_color="#ef4444",
        hovertemplate="%{y} no-rebound<extra></extra>",
    )
    total   = len(outcomes)
    correct = len(rebounded)
    accuracy = f"{correct/total*100:.0f}%" if total else "N/A"

    fig.update_layout(
        **_dark_layout(
            title=dict(
                text=f"Historical Coiled Spring Accuracy — {accuracy} rebound rate "
                     f"({correct}/{total} flagged events)",
                font=dict(size=13, color="#e2e8f0"), x=0,
            ),
            barmode="group",
            height=300,
            xaxis=dict(title="Signal Type", gridcolor="rgba(0,0,0,0)"),
            yaxis=dict(title="Events", gridcolor=CHART_GRID),
        )
    )
    return fig


# ── 5. KPI sparkline ─────────────────────────────────────────────────────────

def build_sparkline(series: pd.Series, color: str, height: int = 80) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=series.index, y=series.values,
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=color.replace(")", ",0.12)").replace("rgb", "rgba"),
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
