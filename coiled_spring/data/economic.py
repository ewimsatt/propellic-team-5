"""FRED API economic signal integration."""

from __future__ import annotations

from datetime import date
import pandas as pd
import requests

from config import FRED_API_KEY, USE_MOCK_DATA
from mock_data import MockDataGenerator

_mock = MockDataGenerator()

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Series used: UMCSENT = Consumer Sentiment, UNRATE = Unemployment Rate
FRED_SERIES = {
    "consumer_confidence": "UMCSENT",
    "unemployment":        "UNRATE",
}


def get_economic_signal(
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    if USE_MOCK_DATA or not FRED_API_KEY:
        return _mock.get_economic_signal()

    try:
        frames = {}
        for label, series_id in FRED_SERIES.items():
            params = {
                "series_id": series_id,
                "observation_start": str(start_date),
                "observation_end": str(end_date),
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "frequency": "d",
                "aggregation_method": "avg",
            }
            resp = requests.get(FRED_BASE, params=params, timeout=10)
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            series = pd.Series(
                {o["date"]: float(o["value"]) for o in obs if o["value"] != "."}
            )
            series.index = pd.to_datetime(series.index)
            frames[label] = series

        dates = pd.date_range(start_date, end_date, freq="D")
        df = pd.DataFrame(frames, index=dates).ffill().bfill()

        # Normalise: unemployment delta and economic pressure composite
        df["unemployment_delta"] = df["unemployment"].diff().fillna(0)
        df["economic_pressure"]  = (
            (100 - df["consumer_confidence"]) / 20
            + df["unemployment_delta"].abs() * 2
        ).clip(lower=0)

        return df[["consumer_confidence", "unemployment_delta", "economic_pressure"]]
    except Exception:
        return _mock.get_economic_signal()
