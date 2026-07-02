"""Push alerts when new card purchases or Splitwise splits affect the budget."""

from __future__ import annotations

import logging

from config import settings
from db.database import get_spending_alert_keys, list_push_subscriptions, mark_spending_alerts_sent
from integrations.spending import get_spending
from integrations.webpush import is_configured, send_to_subscription

logger = logging.getLogger(__name__)


def spending_alert_key(txn: dict) -> str:
    """Stable id so pending card auths don't re-alert when they post."""
    if txn.get("source") in ("bank", "card"):
        pending_ref = txn.get("pending_transaction_id")
        if pending_ref:
            return f"plaid:{pending_ref}"
        return str(txn.get("id") or "")
    return str(txn.get("id") or "")


def format_spending_alert_body(txn: dict, budget_remaining: float) -> str:
    desc = (txn.get("description") or "Expense").strip()
    if len(desc) > 36:
        desc = desc[:33] + "…"
    amount = float(txn.get("amount") or 0)
    if amount > 0:
        amt_str = f"+${amount:,.2f}"
    else:
        amt_str = f"−${abs(amount):,.2f}"
    pending = " · pending" if txn.get("pending") else ""
    return f"{desc} {amt_str}{pending} · ${budget_remaining:,.0f} left"


def _alertable_transactions(transactions: list[dict]) -> list[dict]:
    return [
        t for t in transactions
        if not t.get("excluded_from_total")
        and (
            (t.get("source") == "splitwise" and t.get("txn_type") == "share")
            or (t.get("source") == "card" and float(t.get("amount") or 0) < 0)
        )
    ]


def check_and_send_spending_alerts(*, bootstrap_if_empty: bool = True) -> dict:
    """
    Poll spending, notify on new card charges and Splitwise splits.

    First run seeds existing transactions without notifying (no flood on deploy).
    """
    if not settings.notifications_enabled or not is_configured():
        raise RuntimeError("Push notifications are not configured")

    subs = list_push_subscriptions()
    if not subs:
        return {"sent": 0, "total": 0, "skipped": True, "new": 0}

    try:
        data = get_spending(force_refresh=True)
    except Exception:
        logger.exception("Spending refresh failed for alerts")
        raise

    summary = data.summary or {}
    budget_remaining = float(summary.get("budget_remaining") or 0)
    alertable = _alertable_transactions(data.transactions or [])
    seen = get_spending_alert_keys()

    keys_now = [spending_alert_key(t) for t in alertable if spending_alert_key(t)]
    new_keys = [k for k in keys_now if k and k not in seen]

    if bootstrap_if_empty and not seen and keys_now:
        mark_spending_alerts_sent(keys_now)
        logger.info("Spending alerts bootstrapped %s existing transactions", len(keys_now))
        return {
            "sent": 0,
            "total": len(subs),
            "new": 0,
            "bootstrapped": len(keys_now),
        }

    if not new_keys:
        return {"sent": 0, "total": len(subs), "new": 0}

    key_to_txn = {spending_alert_key(t): t for t in alertable if spending_alert_key(t)}
    sent_total = 0
    delivered_keys: list[str] = []

    for key in new_keys:
        txn = key_to_txn.get(key)
        if not txn:
            continue
        body = format_spending_alert_body(txn, budget_remaining)
        title = "Brain · Spend"
        for sub in subs:
            if send_to_subscription(
                sub["subscription_json"],
                title=title,
                body=body,
                url="/?tab=spend",
            ):
                sent_total += 1
        delivered_keys.append(key)

    if delivered_keys:
        mark_spending_alerts_sent(delivered_keys)

    logger.info(
        "Spending alerts: %s new, %s push deliveries to %s subscribers",
        len(delivered_keys),
        sent_total,
        len(subs),
    )
    return {
        "sent": sent_total,
        "total": len(subs),
        "new": len(delivered_keys),
        "budget_remaining": budget_remaining,
    }
