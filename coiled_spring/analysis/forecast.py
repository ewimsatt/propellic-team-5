"""Rebound window estimation and uplift projection."""

from __future__ import annotations

from analysis.detection import CoiledSpring
from config import RECOVERY_WINDOWS


def estimate_rebound_window(
    signals: list[str],
    historical_outcomes: list[dict] | None = None,
) -> tuple[int, int]:
    """
    Estimate (min_days, max_days) for recovery based on signal types.
    If historical outcomes are provided, adjusts the estimate based on past data.
    """
    if not signals:
        return (7, 30)

    base_min = min(RECOVERY_WINDOWS.get(s, (7, 30))[0] for s in signals)
    base_max = max(RECOVERY_WINDOWS.get(s, (7, 30))[1] for s in signals)

    if not historical_outcomes:
        return (base_min, base_max)

    # Filter to matching signal types and rebounded outcomes
    matching = [
        h for h in historical_outcomes
        if h.get("signal") in signals
        and h.get("outcome") == "rebounded"
        and h.get("actual_days") is not None
    ]
    if len(matching) >= 2:
        actual_days = [h["actual_days"] for h in matching]
        hist_min = int(min(actual_days) * 0.9)
        hist_max = int(max(actual_days) * 1.1)
        # Blend with prior
        blended_min = round((base_min + hist_min) / 2)
        blended_max = round((base_max + hist_max) / 2)
        return (blended_min, blended_max)

    return (base_min, base_max)


def project_recovery_uplift(spring: CoiledSpring) -> dict:
    """
    Returns a dict with spend_at_risk, projected_conversions_gained,
    and projected_revenue_uplift (assuming $50 avg conversion value).
    """
    avg_conversion_value = 50.0  # placeholder — should come from Google Ads config

    midpoint_days = (spring.rebound_min_days + spring.rebound_max_days) / 2

    daily_clicks = spring.campaign_df["clicks"].iloc[-7:].mean()
    cvr_gap = spring.cvr_baseline - spring.cvr_current
    projected_additional_conversions = daily_clicks * cvr_gap * midpoint_days
    projected_revenue = projected_additional_conversions * avg_conversion_value

    daily_spend = spring.campaign_df["cost"].iloc[-7:].mean()
    spend_at_risk = daily_spend * midpoint_days

    return {
        "spend_at_risk":     round(spend_at_risk, 2),
        "additional_conversions": round(max(projected_additional_conversions, 0), 1),
        "revenue_uplift":    round(max(projected_revenue, 0), 2),
        "midpoint_days":     round(midpoint_days, 1),
    }
