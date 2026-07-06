from datetime import date, datetime, timezone

from integrations.splitwise_client import _splitwise_dated_after, _splitwise_dated_before


def test_splitwise_dated_before_includes_late_central_evening_on_utc_next_day():
    """Central evening expenses can have a UTC date of the next calendar day."""
    # Jul 5 9:13 PM Central (CDT) = Jul 6 02:13 UTC — must be included when end=Jul 5 Central.
    end = date(2026, 7, 5)
    dated_before = _splitwise_dated_before(end)

    assert dated_before == "2026-07-06T05:00:00Z"

    expense_utc = datetime(2026, 7, 6, 2, 13, 55, tzinfo=timezone.utc)
    bound = datetime.fromisoformat(dated_before.replace("Z", "+00:00"))
    assert expense_utc < bound


def test_splitwise_dated_after_uses_central_midnight():
    start = date(2026, 6, 6)
    assert _splitwise_dated_after(start) == "2026-06-06T05:00:00Z"
