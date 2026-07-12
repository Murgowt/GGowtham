"""Tests for India FD valuation."""

from datetime import date

from integrations.india_fd import close_today_value, fd_valuation, on_track_value


def test_fd_no_interest_within_seven_days():
    start = date(2025, 1, 1)
    as_of = date(2025, 1, 5)
    assert close_today_value(100_000, 7.0, start, as_of) == 100_000


def test_fd_on_track_grows_with_compounding():
    start = date(2024, 1, 1)
    as_of = date(2025, 1, 1)
    value = on_track_value(100_000, 7.0, start, as_of, compounding="quarterly")
    assert value > 100_000
    assert value < 108_000


def test_fd_close_today_lower_than_on_track():
    start = date(2024, 1, 1)
    maturity = date(2026, 1, 1)
    as_of = date(2025, 1, 1)
    result = fd_valuation(
        principal=100_000,
        rate_pct=7.0,
        start_date=start,
        maturity_date=maturity,
        as_of=as_of,
    )
    assert result["close_today_inr"] < result["on_track_inr"]


def test_fd_at_maturity_uses_on_track_for_close():
    start = date(2024, 1, 1)
    maturity = date(2025, 1, 1)
    as_of = date(2025, 6, 1)
    result = fd_valuation(
        principal=100_000,
        rate_pct=7.0,
        start_date=start,
        maturity_date=maturity,
        as_of=as_of,
    )
    assert result["close_today_inr"] == result["on_track_inr"]
