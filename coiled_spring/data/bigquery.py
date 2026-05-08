"""BigQuery data layer — queries propellic-data-lake for real client performance data."""

from __future__ import annotations

import os
from datetime import date
import pandas as pd

from config import BIGQUERY_KEY_PATH, BIGQUERY_PROJECT_ID


def _client():
    import google.cloud.bigquery as bigquery
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = BIGQUERY_KEY_PATH
    return bigquery.Client(project=BIGQUERY_PROJECT_ID)


def get_campaigns() -> list[dict]:
    """Return one entry per active Propellic client account."""
    bq = _client()
    query = """
        SELECT
            CAST(customer_id AS STRING)         AS id,
            customer_descriptive_name           AS name,
            MAX(segments_date)                  AS latest_date
        FROM `propellic-data-lake.raw_google_ads.account_performance_report`
        WHERE customer_manager = FALSE
          AND customer_test_account = FALSE
        GROUP BY 1, 2
        ORDER BY name
    """
    rows = list(bq.query(query).result())
    return [{"id": r.id, "name": r.name} for r in rows]


def get_data_date_range() -> tuple[date, date]:
    """Return the actual min/max date available in the database."""
    bq = _client()
    query = """
        SELECT MIN(segments_date) AS min_date, MAX(segments_date) AS max_date
        FROM `propellic-data-lake.raw_google_ads.account_performance_report`
        WHERE customer_manager = FALSE
    """
    rows = list(bq.query(query).result())
    row = rows[0]
    return row.min_date, row.max_date


def get_campaign_timeseries(
    campaign_id: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """
    Return daily aggregated performance for one client account.
    Aggregates across devices so each date is a single row.
    """
    bq = _client()
    query = f"""
        SELECT
            segments_date                                               AS date,
            SUM(metrics_impressions)                                    AS impressions,
            SUM(metrics_clicks)                                         AS clicks,
            SUM(metrics_conversions)                                    AS conversions,
            SAFE_DIVIDE(SUM(metrics_conversions), SUM(metrics_clicks))  AS cvr,
            SUM(metrics_cost_micros) / 1000000                          AS cost,
            AVG(metrics_search_impression_share) * 100                  AS impression_share,
            SAFE_DIVIDE(
                SUM(metrics_cost_micros) / 1000000,
                NULLIF(SUM(metrics_clicks), 0)
            )                                                           AS cpc
        FROM `propellic-data-lake.raw_google_ads.account_performance_report`
        WHERE customer_id = {campaign_id}
          AND segments_date BETWEEN '{start_date}' AND '{end_date}'
          AND customer_manager = FALSE
        GROUP BY segments_date
        ORDER BY segments_date
    """
    rows = list(bq.query(query).result())
    if not rows:
        return pd.DataFrame(
            columns=["impressions", "clicks", "conversions", "cvr",
                     "cost", "impression_share", "cpc"]
        )

    df = pd.DataFrame(
        [
            {
                "date":             r.date,
                "impressions":      r.impressions or 0,
                "clicks":           r.clicks or 0,
                "conversions":      float(r.conversions or 0),
                "cvr":              float(r.cvr or 0),
                "cost":             float(r.cost or 0),
                "impression_share": float(r.impression_share or 0),
                "cpc":              float(r.cpc or 0),
            }
            for r in rows
        ]
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    # Fill any date gaps so the detection window has a continuous series
    full_index = pd.date_range(start_date, end_date, freq="D")
    df = df.reindex(full_index).ffill().fillna(0)

    return df
