"""Open-Meteo weather integration (free, no API key required)."""

from __future__ import annotations

from datetime import date
import pandas as pd
import requests

from config import USE_MOCK_DATA
from mock_data import MockDataGenerator

_mock = MockDataGenerator()

# Default lat/lon: Austin, TX — override via .env WEATHER_LAT / WEATHER_LON
import os
WEATHER_LAT = float(os.getenv("WEATHER_LAT", "30.2672"))
WEATHER_LON = float(os.getenv("WEATHER_LON", "-97.7431"))


def get_weather_signal(
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    if USE_MOCK_DATA:
        return _mock.get_weather_signal()

    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": WEATHER_LAT,
            "longitude": WEATHER_LON,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "daily": "temperature_2m_mean,precipitation_sum",
            "timezone": "America/Chicago",
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()["daily"]

        df = pd.DataFrame(
            {
                "date": pd.to_datetime(data["time"]),
                "temp": data["temperature_2m_mean"],
                "precip": data["precipitation_sum"],
            }
        ).set_index("date")

        # Compute z-score anomalies vs the rolling 30-day mean
        df["weather_temp_anomaly"]   = _zscore(df["temp"])
        df["weather_precip_anomaly"] = _zscore(df["precip"])
        df["weather_composite"] = (
            df["weather_temp_anomaly"].abs() + df["weather_precip_anomaly"].abs()
        ) / 2
        return df[["weather_temp_anomaly", "weather_precip_anomaly", "weather_composite"]]

    except Exception:
        return _mock.get_weather_signal()


def _zscore(series: pd.Series, window: int = 30) -> pd.Series:
    mean = series.rolling(window, min_periods=5).mean()
    std  = series.rolling(window, min_periods=5).std().replace(0, 1)
    return ((series - mean) / std).fillna(0)
