"""Monthly spend history (6th-to-6th billing periods)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from integrations.app_time import app_midnight, now_app
from db.database import get_spending_exclusion_ids
from integrations import plaid_client, splitwise_client
from integrations.spending import (
    HISTORY_EPOCH,
    _parse_date,
    _period_label,
    _txn_amount,
    compute_period_spend,
    iter_billing_periods,
    resolve_spending_transactions,
)


def _period_key(period_start: datetime) -> str:
    return period_start.date().isoformat()


def _resolve_period(period_key: str, now: datetime) -> tuple[datetime, datetime] | None:
    try:
        requested = app_midnight(*map(int, period_key.split("-")))
    except ValueError:
        return None

    if requested < HISTORY_EPOCH:
        return None

    for start, end in iter_billing_periods(HISTORY_EPOCH, now):
        if start.date() == requested.date():
            return start, end
    return None


def _period_date_bounds(period_start: datetime, period_end: datetime) -> tuple[date, date]:
    """Inclusive calendar dates for Plaid/Splitwise API calls."""
    last_day = period_end - timedelta(days=1)
    return period_start.date(), last_day.date()


def _fetch_period_transactions(
    period_start: datetime,
    period_end: datetime,
) -> list[dict]:
    range_start, range_end = _period_date_bounds(period_start, period_end)
    plaid_txns: list[dict] = []
    splitwise_txns: list[dict] = []

    if plaid_client.has_connection():
        try:
            plaid_txns = plaid_client.fetch_plaid_transactions_between(
                start=range_start,
                end=range_end,
            )
        except Exception:
            pass

    if splitwise_client.is_configured():
        try:
            splitwise_txns = splitwise_client.fetch_expenses_between(
                start=range_start,
                end=range_end,
            )
        except Exception:
            pass

    merged: list[dict] = []
    seen: set[str] = set()
    for txn in plaid_txns + splitwise_txns:
        if txn["id"] in seen:
            continue
        seen.add(txn["id"])
        merged.append(txn)
    return resolve_spending_transactions(merged)


def _public_period_txn(txn: dict) -> dict:
    skip = {
        "paid_share", "owed_share", "expense_cost", "hidden", "effective_amount",
        "settlement_direction", "net_balance", "original_description", "merchant_name",
        "pending_transaction_id", "counterparties", "plaid_category_primary",
        "plaid_category_detailed",
    }
    if txn.get("hidden"):
        return {}
    row = {k: v for k, v in txn.items() if k not in skip}
    effective = txn.get("effective_amount", txn["amount"])
    if effective != txn.get("amount"):
        row["amount"] = effective
    return row


def get_spending_history(*, now: datetime | None = None) -> dict:
    """Return billing period labels only — no transaction fetch or totals."""
    now = now or now_app()
    periods = []

    for period_start, period_end in iter_billing_periods(HISTORY_EPOCH, now):
        periods.append({
            "key": _period_key(period_start),
            "label": _period_label(period_start, period_end),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "is_current": period_end > now >= period_start,
        })

    periods.reverse()

    return {
        "periods": periods,
        "history_start": HISTORY_EPOCH.date().isoformat(),
        "period_start_day": settings.spending_period_start_day,
        "updated_at": now.isoformat(),
    }


def get_spending_history_period(period_key: str, *, now: datetime | None = None) -> dict | None:
    now = now or now_app()
    matched = _resolve_period(period_key, now)
    if not matched:
        return None

    period_start, period_end = matched
    transactions = _fetch_period_transactions(period_start, period_end)
    excluded_ids = frozenset(get_spending_exclusion_ids())
    spend = compute_period_spend(
        transactions, period_start, period_end, excluded_ids=excluded_ids,
    )

    period_txns = []
    for t in transactions:
        if not (period_start <= _parse_date(t["date"]) < period_end):
            continue
        row = _public_period_txn(t)
        if not row or _txn_amount(t) == 0:
            continue
        if t.get("txn_type") in ("transfer", "cc_payment"):
            continue
        row["excluded_from_total"] = t.get("id") in excluded_ids
        period_txns.append(row)
    period_txns.sort(key=lambda t: t["date"], reverse=True)

    return {
        "key": _period_key(period_start),
        "label": _period_label(period_start, period_end),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "spend": spend,
        "transactions": period_txns,
        "excluded_ids": sorted(excluded_ids),
        "updated_at": now.isoformat(),
    }
