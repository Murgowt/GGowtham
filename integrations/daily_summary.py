import logging
from datetime import datetime, timedelta, timezone

from db.database import get_setting, list_push_subscriptions, set_setting
from integrations.snaptrade import get_portfolio
from integrations.webpush import is_configured, send_to_subscription

logger = logging.getLogger(__name__)

DAILY_SUMMARY_LAST_SENT_KEY = "daily_summary_last_sent_at"
DAILY_SUMMARY_MIN_INTERVAL = timedelta(hours=20)


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


def _send_to_all(title: str, body: str) -> dict:
    subs = list_push_subscriptions()
    if not subs:
        logger.info("No push subscriptions")
        return {"sent": 0, "total": 0, "skipped": True}

    sent = 0
    for sub in subs:
        if send_to_subscription(sub["subscription_json"], title=title, body=body):
            sent += 1

    return {"sent": sent, "total": len(subs), "body": body}


def send_cron_test() -> dict:
    from config import settings

    if not settings.notifications_enabled or not is_configured():
        raise RuntimeError("Push notifications are not configured")

    result = _send_to_all("Brain", "Scheduled notification is working.")
    logger.info("Cron test sent to %s/%s subscribers", result["sent"], result["total"])
    return result


def send_daily_summary(*, force: bool = False) -> dict:
    from config import settings

    if not settings.notifications_enabled or not is_configured():
        raise RuntimeError("Push notifications are not configured")

    subs = list_push_subscriptions()
    if not subs:
        logger.info("No push subscriptions — skipping daily summary")
        return {"sent": 0, "total": 0, "skipped": True}

    now = datetime.now(timezone.utc)
    if not force:
        last_raw = get_setting(DAILY_SUMMARY_LAST_SENT_KEY)
        if last_raw:
            try:
                last_sent = datetime.fromisoformat(last_raw)
                if last_sent.tzinfo is None:
                    last_sent = last_sent.replace(tzinfo=timezone.utc)
                if now - last_sent < DAILY_SUMMARY_MIN_INTERVAL:
                    logger.info(
                        "Daily summary skipped — last sent %s (min interval %sh)",
                        last_sent.isoformat(),
                        int(DAILY_SUMMARY_MIN_INTERVAL.total_seconds() // 3600),
                    )
                    return {
                        "sent": 0,
                        "total": len(subs),
                        "skipped": True,
                        "reason": "already_sent_recently",
                    }
            except ValueError:
                pass

    body = None
    try:
        portfolio = get_portfolio(force_refresh=True)
        body = format_summary(portfolio)
    except Exception:
        logger.warning("Live portfolio refresh failed, trying cached data", exc_info=True)
        try:
            portfolio = get_portfolio(force_refresh=False)
            body = format_summary(portfolio)
        except Exception:
            logger.warning("Cached portfolio failed, sending generic message", exc_info=True)
            body = "Your portfolio was updated — open Brain to view."

    sent = 0
    for sub in subs:
        if send_to_subscription(sub["subscription_json"], title="Brain", body=body):
            sent += 1

    if sent:
        set_setting(DAILY_SUMMARY_LAST_SENT_KEY, now.isoformat())

    logger.info("Daily summary sent to %s/%s subscribers", sent, len(subs))
    return {"sent": sent, "total": len(subs), "body": body}
