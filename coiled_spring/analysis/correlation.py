"""Cross-signal correlation analysis."""

from __future__ import annotations

import pandas as pd
import numpy as np


CAMPAIGN_METRICS = ["cvr", "impressions", "impression_share", "clicks", "conversions"]
SIGNAL_COLS = [
    "weather_composite", "news_score", "seasonal_index",
    "economic_pressure", "trends_index",
]
DISPLAY_LABELS = {
    "cvr":               "Conv. Rate",
    "impressions":       "Impressions",
    "impression_share":  "Imp. Share",
    "clicks":            "Clicks",
    "conversions":       "Conversions",
    "weather_composite": "Weather Anomaly",
    "news_score":        "News Intensity",
    "seasonal_index":    "Seasonal Index",
    "economic_pressure": "Econ. Pressure",
    "trends_index":      "Search Trends",
}


def compute_correlations(
    campaign_df: pd.DataFrame,
    signals_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Returns a correlation matrix (signals × campaign metrics) rounded to 2 decimals.
    """
    avail_metrics  = [c for c in CAMPAIGN_METRICS if c in campaign_df.columns]
    avail_signals  = [c for c in SIGNAL_COLS      if c in signals_df.columns]

    combined = pd.concat(
        [campaign_df[avail_metrics], signals_df[avail_signals]], axis=1
    ).dropna()

    if combined.shape[0] < 10:
        return pd.DataFrame()

    corr = combined.corr()
    result = corr.loc[avail_signals, avail_metrics].round(2)
    result.index   = [DISPLAY_LABELS.get(c, c) for c in result.index]
    result.columns = [DISPLAY_LABELS.get(c, c) for c in result.columns]
    return result


def identify_signal_anomalies(
    signals_df: pd.DataFrame,
    window: int = 7,
) -> pd.DataFrame:
    """
    Returns a DataFrame of z-scores per signal column.
    Values with |z| > 1.5 are considered anomalous.
    """
    result = pd.DataFrame(index=signals_df.index)
    for col in SIGNAL_COLS:
        if col not in signals_df.columns:
            continue
        series = signals_df[col]
        roll_mean = series.rolling(window, min_periods=3).mean()
        roll_std  = series.rolling(window, min_periods=3).std().replace(0, 1)
        result[f"{col}_zscore"] = ((series - roll_mean) / roll_std).fillna(0).round(2)
    return result
