import os
from dotenv import load_dotenv

load_dotenv()

# ── Google Ads ───────────────────────────────────────────────────────────────
GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
GOOGLE_ADS_CLIENT_ID       = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
GOOGLE_ADS_CLIENT_SECRET   = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
GOOGLE_ADS_REFRESH_TOKEN   = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
GOOGLE_ADS_CUSTOMER_ID     = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")

# ── External Signal APIs ─────────────────────────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
# Open-Meteo is free — no key required

# ── Detection Thresholds ─────────────────────────────────────────────────────
CVR_DROP_THRESHOLD_SD      = 1.5    # standard deviations below baseline to flag
IMPRESSION_FLOOR_PCT       = -0.10  # allow up to -10% impression drop before disqualifying
MIN_SIGNALS_FOR_FLAG       = 1      # at least 1 anomalous external signal required
SPRING_MIN_DURATION_DAYS   = 3      # consecutive flagged days needed for a valid spring
BASELINE_PERIOD_DAYS       = 60     # days used to compute CVR mean/std
DETECTION_WINDOW_DAYS      = 30     # recent days scanned for active springs

# Anomaly thresholds per signal type
SIGNAL_ANOMALY_SD          = 1.5    # weather / economic z-score threshold
NEWS_SCORE_THRESHOLD       = 0.55   # 0–1 composite news intensity threshold
SEASONAL_DEVIATION_PCT     = 0.15   # ±15% deviation from seasonal norm
ECONOMIC_DEVIATION_PCT     = 0.05   # ±5% deviation from economic index baseline

# ── Confidence Scoring ───────────────────────────────────────────────────────
CONFIDENCE_THRESHOLDS = {"high": 3, "medium": 2, "low": 1}

CONFIDENCE_COLORS = {
    "high":   "#10b981",
    "medium": "#f59e0b",
    "low":    "#94a3b8",
}
CONFIDENCE_BG = {
    "high":   "rgba(16,185,129,0.15)",
    "medium": "rgba(245,158,11,0.15)",
    "low":    "rgba(148,163,184,0.12)",
}

# ── Recovery Window Estimates by signal type (min_days, max_days) ────────────
RECOVERY_WINDOWS = {
    "weather":  (3,  14),
    "news":     (7,  30),
    "seasonal": (14, 45),
    "economic": (30, 90),
}

# ── Chart / UI Colors ────────────────────────────────────────────────────────
COLOR_INTENT          = "#3b82f6"
COLOR_CVR             = "#f59e0b"
COLOR_SIGNAL_WEATHER  = "#60a5fa"
COLOR_SIGNAL_NEWS     = "#f472b6"
COLOR_SIGNAL_SEASONAL = "#34d399"
COLOR_SIGNAL_ECONOMIC = "#a78bfa"
COLOR_SPRING_ZONE     = "rgba(245,158,11,0.07)"

CHART_BG       = "#0b0f1a"
CHART_GRID     = "#1e293b"
CHART_TEXT     = "#94a3b8"
CHART_AXIS     = "#334155"

# ── Feature flag ─────────────────────────────────────────────────────────────
USE_MOCK_DATA = not all([
    GOOGLE_ADS_DEVELOPER_TOKEN,
    GOOGLE_ADS_CLIENT_ID,
    GOOGLE_ADS_CLIENT_SECRET,
    GOOGLE_ADS_REFRESH_TOKEN,
    GOOGLE_ADS_CUSTOMER_ID,
])
