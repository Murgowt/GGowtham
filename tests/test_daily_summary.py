from datetime import timedelta
from unittest.mock import MagicMock, patch

from integrations.app_time import now_app
from integrations.daily_summary import DAILY_SUMMARY_LAST_SENT_KEY, send_daily_summary


def test_daily_summary_rate_limited():
    recent = (now_app() - timedelta(hours=1)).isoformat()
    with (
        patch("integrations.daily_summary.is_configured", return_value=True),
        patch("config.settings.notifications_enabled", True),
        patch("integrations.daily_summary.list_push_subscriptions", return_value=[{"endpoint": "x", "subscription_json": {}}]),
        patch("integrations.daily_summary.get_setting", return_value=recent),
        patch("integrations.daily_summary.get_merged_portfolio") as mock_portfolio,
        patch("integrations.daily_summary.send_to_subscription") as mock_send,
    ):
        result = send_daily_summary()

    assert result["skipped"] is True
    assert result["reason"] == "already_sent_recently"
    assert result["sent"] == 0
    mock_portfolio.assert_not_called()
    mock_send.assert_not_called()


def test_daily_summary_sends_when_not_recent():
    with (
        patch("integrations.daily_summary.is_configured", return_value=True),
        patch("config.settings.notifications_enabled", True),
        patch("integrations.daily_summary.list_push_subscriptions", return_value=[{"endpoint": "x", "subscription_json": {"k": 1}}]),
        patch("integrations.daily_summary.get_setting", return_value=None),
        patch("integrations.daily_summary.set_setting") as mock_set,
        patch("integrations.daily_summary.get_merged_portfolio") as mock_portfolio,
        patch("integrations.daily_summary.send_to_subscription", return_value=True),
    ):
        portfolio = MagicMock()
        portfolio.total_pnl = 100
        portfolio.total_invested = 1000
        portfolio.total_value = 1100
        portfolio.holdings = [1, 2]
        mock_portfolio.return_value = portfolio
        result = send_daily_summary()

    assert result["sent"] == 1
    mock_set.assert_called_once()
    assert mock_set.call_args[0][0] == DAILY_SUMMARY_LAST_SENT_KEY
