"""Coiled Spring detection engine — the core analytical logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from config import (
    CVR_DROP_THRESHOLD_SD, IMPRESSION_FLOOR_PCT, MIN_SIGNALS_FOR_FLAG,
    SPRING_MIN_DURATION_DAYS, BASELINE_PERIOD_DAYS, DETECTION_WINDOW_DAYS,
    SIGNAL_ANOMALY_SD, NEWS_SCORE_THRESHOLD, SEASONAL_DEVIATION_PCT,
    ECONOMIC_DEVIATION_PCT, CONFIDENCE_THRESHOLDS, RECOVERY_WINDOWS,
)


@dataclass
class CoiledSpring:
    campaign_id:    str
    campaign_name:  str
    start_date:     date
    end_date:       date
    duration_days:  int
    confidence:     str   # "low" | "medium" | "high"
    confidence_score: int
    cvr_baseline:   float
    cvr_current:    float
    cvr_z_score:    float
    impression_trend: str  # "rising" | "stable" | "slight_decline"
    active_signals: list[str]
    signal_details: dict
    rebound_min_days: int
    rebound_max_days: int
    estimated_spend_at_risk: float
    projected_recovery_uplift: float
    recommendation: str
    campaign_df:    pd.DataFrame = field(repr=False)
    signals_df:     pd.DataFrame = field(repr=False)


class CoiledSpringDetector:

    def detect(
        self,
        campaign_id: str,
        campaign_name: str,
        campaign_df: pd.DataFrame,
        signals_df: pd.DataFrame,
    ) -> Optional[CoiledSpring]:
        """
        Returns the most severe active CoiledSpring for this campaign, or None.
        Examines the most recent DETECTION_WINDOW_DAYS of data against a
        BASELINE_PERIOD_DAYS baseline.
        """
        if len(campaign_df) < BASELINE_PERIOD_DAYS + SPRING_MIN_DURATION_DAYS:
            return None

        # Align signals to campaign dates
        signals_df = signals_df.reindex(campaign_df.index).ffill().bfill()

        baseline = campaign_df.iloc[:BASELINE_PERIOD_DAYS]
        recent   = campaign_df.iloc[BASELINE_PERIOD_DAYS:]

        cvr_mean = baseline["cvr"].mean()
        cvr_std  = baseline["cvr"].std()
        if cvr_std == 0:
            return None

        imp_baseline = baseline["impression_share"].mean()

        # Scan the recent window for consecutive flagged days
        flags = self._flag_days(
            recent, signals_df.iloc[BASELINE_PERIOD_DAYS:],
            cvr_mean, cvr_std, imp_baseline,
        )

        windows = self._find_consecutive_windows(flags, SPRING_MIN_DURATION_DAYS)
        if not windows:
            return None

        # Pick the most recent window (most actionable)
        win_start_idx, win_end_idx = windows[-1]
        window_df  = recent.iloc[win_start_idx: win_end_idx + 1]
        window_sig = signals_df.iloc[BASELINE_PERIOD_DAYS + win_start_idx:
                                      BASELINE_PERIOD_DAYS + win_end_idx + 1]

        cvr_current = window_df["cvr"].mean()
        cvr_z       = (cvr_current - cvr_mean) / cvr_std
        imp_current = window_df["impression_share"].mean()
        imp_change  = (imp_current - imp_baseline) / imp_baseline

        if imp_change > 0.05:
            imp_trend = "rising"
        elif imp_change > IMPRESSION_FLOOR_PCT:
            imp_trend = "stable"
        else:
            imp_trend = "slight_decline"

        active_signals, signal_details = self._score_signals(window_sig, signals_df)

        if len(active_signals) < MIN_SIGNALS_FOR_FLAG:
            return None

        confidence_score = len(active_signals)
        if confidence_score >= CONFIDENCE_THRESHOLDS["high"]:
            confidence = "high"
        elif confidence_score >= CONFIDENCE_THRESHOLDS["medium"]:
            confidence = "medium"
        else:
            confidence = "low"

        rebound_min, rebound_max = self._rebound_window(active_signals)
        rebound_midpoint = (rebound_min + rebound_max) / 2

        daily_spend = window_df["cost"].mean()
        spend_at_risk = daily_spend * rebound_midpoint

        # Uplift = estimated additional conversions at baseline CVR vs current CVR
        avg_impressions = window_df["impressions"].mean()
        avg_imp_share   = window_df["impression_share"].mean() / 100
        avg_ctr         = (window_df["clicks"] / window_df["impressions"].replace(0, 1)).mean()
        future_clicks   = avg_impressions * avg_imp_share * avg_ctr * rebound_midpoint
        uplift = future_clicks * (cvr_mean - cvr_current)
        uplift = max(uplift, 0)

        recommendation = self._build_recommendation(
            confidence, active_signals, cvr_z, rebound_min, rebound_max, imp_trend
        )

        return CoiledSpring(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            start_date=window_df.index[0].date(),
            end_date=window_df.index[-1].date(),
            duration_days=len(window_df),
            confidence=confidence,
            confidence_score=confidence_score,
            cvr_baseline=round(cvr_mean, 4),
            cvr_current=round(cvr_current, 4),
            cvr_z_score=round(cvr_z, 2),
            impression_trend=imp_trend,
            active_signals=active_signals,
            signal_details=signal_details,
            rebound_min_days=rebound_min,
            rebound_max_days=rebound_max,
            estimated_spend_at_risk=round(spend_at_risk, 2),
            projected_recovery_uplift=round(uplift, 1),
            recommendation=recommendation,
            campaign_df=campaign_df,
            signals_df=signals_df,
        )

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _flag_days(
        self,
        recent_df: pd.DataFrame,
        recent_sig: pd.DataFrame,
        cvr_mean: float,
        cvr_std: float,
        imp_baseline: float,
    ) -> pd.Series:
        """Returns a boolean Series marking days that meet spring pre-conditions."""
        cvr_z = (recent_df["cvr"] - cvr_mean) / cvr_std
        cvr_flag = cvr_z < -CVR_DROP_THRESHOLD_SD

        imp_change = (recent_df["impression_share"] - imp_baseline) / imp_baseline
        imp_flag = imp_change > IMPRESSION_FLOOR_PCT

        signal_flag = self._any_signal_anomalous(recent_sig)

        return cvr_flag & imp_flag & signal_flag

    def _any_signal_anomalous(self, sig: pd.DataFrame) -> pd.Series:
        flags = pd.Series(False, index=sig.index)

        if "weather_composite" in sig.columns:
            weather_mean = sig["weather_composite"].mean()
            weather_std  = sig["weather_composite"].std() or 1
            flags |= ((sig["weather_composite"] - weather_mean) / weather_std) > SIGNAL_ANOMALY_SD

        if "news_score" in sig.columns:
            flags |= sig["news_score"] > NEWS_SCORE_THRESHOLD

        if "seasonal_index" in sig.columns:
            s_mean = sig["seasonal_index"].mean()
            flags |= (sig["seasonal_index"] - s_mean).abs() / s_mean > SEASONAL_DEVIATION_PCT

        if "economic_pressure" in sig.columns:
            ep_mean = sig["economic_pressure"].mean()
            flags |= (sig["economic_pressure"] - ep_mean).abs() / (ep_mean or 1) > ECONOMIC_DEVIATION_PCT

        return flags

    def _find_consecutive_windows(
        self, flags: pd.Series, min_days: int
    ) -> list[tuple[int, int]]:
        windows: list[tuple[int, int]] = []
        start = None
        for i, val in enumerate(flags):
            if val and start is None:
                start = i
            elif not val and start is not None:
                if (i - start) >= min_days:
                    windows.append((start, i - 1))
                start = None
        if start is not None and (len(flags) - start) >= min_days:
            windows.append((start, len(flags) - 1))
        return windows

    def _score_signals(
        self,
        window_sig: pd.DataFrame,
        full_sig: pd.DataFrame,
    ) -> tuple[list[str], dict]:
        active = []
        details: dict = {}

        # Weather
        if "weather_composite" in window_sig.columns:
            full_mean = full_sig["weather_composite"].mean()
            full_std  = full_sig["weather_composite"].std() or 1
            w_z = (window_sig["weather_composite"].mean() - full_mean) / full_std
            if w_z > SIGNAL_ANOMALY_SD:
                active.append("weather")
                temp_dir = "colder" if window_sig["weather_temp_anomaly"].mean() < 0 else "warmer"
                details["weather"] = (
                    f"Significant weather anomaly detected — temperatures running "
                    f"{abs(window_sig['weather_temp_anomaly'].mean()):.1f}°C {temp_dir} than normal "
                    f"with elevated precipitation."
                )

        # News
        if "news_score" in window_sig.columns:
            avg_score = window_sig["news_score"].mean()
            if avg_score > NEWS_SCORE_THRESHOLD:
                active.append("news")
                details["news"] = (
                    f"Elevated news/political activity (intensity: {avg_score:.2f}) "
                    f"coinciding with the conversion rate drop."
                )

        # Seasonal
        if "seasonal_index" in window_sig.columns:
            s_mean = full_sig["seasonal_index"].mean()
            s_current = window_sig["seasonal_index"].mean()
            deviation = (s_current - s_mean) / s_mean
            if abs(deviation) > SEASONAL_DEVIATION_PCT:
                active.append("seasonal")
                direction = "below" if deviation < 0 else "above"
                details["seasonal"] = (
                    f"Seasonal index is {abs(deviation)*100:.0f}% {direction} the annual average "
                    f"for this campaign type — a predictable cyclical trough."
                )

        # Economic
        if "economic_pressure" in window_sig.columns:
            ep_mean = full_sig["economic_pressure"].mean()
            ep_now  = window_sig["economic_pressure"].mean()
            if ep_mean > 0 and abs(ep_now - ep_mean) / ep_mean > ECONOMIC_DEVIATION_PCT:
                active.append("economic")
                pressure_dir = "increased" if ep_now > ep_mean else "decreased"
                details["economic"] = (
                    f"Economic pressure index has {pressure_dir} by "
                    f"{abs(ep_now - ep_mean)/ep_mean*100:.0f}% — likely reflecting consumer "
                    f"hesitation, not a loss of demand."
                )

        return active, details

    def _rebound_window(self, signals: list[str]) -> tuple[int, int]:
        if not signals:
            return (7, 30)
        mins = [RECOVERY_WINDOWS.get(s, (7, 30))[0] for s in signals]
        maxs = [RECOVERY_WINDOWS.get(s, (7, 30))[1] for s in signals]
        return (min(mins), max(maxs))

    def _build_recommendation(
        self,
        confidence: str,
        signals: list[str],
        cvr_z: float,
        rebound_min: int,
        rebound_max: int,
        imp_trend: str,
    ) -> str:
        action = "maintain" if confidence == "low" else "increase"
        signal_str = " and ".join(signals) if signals else "external factors"
        intent_str = (
            "rising intent signals suggest demand is building"
            if imp_trend == "rising"
            else "steady impression volume confirms ongoing search demand"
        )
        return (
            f"Recommend {action} budget spend. The CVR dip ({cvr_z:.1f} SD below baseline) "
            f"appears driven by {signal_str} — not declining demand. {intent_str.capitalize()}. "
            f"Historical patterns for this signal type show recovery within "
            f"{rebound_min}–{rebound_max} days."
        )
