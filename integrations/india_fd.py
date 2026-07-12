"""Fixed deposit valuation for Indian banks (HDFC-style premature rules)."""

from __future__ import annotations

from datetime import date
from math import pow


def _elapsed_years(start: date, as_of: date) -> float:
    days = max(0, (as_of - start).days)
    return days / 365.25


def on_track_value(
    principal: float,
    rate_pct: float,
    start_date: date,
    as_of: date,
    *,
    maturity_date: date | None = None,
    compounding: str = "quarterly",
) -> float:
    """Value if FD stays on contracted rate through as_of (capped at maturity)."""
    if as_of <= start_date:
        return round(principal, 2)

    end = as_of
    if maturity_date and as_of > maturity_date:
        end = maturity_date

    years = _elapsed_years(start_date, end)
    if years <= 0:
        return round(principal, 2)

    rate = rate_pct / 100.0
    if compounding == "maturity":
        value = principal * (1 + rate * years)
    else:
        # Quarterly compounding (HDFC default for regular FDs).
        value = principal * pow(1 + rate / 4, 4 * years)
    return round(value, 2)


def close_today_value(
    principal: float,
    rate_pct: float,
    start_date: date,
    as_of: date,
    *,
    penalty_pct: float = 1.0,
) -> float:
    """Estimated payout on premature withdrawal today (HDFC-style approximation)."""
    days = (as_of - start_date).days
    if days < 7:
        return round(principal, 2)

    effective_rate = max(0.0, rate_pct - penalty_pct) / 100.0
    years = _elapsed_years(start_date, as_of)
    value = principal * (1 + effective_rate * years)
    return round(value, 2)


def fd_valuation(
    *,
    principal: float,
    rate_pct: float,
    start_date: date,
    maturity_date: date,
    as_of: date,
    compounding: str = "quarterly",
    penalty_pct: float = 1.0,
) -> dict:
    on_track = on_track_value(
        principal,
        rate_pct,
        start_date,
        as_of,
        maturity_date=maturity_date,
        compounding=compounding,
    )
    close_today = close_today_value(
        principal,
        rate_pct,
        start_date,
        as_of,
        penalty_pct=penalty_pct,
    )
    if as_of >= maturity_date:
        close_today = on_track

    return {
        "on_track_inr": on_track,
        "close_today_inr": close_today,
        "maturity_date": maturity_date.isoformat(),
    }
