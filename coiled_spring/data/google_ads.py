"""
Campaign data layer.
Priority order: BigQuery (live client data) → Google Ads API → Mock data.
"""

from __future__ import annotations

from datetime import date
import pandas as pd

from config import (
    GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET,
    GOOGLE_ADS_REFRESH_TOKEN, GOOGLE_ADS_CUSTOMER_ID, USE_MOCK_DATA, USE_BIGQUERY,
)
from mock_data import MockDataGenerator

_mock = MockDataGenerator()


def get_campaigns() -> list[dict]:
    if USE_BIGQUERY:
        from data.bigquery import get_campaigns as bq_campaigns
        return bq_campaigns()
    if USE_MOCK_DATA:
        return _mock.get_campaigns()

    try:
        from google.ads.googleads.client import GoogleAdsClient
        credentials = {
            "developer_token": GOOGLE_ADS_DEVELOPER_TOKEN,
            "client_id": GOOGLE_ADS_CLIENT_ID,
            "client_secret": GOOGLE_ADS_CLIENT_SECRET,
            "refresh_token": GOOGLE_ADS_REFRESH_TOKEN,
            "use_proto_plus": True,
        }
        client = GoogleAdsClient.load_from_dict(credentials)
        ga_service = client.get_service("GoogleAdsService")

        query = """
            SELECT campaign.id, campaign.name
            FROM campaign
            WHERE campaign.status = 'ENABLED'
            ORDER BY campaign.name
        """
        response = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query)
        return [
            {"id": str(row.campaign.id), "name": row.campaign.name}
            for row in response
        ]
    except Exception:
        return _mock.get_campaigns()


def get_campaign_timeseries(
    campaign_id: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    if USE_BIGQUERY:
        from data.bigquery import get_campaign_timeseries as bq_ts
        return bq_ts(campaign_id, start_date, end_date)
    if USE_MOCK_DATA:
        return _mock.get_campaign_timeseries(campaign_id)

    try:
        from google.ads.googleads.client import GoogleAdsClient
        credentials = {
            "developer_token": GOOGLE_ADS_DEVELOPER_TOKEN,
            "client_id": GOOGLE_ADS_CLIENT_ID,
            "client_secret": GOOGLE_ADS_CLIENT_SECRET,
            "refresh_token": GOOGLE_ADS_REFRESH_TOKEN,
            "use_proto_plus": True,
        }
        client = GoogleAdsClient.load_from_dict(credentials)
        ga_service = client.get_service("GoogleAdsService")

        query = f"""
            SELECT
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.cost_micros,
                metrics.search_impression_share,
                metrics.average_cpc
            FROM campaign
            WHERE campaign.id = {campaign_id}
              AND segments.date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY segments.date
        """
        response = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query)

        rows = []
        for row in response:
            m = row.metrics
            impressions = m.impressions
            clicks = m.clicks
            conversions = m.conversions
            cost = m.cost_micros / 1_000_000
            cvr = conversions / clicks if clicks > 0 else 0.0
            rows.append(
                {
                    "date": pd.to_datetime(row.segments.date),
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "cvr": cvr,
                    "cost": cost,
                    "impression_share": m.search_impression_share * 100,
                    "cpc": m.average_cpc / 1_000_000,
                }
            )

        df = pd.DataFrame(rows).set_index("date")
        df.index = pd.DatetimeIndex(df.index)
        return df
    except Exception:
        return _mock.get_campaign_timeseries(campaign_id)
