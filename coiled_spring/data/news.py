"""News signal integration — tries NewsAPI, falls back to GDELT (free), then mock."""

from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
import requests

from config import NEWS_API_KEY, USE_MOCK_DATA
from mock_data import MockDataGenerator

_mock = MockDataGenerator()


def get_news_signal(
    start_date: date | None = None,
    end_date: date | None = None,
    keywords: list[str] | None = None,
) -> pd.DataFrame:
    if USE_MOCK_DATA:
        return _mock.get_news_signal()

    if NEWS_API_KEY:
        try:
            return _fetch_newsapi(start_date, end_date, keywords or ["economy", "weather", "housing"])
        except Exception:
            pass

    try:
        return _fetch_gdelt(start_date, end_date)
    except Exception:
        return _mock.get_news_signal()


def _fetch_newsapi(start_date: date, end_date: date, keywords: list[str]) -> pd.DataFrame:
    query = " OR ".join(keywords)
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": str(start_date),
        "to": str(end_date),
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 100,
        "apiKey": NEWS_API_KEY,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    articles = resp.json().get("articles", [])

    # Aggregate daily article count → normalise to 0–1 score
    records: dict[str, int] = {}
    for art in articles:
        day = art["publishedAt"][:10]
        records[day] = records.get(day, 0) + 1

    dates = pd.date_range(start_date, end_date, freq="D")
    counts = [records.get(str(d.date()), 0) for d in dates]
    max_count = max(counts) or 1
    scores = [c / max_count for c in counts]
    flags  = [1 if s > 0.55 else 0 for s in scores]

    return pd.DataFrame(
        {"news_score": scores, "news_event_flag": flags},
        index=dates,
    )


def _fetch_gdelt(start_date: date, end_date: date) -> pd.DataFrame:
    """Pull article volume from GDELT 2.0 doc API (free, no key)."""
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": "economy OR housing OR weather disaster",
        "mode": "timelinevolnorm",
        "format": "json",
        "startdatetime": start_date.strftime("%Y%m%d000000"),
        "enddatetime": end_date.strftime("%Y%m%d235959"),
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    timeline = resp.json().get("timeline", [{}])[0].get("data", [])

    records = {item["date"][:8]: item["value"] for item in timeline}
    dates = pd.date_range(start_date, end_date, freq="D")
    values = [records.get(d.strftime("%Y%m%d"), 0) for d in dates]
    max_v = max(values) or 1
    scores = [v / max_v for v in values]
    flags  = [1 if s > 0.55 else 0 for s in scores]

    return pd.DataFrame(
        {"news_score": scores, "news_event_flag": flags},
        index=dates,
    )
