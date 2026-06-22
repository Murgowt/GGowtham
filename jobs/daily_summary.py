"""Send daily portfolio summary push to all subscribers.

Run manually: python -m jobs.daily_summary
Railway cron (weekdays 4:30 PM ET): 30 21 * * 1-5
"""

import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brain.daily_summary")


def format_summary(portfolio) -> str:
    pnl = portfolio.total_pnl or 0
    sign = "+" if pnl >= 0 else ""
    return_pct = (
        (pnl / portfolio.total_invested * 100)
        if portfolio.total_invested
        else 0
    )
    return (
        f"Portfolio: ${portfolio.total_value:,.2f} · "
        f"{sign}${pnl:,.2f} ({sign}{return_pct:.1f}%) · "
        f"{len(portfolio.holdings)} holdings"
    )


def main() -> int:
    from config import settings
    from db.database import init_db, list_push_subscriptions
    from integrations.snaptrade import get_portfolio
    from integrations.webpush import is_configured, send_to_subscription

    if not settings.notifications_enabled or not is_configured():
        logger.error("Notifications not configured")
        return 1

    init_db()
    subs = list_push_subscriptions()
    if not subs:
        logger.info("No push subscriptions — skipping")
        return 0

    try:
        portfolio = get_portfolio(force_refresh=True)
    except Exception:
        logger.exception("Failed to fetch portfolio")
        return 1

    body = format_summary(portfolio)
    sent = 0
    for sub in subs:
        if send_to_subscription(sub["subscription_json"], title="Brain", body=body):
            sent += 1

    logger.info("Daily summary sent to %s/%s subscribers", sent, len(subs))
    return 0 if sent > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
