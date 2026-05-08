"""Google Trends proxy via pytrends."""

from __future__ import annotations

from datetime import date
import pandas as pd

from config import USE_MOCK_DATA
from mock_data import MockDataGenerator

_mock = MockDataGenerator()

CAMPAIGN_KEYWORDS = {
    "camp_001": ["roof repair", "storm damage roof"],
    "camp_002": ["HVAC installation", "air conditioner replacement"],
    "camp_003": ["home equity loan", "HELOC rates"],
    "camp_004": ["gutter cleaning service"],
    "camp_005": ["lawn care service", "yard maintenance"],
    "camp_006": ["emergency plumber", "plumbing repair"],
    "camp_007": ["window replacement cost", "new windows home"],
}


def get_trends_signal(
    campaign_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    if USE_MOCK_DATA:
        return _mock.get_trends_signal(campaign_id)

    try:
        from pytrends.request import TrendReq
        keywords = CAMPAIGN_KEYWORDS.get(campaign_id, ["home services"])
        timeframe = f"{start_date} {end_date}"

        pt = TrendReq(hl="en-US", tz=360)
        pt.build_payload(keywords[:5], cat=0, timeframe=timeframe, geo="US")
        interest = pt.interest_over_time()

        if interest.empty:
            return _mock.get_trends_signal(campaign_id)

        # Average across keywords, resample to daily
        idx = interest.drop(columns=["isPartial"], errors="ignore")
        daily = idx.mean(axis=1).resample("D").interpolate()
        dates = pd.date_range(start_date, end_date, freq="D")
        daily = daily.reindex(dates).ffill().bfill()

        return pd.DataFrame({"trends_index": daily.values}, index=dates)

    except Exception:
        return _mock.get_trends_signal(campaign_id)
