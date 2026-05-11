"""Generates realistic mock data for demo mode. All random state is seeded for reproducibility."""

from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import date, timedelta


# ── Campaign definitions ─────────────────────────────────────────────────────

CAMPAIGN_CONFIGS = [
    {
        "id": "camp_001",
        "name": "Roofing — Storm Damage",
        "type": "roofing",
        "daily_budget": 850,
        "base_cvr": 0.042,
        "base_impressions": 1_400,
        "base_impression_share": 0.52,
        "ctr_base": 0.061,
        "cpc_base": 8.75,
        "spring": {
            "active": True,
            "start_offset": -28,   # days before today the spring started
            "duration": 28,
            "cvr_drop_factor": 0.38,
            "impression_behavior": "rising",
            "signals": ["weather", "news"],
        },
    },
    {
        "id": "camp_002",
        "name": "HVAC Installation",
        "type": "hvac",
        "daily_budget": 1_200,
        "base_cvr": 0.031,
        "base_impressions": 3_100,
        "base_impression_share": 0.48,
        "ctr_base": 0.045,
        "cpc_base": 6.40,
        "spring": {
            "active": True,
            "start_offset": -22,
            "duration": 22,
            "cvr_drop_factor": 0.51,
            "impression_behavior": "stable",
            "signals": ["weather", "seasonal"],
        },
    },
    {
        "id": "camp_003",
        "name": "Home Equity Loans",
        "type": "financial",
        "daily_budget": 2_400,
        "base_cvr": 0.018,
        "base_impressions": 5_800,
        "base_impression_share": 0.35,
        "ctr_base": 0.028,
        "cpc_base": 14.20,
        "spring": {
            "active": True,
            "start_offset": -18,
            "duration": 18,
            "cvr_drop_factor": 0.60,
            "impression_behavior": "stable",
            "signals": ["economic", "news"],
        },
    },
    {
        "id": "camp_004",
        "name": "Gutter Cleaning",
        "type": "seasonal_service",
        "daily_budget": 320,
        "base_cvr": 0.055,
        "base_impressions": 780,
        "base_impression_share": 0.61,
        "ctr_base": 0.075,
        "cpc_base": 4.10,
        "spring": {
            "active": True,
            "start_offset": -12,
            "duration": 12,
            "cvr_drop_factor": 0.68,
            "impression_behavior": "stable",
            "signals": ["seasonal"],
        },
    },
    {
        "id": "camp_005",
        "name": "Lawn Care Services",
        "type": "lawn",
        "daily_budget": 460,
        "base_cvr": 0.038,
        "base_impressions": 2_200,
        "base_impression_share": 0.55,
        "ctr_base": 0.052,
        "cpc_base": 3.80,
        "spring": None,
    },
    {
        "id": "camp_006",
        "name": "Plumbing Emergency",
        "type": "emergency",
        "daily_budget": 680,
        "base_cvr": 0.071,
        "base_impressions": 950,
        "base_impression_share": 0.67,
        "ctr_base": 0.082,
        "cpc_base": 9.50,
        "spring": None,
    },
    {
        "id": "camp_007",
        "name": "Window Replacement",
        "type": "home_improvement",
        "daily_budget": 990,
        "base_cvr": 0.024,
        "base_impressions": 2_700,
        "base_impression_share": 0.43,
        "ctr_base": 0.038,
        "cpc_base": 11.30,
        "spring": None,
    },
]


class MockDataGenerator:
    """Deterministic mock data generator — same seed = same output every run."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.today = date.today()
        self.start_date = self.today - timedelta(days=89)
        self.dates = pd.date_range(self.start_date, self.today, freq="D")
        self._weather_cache: pd.DataFrame | None = None
        self._news_cache: pd.DataFrame | None = None
        self._economic_cache: pd.DataFrame | None = None

    # ── Campaign list ────────────────────────────────────────────────────────

    def get_campaigns(self) -> list[dict]:
        return [{"id": c["id"], "name": c["name"]} for c in CAMPAIGN_CONFIGS]

    # ── Campaign timeseries ──────────────────────────────────────────────────

    def get_campaign_timeseries(self, campaign_id: str) -> pd.DataFrame:
        cfg = next(c for c in CAMPAIGN_CONFIGS if c["id"] == campaign_id)
        n = len(self.dates)
        seed_offset = int(campaign_id[-3:])
        rng = np.random.default_rng(42 + seed_offset)

        # Weekly seasonality factor (weekends are ~40% lower)
        dow = np.array([d.dayofweek for d in self.dates])
        weekly = np.where(dow < 5, 1.0, 0.60)

        # Slight upward trend in impressions
        trend = np.linspace(0.97, 1.03, n)

        impressions = (
            cfg["base_impressions"] * weekly * trend
            + rng.normal(0, cfg["base_impressions"] * 0.07, n)
        ).clip(200)

        imp_share = (
            cfg["base_impression_share"] + rng.normal(0, 0.025, n)
        ).clip(0.15, 0.95)

        cvr = (cfg["base_cvr"] + rng.normal(0, cfg["base_cvr"] * 0.06, n)).clip(0.002)

        # ── Inject coiled spring pattern ─────────────────────────────────────
        sp = cfg.get("spring")
        if sp and sp["active"]:
            spring_start_idx = n + sp["start_offset"]  # offset is negative
            spring_start_idx = max(spring_start_idx, 0)

            for i in range(spring_start_idx, n):
                progress = (i - spring_start_idx) / max(sp["duration"] - 1, 1)
                # CVR ramps down sharply over first half, then lingers
                ramp = min(progress * 2.2, 1.0)
                drop = 1.0 - (1.0 - sp["cvr_drop_factor"]) * ramp
                cvr[i] *= drop

            if sp["impression_behavior"] == "rising":
                for i in range(spring_start_idx, n):
                    progress = (i - spring_start_idx) / max(sp["duration"] - 1, 1)
                    impressions[i] *= 1.0 + 0.28 * min(progress, 1.0)
                    imp_share[i] = (imp_share[i] * 1.12).clip(0.15, 0.95)

        impressions = impressions.round().astype(int)
        clicks = np.round(impressions * imp_share * cfg["ctr_base"]).astype(int).clip(0)
        conversions = np.round(clicks * cvr).astype(int).clip(0)
        cost = clicks * cfg["cpc_base"] * (1 + rng.normal(0, 0.04, n))
        cpc = np.where(clicks > 0, cost / np.maximum(clicks, 1), cfg["cpc_base"])

        return pd.DataFrame(
            {
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "cvr": cvr,
                "cost": cost.round(2),
                "impression_share": (imp_share * 100).round(1),
                "cpc": cpc.round(2),
            },
            index=self.dates,
        )

    # ── Weather signal ───────────────────────────────────────────────────────

    def get_weather_signal(self) -> pd.DataFrame:
        if self._weather_cache is not None:
            return self._weather_cache
        n = len(self.dates)
        rng = np.random.default_rng(101)

        temp_anomaly = rng.normal(0, 1.0, n)
        precip_anomaly = rng.normal(0, 0.8, n)

        # Inject a significant cold/storm event ~28 days ago
        storm_idx = n - 30
        for i in range(storm_idx, storm_idx + 7):
            if 0 <= i < n:
                temp_anomaly[i] -= rng.uniform(2.5, 4.2)
                precip_anomaly[i] += rng.uniform(2.0, 3.8)

        # Composite weather anomaly score (positive = anomalous)
        composite = (np.abs(temp_anomaly) + np.abs(precip_anomaly)) / 2

        df = pd.DataFrame(
            {
                "weather_temp_anomaly": temp_anomaly.round(2),
                "weather_precip_anomaly": precip_anomaly.round(2),
                "weather_composite": composite.round(2),
            },
            index=self.dates,
        )
        self._weather_cache = df
        return df

    # ── News signal ──────────────────────────────────────────────────────────

    def get_news_signal(self) -> pd.DataFrame:
        if self._news_cache is not None:
            return self._news_cache
        n = len(self.dates)
        rng = np.random.default_rng(202)

        # Low baseline noise
        news_score = rng.uniform(0.05, 0.30, n)

        # Two news bursts: one ~28 days ago (storm coverage), one ~16 days ago (economic headlines)
        for burst_offset, intensity, duration in [(-30, 0.72, 8), (-18, 0.65, 6)]:
            idx = n + burst_offset
            for i in range(idx, idx + duration):
                if 0 <= i < n:
                    news_score[i] = min(news_score[i] + intensity * rng.uniform(0.8, 1.0), 1.0)

        event_flag = (news_score > 0.55).astype(int)

        df = pd.DataFrame(
            {
                "news_score": news_score.round(3),
                "news_event_flag": event_flag,
            },
            index=self.dates,
        )
        self._news_cache = df
        return df

    # ── Economic signal ──────────────────────────────────────────────────────

    def get_economic_signal(self) -> pd.DataFrame:
        if self._economic_cache is not None:
            return self._economic_cache
        n = len(self.dates)
        rng = np.random.default_rng(303)

        # Consumer confidence index (baseline ~100, slow-moving)
        base_confidence = 98.5
        daily_changes = rng.normal(0, 0.25, n)
        # Gradual deterioration starting ~20 days ago
        drift = np.zeros(n)
        drift_start = n - 22
        drift[drift_start:] = np.linspace(0, -6.5, n - drift_start)
        confidence = base_confidence + np.cumsum(daily_changes) * 0.1 + drift

        # Unemployment change index (0 = stable, +/- = change)
        unemployment_delta = rng.normal(0, 0.08, n)
        unemployment_delta[n - 20 :] += 0.12

        # Composite economic pressure index (higher = more pressure)
        economic_pressure = (
            (100 - confidence) / 20 + np.abs(unemployment_delta) * 2
        ).clip(0)

        df = pd.DataFrame(
            {
                "consumer_confidence": confidence.round(1),
                "unemployment_delta": unemployment_delta.round(3),
                "economic_pressure": economic_pressure.round(3),
            },
            index=self.dates,
        )
        self._economic_cache = df
        return df

    # ── Search trends signal ─────────────────────────────────────────────────

    def get_trends_signal(self, campaign_id: str) -> pd.DataFrame:
        cfg = next((c for c in CAMPAIGN_CONFIGS if c["id"] == campaign_id), CAMPAIGN_CONFIGS[0])
        n = len(self.dates)
        seed_val = (abs(hash(campaign_id)) % 900) + 400
        rng = np.random.default_rng(seed_val)

        base_index = 55 + rng.uniform(-5, 5)
        trend_index = base_index + rng.normal(0, 4, n)

        sp = cfg.get("spring")
        if sp and sp["active"]:
            spring_start = n + sp["start_offset"]
            if sp["impression_behavior"] == "rising":
                # Trends spike with impressions
                trend_index[spring_start:] *= np.linspace(1.0, 1.35, n - spring_start)

        trend_index = trend_index.clip(10, 100)

        return pd.DataFrame(
            {"trends_index": trend_index.round(1)},
            index=self.dates,
        )

    # ── Seasonal index ───────────────────────────────────────────────────────

    def get_seasonal_signal(self, campaign_id: str) -> pd.DataFrame:
        cfg = next((c for c in CAMPAIGN_CONFIGS if c["id"] == campaign_id), CAMPAIGN_CONFIGS[0])
        n = len(self.dates)

        # Build a simple seasonal curve based on campaign type
        seasonal_profiles = {
            "roofing":         [0.7, 0.8, 1.0, 1.1, 1.1, 1.0, 0.9, 0.9, 1.0, 1.1, 0.9, 0.7],
            "hvac":            [1.2, 1.0, 0.8, 0.7, 0.9, 1.3, 1.4, 1.3, 1.1, 0.8, 0.9, 1.1],
            "financial":       [1.0, 1.0, 1.0, 0.9, 0.9, 0.9, 1.0, 1.0, 1.1, 1.1, 1.0, 1.0],
            "seasonal_service":[0.5, 0.5, 0.7, 1.0, 1.1, 0.9, 0.7, 0.7, 1.0, 1.1, 0.7, 0.5],
            "lawn":            [0.4, 0.5, 0.8, 1.1, 1.3, 1.2, 1.1, 1.1, 1.0, 0.8, 0.5, 0.3],
            "emergency":       [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            "home_improvement":[0.8, 0.8, 1.0, 1.1, 1.2, 1.1, 1.0, 1.0, 1.1, 1.0, 0.9, 0.8],
        }
        profile = seasonal_profiles.get(cfg["type"], [1.0] * 12)

        indices = [profile[d.month - 1] for d in self.dates]
        return pd.DataFrame(
            {"seasonal_index": indices},
            index=self.dates,
        )

    # ── Unified signals DataFrame ────────────────────────────────────────────

    def get_all_signals(self, campaign_id: str) -> pd.DataFrame:
        weather  = self.get_weather_signal()
        news     = self.get_news_signal()
        economic = self.get_economic_signal()
        trends   = self.get_trends_signal(campaign_id)
        seasonal = self.get_seasonal_signal(campaign_id)
        return pd.concat([weather, news, economic, trends, seasonal], axis=1)

    # ── Historical outcomes (for accuracy tracker) ───────────────────────────

    def get_historical_outcomes(self) -> list[dict]:
        base = self.today - timedelta(days=90)
        return [
            {
                "campaign": "Roofing — Storm Damage",
                "flag_date": str(base - timedelta(days=45)),
                "signal": "weather",
                "confidence": "high",
                "rebound_predicted_days": 10,
                "outcome": "rebounded",
                "actual_days": 8,
            },
            {
                "campaign": "HVAC Installation",
                "flag_date": str(base - timedelta(days=60)),
                "signal": "seasonal",
                "confidence": "medium",
                "rebound_predicted_days": 25,
                "outcome": "rebounded",
                "actual_days": 22,
            },
            {
                "campaign": "Home Equity Loans",
                "flag_date": str(base - timedelta(days=75)),
                "signal": "economic",
                "confidence": "medium",
                "rebound_predicted_days": 35,
                "outcome": "rebounded",
                "actual_days": 41,
            },
            {
                "campaign": "Lawn Care Services",
                "flag_date": str(base - timedelta(days=50)),
                "signal": "seasonal",
                "confidence": "low",
                "rebound_predicted_days": 20,
                "outcome": "no_rebound",
                "actual_days": None,
            },
            {
                "campaign": "Roofing — Storm Damage",
                "flag_date": str(base - timedelta(days=110)),
                "signal": "weather",
                "confidence": "high",
                "rebound_predicted_days": 9,
                "outcome": "rebounded",
                "actual_days": 11,
            },
            {
                "campaign": "Window Replacement",
                "flag_date": str(base - timedelta(days=85)),
                "signal": "economic",
                "confidence": "low",
                "rebound_predicted_days": 40,
                "outcome": "rebounded",
                "actual_days": 33,
            },
        ]
