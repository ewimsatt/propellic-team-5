"""Dynamic plain-English executive summary generator."""

from __future__ import annotations

from analysis.detection import CoiledSpring


_SIGNAL_PLAIN = {
    "weather":  "severe weather conditions",
    "news":     "elevated news and political activity",
    "seasonal": "predictable seasonal shifts in demand",
    "economic": "broader economic uncertainty",
}

_SIGNAL_CAUSE = {
    "weather":  (
        "When major weather events occur, consumers shift their attention to immediate concerns "
        "rather than making purchase decisions — even when their underlying need remains high."
    ),
    "news":     (
        "During periods of intense news cycles or political events, consumers become distracted "
        "and defer non-urgent decisions, even while their search activity continues."
    ),
    "seasonal": (
        "This is a well-documented seasonal trough for this category — a temporary lull in "
        "purchase behaviour that reliably precedes a seasonal uptick."
    ),
    "economic": (
        "Economic uncertainty is causing consumers to pause before committing, but their "
        "ongoing search activity shows the underlying intent has not disappeared."
    ),
}


def generate_executive_summary(
    springs: list[CoiledSpring],
    kpis: dict,
) -> str:
    if not springs:
        return (
            "All monitored campaigns are currently performing within normal ranges. "
            "No external shocks have been detected that would suggest a temporary conversion dip. "
            "Budgets are working efficiently across the account — no corrective action is recommended at this time."
        )

    high    = [s for s in springs if s.confidence == "high"]
    medium  = [s for s in springs if s.confidence == "medium"]
    count   = len(springs)
    names   = [s.campaign_name for s in springs[:3]]

    # Determine the dominant signal type across all springs
    all_signals: list[str] = []
    for sp in springs:
        all_signals.extend(sp.active_signals)
    if all_signals:
        dominant_signal = max(set(all_signals), key=all_signals.count)
    else:
        dominant_signal = "external factors"

    cause_text = _SIGNAL_CAUSE.get(dominant_signal, "")
    signal_plain = _SIGNAL_PLAIN.get(dominant_signal, dominant_signal)

    # Sentence 1 — what is happening
    names_str = ", ".join(f'"{n}"' for n in names)
    if count > 3:
        names_str += f" and {count - 3} other campaign{'s' if count - 3 > 1 else ''}"

    sentence1 = (
        f"Across the account, {count} campaign{'s are' if count > 1 else ' is'} currently showing "
        f"a pattern where conversion rates have dropped below normal levels while search volume "
        f"and impression share remain stable — a pattern we call a Coiled Spring. "
        f"The affected campaign{'s are' if count > 1 else ' is'}: {names_str}."
    )

    # Sentence 2 — why
    sentence2 = (
        f"This dip appears to be driven primarily by {signal_plain}, not by a loss of consumer demand. "
        + cause_text
    )

    # Sentence 3 — what happens next
    rebound_mins = [s.rebound_min_days for s in springs]
    rebound_maxs = [s.rebound_max_days for s in springs]
    avg_min = round(sum(rebound_mins) / len(rebound_mins))
    avg_max = round(sum(rebound_maxs) / len(rebound_maxs))

    sentence3 = (
        f"Based on historical patterns for this type of disruption, conversion rates typically "
        f"recover to baseline levels within {avg_min}–{avg_max} days once the external pressure "
        f"subsides. {'High' if high else 'Medium'}-confidence signals indicate a rebound is likely."
    )

    # Sentence 4 — recommendation
    total_at_risk = kpis.get("total_spend_at_risk", 0)
    total_uplift  = kpis.get("total_projected_uplift", 0)

    if high:
        action = "maintain or modestly increase"
        reasoning = "cutting spend now would forfeit the recovery conversions that are already coming"
    else:
        action = "maintain"
        reasoning = "pulling budget during a temporary dip risks losing ground to competitors who hold their spend"

    sentence4 = (
        f"The recommendation is to {action} spend across these campaigns over the next {avg_max} days. "
        f"Cutting budget at this moment would be a costly mistake — {reasoning}. "
    )

    if total_at_risk > 0 and total_uplift > 0:
        sentence4 += (
            f"The estimated spend at risk if budgets are cut is ${total_at_risk:,.0f}, "
            f"against a projected recovery uplift of {total_uplift:,.0f} additional conversions."
        )

    return f"{sentence1}\n\n{sentence2}\n\n{sentence3}\n\n{sentence4}"
