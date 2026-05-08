# 🌀 Coiled Spring Opportunity Forecasting Tool

Identify moments where search intent stays high but conversion rates temporarily drop due to external shocks — and give clients data-backed reasons to hold spend instead of cutting it.

---

## What It Does

The tool monitors Google Ads campaigns over a rolling 90-day window and flags **Coiled Spring** opportunities: periods where:

1. **Conversion rate drops** more than 1.5 standard deviations below the campaign's own baseline
2. **Impression share / search volume holds steady or rises** (demand is still there)
3. **At least one external signal is anomalous** in the same window (weather, news, seasonal, economic)

Each flagged period is scored **Low / Medium / High** confidence based on how many signals converge, and a rebound window estimate is projected from historical recovery patterns for that signal type.

---

## Quick Start (Demo Mode — no credentials needed)

```bash
cd coiled_spring
pip install -r requirements.txt
streamlit run app.py
```

The app launches in **Demo Mode** automatically whenever Google Ads credentials are absent. All data is generated from a seeded mock generator — the same realistic coiled spring patterns appear on every run.

---

## Live Mode Setup

Copy `.env.example` → `.env` and fill in your credentials:

```bash
cp .env.example .env
```

### API Keys

| Service | Where to get it | Cost |
|---|---|---|
| **Google Ads API** | [Google Ads API Center](https://developers.google.com/google-ads/api/docs/get-started/introduction) | Free (usage limits apply) |
| **NewsAPI** | [newsapi.org/register](https://newsapi.org/register) | Free tier: 100 req/day |
| **FRED API** | [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html) | Free |
| **Open-Meteo** | No key required | Free |
| **Google Trends** (pytrends) | No key required | Free (rate-limited) |

### Google Ads OAuth setup (5 minutes)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Enable **Google Ads API**
2. Create an OAuth 2.0 credential (Desktop app)
3. Run the Google Ads Python client auth helper to generate a refresh token:
   ```bash
   pip install google-ads
   python -c "from google.ads.googleads.oauth2 import OAuth2Client; ..."
   ```
   Or follow [this guide](https://developers.google.com/google-ads/api/docs/oauth/playground).

---

## Project Structure

```
coiled_spring/
├── app.py                  # Streamlit entry point
├── config.py               # API keys, thresholds, constants
├── mock_data.py            # Seeded mock data generator (demo mode)
├── data/
│   ├── google_ads.py       # Google Ads API — campaign timeseries
│   ├── weather.py          # Open-Meteo weather anomaly signal
│   ├── news.py             # NewsAPI / GDELT news intensity signal
│   ├── economic.py         # FRED consumer confidence + unemployment
│   └── trends.py           # Google Trends search intent proxy
├── analysis/
│   ├── detection.py        # ⭐ Coiled Spring scoring engine
│   ├── correlation.py      # Cross-signal correlation matrix
│   └── forecast.py         # Rebound window + uplift projection
├── ui/
│   ├── components.py       # KPI bar, opportunity cards, badges
│   ├── charts.py           # Plotly chart builders (dark theme)
│   └── executive_summary.py # Plain-English summary generator
├── export/
│   └── pdf_report.py       # PDF generation via reportlab
├── .streamlit/config.toml  # Dark theme config
├── requirements.txt
├── .env.example
└── README.md
```

---

## Detection Logic

The core algorithm in `analysis/detection.py`:

1. **Baseline** — first 60 days of each campaign's data establish the CVR mean and standard deviation
2. **Scan** — the most recent 30 days are scanned for windows where CVR z-score < −1.5
3. **Impression gate** — windows where impression share dropped more than 10% are filtered out (real demand loss, not a spring)
4. **Signal check** — remaining windows are checked against all active external signals
5. **Scoring** — 1 signal = Low, 2 signals = Medium, 3+ signals = High confidence
6. **Rebound estimate** — weather events recover in 3–14 days; economic signals in 30–90 days

---

## PDF Export

Click **Export Report** on the dashboard. Requires `kaleido` for chart-to-PNG conversion:

```bash
pip install kaleido
```

The PDF uses a white/light background (print-friendly) even though the dashboard is dark mode.

---

## Configuration

Key thresholds in `config.py`:

| Constant | Default | Description |
|---|---|---|
| `CVR_DROP_THRESHOLD_SD` | 1.5 | Standard deviations below baseline to flag |
| `IMPRESSION_FLOOR_PCT` | -10% | Max allowed impression drop |
| `BASELINE_PERIOD_DAYS` | 60 | Days used to establish the CVR baseline |
| `DETECTION_WINDOW_DAYS` | 30 | Days scanned for active springs |
| `NEWS_SCORE_THRESHOLD` | 0.55 | News intensity trigger (0–1) |

---

## Hackathon Notes

- All mock campaigns include realistic spring patterns with different confidence levels and signal types
- The detection algorithm is statistically sound and will work on real Google Ads data
- Dark mode is applied via `.streamlit/config.toml` — no manual CSS hacks needed for the theme base
- Charts are Plotly throughout; the PDF renderer switches them to a light background automatically
