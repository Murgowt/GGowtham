import logging

from db.database import list_push_subscriptions
from integrations.snaptrade import get_portfolio
from integrations.webpush import is_configured, send_to_subscription

logger = logging.getLogger(__name__)


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


def send_daily_summary() -> dict:
    from config import settings

    if not settings.notifications_enabled or not is_configured():
        raise RuntimeError("Push notifications are not configured")

    subs = list_push_subscriptions()
    if not subs:
        logger.info("No push subscriptions — skipping daily summary")
        return {"sent": 0, "total": 0, "skipped": True}

    portfolio = get_portfolio(force_refresh=True)
    body = format_summary(portfolio)

    sent = 0
    for sub in subs:
        if send_to_subscription(sub["subscription_json"], title="Brain", body=body):
            sent += 1

    logger.info("Daily summary sent to %s/%s subscribers", sent, len(subs))
    return {"sent": sent, "total": len(subs), "body": body}
