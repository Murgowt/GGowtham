import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from config import settings
from db.database import get_latest_spending_snapshot, get_plaid_institution_logos, save_spending_snapshot
from integrations import plaid_client, splitwise_client
from integrations.medium import resolve_medium

logger = logging.getLogger(__name__)

OVERLAP_MATCH_DAYS = 5
OVERLAP_AMOUNT_TOLERANCE = 1.0

MOCK_TRANSACTIONS = [
    {
        "id": "mock:1",
        "source": "bank",
        "date": "",
        "amount": 3200.00,
        "currency": "USD",
        "description": "Direct deposit · Acme Corp",
        "account_name": "Chase Checking",
        "category": "Income",
    },
    {
        "id": "mock:2",
        "source": "card",
        "date": "",
        "amount": -42.50,
        "currency": "USD",
        "description": "Whole Foods Market",
        "account_name": "Amex Gold",
        "category": "Groceries",
    },
    {
        "id": "mock:3",
        "source": "splitwise",
        "date": "",
        "amount": -800.00,
        "currency": "USD",
        "description": "June rent split",
        "account_name": "Splitwise · Roommates",
        "category": "Rent",
    },
    {
        "id": "mock:4",
        "source": "card",
        "date": "",
        "amount": -18.75,
        "currency": "USD",
        "description": "Uber Eats",
        "account_name": "Amex Gold",
        "category": "Food and Drink",
    },
]


@dataclass
class SpendingData:
    transactions: list[dict]
    summary: dict
    cached: bool
    updated_at: datetime
    source: str


def _period_bounds(now: datetime) -> tuple[datetime, datetime]:
    start_day = settings.spending_period_start_day
    if now.day >= start_day:
        period_start = now.replace(day=start_day, hour=0, minute=0, second=0, microsecond=0)
    elif now.month == 1:
        period_start = now.replace(
            year=now.year - 1, month=12, day=start_day,
            hour=0, minute=0, second=0, microsecond=0,
        )
    else:
        period_start = now.replace(
            month=now.month - 1, day=start_day,
            hour=0, minute=0, second=0, microsecond=0,
        )

    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1, day=start_day)
    else:
        period_end = period_start.replace(month=period_start.month + 1, day=start_day)

    return period_start, period_end


def _period_label(period_start: datetime, period_end: datetime) -> str:
    last_day = period_end - timedelta(days=1)
    return f"{period_start.strftime('%b')} {period_start.day} – {last_day.strftime('%b')} {last_day.day}, {last_day.year}"


def _amounts_match(a: float, b: float) -> bool:
    if b == 0:
        return a == 0
    return abs(a - b) <= max(OVERLAP_AMOUNT_TOLERANCE, 0.01 * b)


def resolve_splitwise_overlaps(transactions: list[dict]) -> list[dict]:
    """Match Splitwise shares to card/bank charges so shared expenses count once."""
    txns = [dict(t) for t in transactions]

    splitwise = [t for t in txns if t.get("source") == "splitwise" and t.get("amount", 0) < 0]
    charges = [t for t in txns if t.get("source") in ("card", "bank") and t.get("amount", 0) < 0]
    matched_charges: set[str] = set()

    for sw in splitwise:
        owed = abs(sw.get("amount", 0))
        paid = sw.get("paid_share", 0)
        cost = sw.get("expense_cost", 0)
        sw_dt = datetime.fromisoformat(sw["date"])

        if paid <= 0:
            sw["effective_amount"] = sw["amount"]
            continue

        match = None
        for charge in charges:
            if charge["id"] in matched_charges:
                continue
            charge_amt = abs(charge["amount"])
            charge_dt = datetime.fromisoformat(charge["date"])
            if abs((charge_dt - sw_dt).days) > OVERLAP_MATCH_DAYS:
                continue
            if _amounts_match(charge_amt, paid) or (cost > 0 and _amounts_match(charge_amt, cost)):
                match = charge
                break

        if match:
            matched_charges.add(match["id"])
            match["effective_amount"] = round(-owed, 2)
            match["overlap_resolved"] = True
            sw["effective_amount"] = 0
            sw["hidden"] = True
        else:
            sw["effective_amount"] = round(-owed, 2)

    for txn in txns:
        if "effective_amount" not in txn:
            txn["effective_amount"] = txn.get("amount", 0)

    return txns


def _txn_amount(txn: dict) -> float:
    return txn.get("effective_amount", txn["amount"])


def _public_transactions(transactions: list[dict]) -> list[dict]:
    public: list[dict] = []
    skip_keys = {"paid_share", "expense_cost", "hidden", "overlap_resolved", "effective_amount"}

    for txn in transactions:
        if txn.get("hidden"):
            continue
        row = {k: v for k, v in txn.items() if k not in skip_keys}
        effective = txn.get("effective_amount", txn["amount"])
        if effective != txn.get("amount"):
            row["amount"] = effective
        public.append(row)

    return public


def compute_summary(transactions: list[dict], *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    period_start, period_end = _period_bounds(now)

    period_txns = [
        t for t in transactions
        if period_start <= datetime.fromisoformat(t["date"]) < period_end
    ]

    outflow = sum(abs(_txn_amount(t)) for t in period_txns if _txn_amount(t) < 0)
    inflow = sum(_txn_amount(t) for t in period_txns if _txn_amount(t) > 0)

    by_source = {"bank": 0.0, "card": 0.0, "splitwise": 0.0}
    for t in period_txns:
        amt = _txn_amount(t)
        if amt >= 0:
            continue
        src = t.get("source", "bank")
        if src in by_source:
            by_source[src] += abs(amt)

    return {
        "month_outflow": round(outflow, 2),
        "month_inflow": round(inflow, 2),
        "month_net": round(inflow - outflow, 2),
        "transaction_count": len(transactions),
        "month_transaction_count": len(period_txns),
        "by_source": {k: round(v, 2) for k, v in by_source.items()},
        "month_label": _period_label(period_start, period_end),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "overlaps_resolved": sum(1 for t in transactions if t.get("overlap_resolved")),
    }


def _fetch_days(now: datetime, default_days: int) -> int:
    period_start, _ = _period_bounds(now)
    needed = (now - period_start).days + OVERLAP_MATCH_DAYS + 1
    return max(default_days, needed)


def _snapshot_to_spending(snapshot) -> SpendingData:
    captured = snapshot.captured_at
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=timezone.utc)
    transactions = snapshot.transactions_json or []
    resolved = resolve_splitwise_overlaps(transactions)
    summary = compute_summary(resolved, now=captured)
    return SpendingData(
        transactions=_public_transactions(resolved),
        summary=summary,
        cached=True,
        updated_at=captured,
        source="snapshot",
    )


_cache: SpendingData | None = None
_cache_at: datetime | None = None


def invalidate_spending_cache() -> None:
    global _cache, _cache_at
    _cache = None
    _cache_at = None


def _dedupe_and_sort(transactions: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for txn in transactions:
        if txn["id"] in seen:
            continue
        seen.add(txn["id"])
        unique.append(txn)
    unique.sort(key=lambda t: t["date"], reverse=True)
    return unique


def _fetch_splitwise(*, days: int) -> list[dict]:
    if not splitwise_client.is_configured():
        return []
    try:
        return splitwise_client.fetch_expenses(days=days)
    except Exception:
        logger.exception("Splitwise fetch failed")
        return []


def _build_spending(
    plaid_txns: list[dict],
    splitwise_txns: list[dict],
    *,
    now: datetime,
    source: str,
    cached: bool = False,
) -> SpendingData:
    unique = _dedupe_and_sort(plaid_txns + splitwise_txns)
    resolved = resolve_splitwise_overlaps(unique)
    summary = compute_summary(resolved, now=now)
    visible = _public_transactions(resolved)
    if not visible and source == "live":
        source = "empty"
    return SpendingData(
        transactions=visible,
        summary=summary,
        cached=cached,
        updated_at=now,
        source=source,
    )


def _mock_spending(*, days: int) -> SpendingData:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    txns = []
    for i, template in enumerate(MOCK_TRANSACTIONS):
        dt = now - timedelta(days=i * 3 + 1)
        medium = resolve_medium(
            source=template["source"],
            account_name=template.get("account_name"),
        )
        txn = {**template, **medium, "date": dt.isoformat()}
        if dt >= cutoff:
            txns.append(txn)

    txns.sort(key=lambda t: t["date"], reverse=True)
    resolved = resolve_splitwise_overlaps(txns)
    summary = compute_summary(resolved, now=now)
    return SpendingData(
        transactions=_public_transactions(resolved),
        summary=summary,
        cached=False,
        updated_at=now,
        source="mock",
    )


def _fetch_live(*, days: int, splitwise_txns: list[dict] | None = None) -> SpendingData:
    now = datetime.now(timezone.utc)
    plaid_txns: list[dict] = []

    try:
        plaid_txns = plaid_client.fetch_plaid_transactions(days=days, force_refresh=True)
    except Exception:
        logger.exception("Plaid fetch failed")

    if splitwise_txns is None:
        splitwise_txns = _fetch_splitwise(days=days)
    result = _build_spending(plaid_txns, splitwise_txns, now=now, source="live")
    save_spending_snapshot(result.transactions, result.summary)
    return result


def get_spending_logos() -> dict[str, str]:
    return get_plaid_institution_logos()


def get_spending_status() -> dict:
    return {
        "plaid_configured": plaid_client.is_configured(),
        "plaid_connected": plaid_client.has_connection(),
        "splitwise_configured": splitwise_client.is_configured(),
        "accounts": plaid_client.list_connected_accounts(),
        "mock": settings.mock_integrations,
    }


def get_spending(*, force_refresh: bool = False, days: int = 30) -> SpendingData:
    global _cache, _cache_at

    if settings.mock_integrations:
        return _mock_spending(days=days)

    now = datetime.now(timezone.utc)
    cache_ttl = timedelta(minutes=settings.spending_cache_minutes)
    days = _fetch_days(now, days)

    if force_refresh:
        invalidate_spending_cache()

    splitwise_txns = _fetch_splitwise(days=days)

    if not force_refresh and _cache and _cache_at and (now - _cache_at) < cache_ttl:
        plaid_txns = [t for t in _cache.transactions if t.get("source") != "splitwise"]
        result = _build_spending(plaid_txns, splitwise_txns, now=now, source="live", cached=True)
        _cache = result
        _cache_at = now
        return result

    has_any_source = plaid_client.has_connection() or splitwise_client.is_configured()
    if not has_any_source:
        snapshot = get_latest_spending_snapshot()
        if snapshot:
            return _snapshot_to_spending(snapshot)
        return SpendingData(
            transactions=[],
            summary=compute_summary([]),
            cached=False,
            updated_at=now,
            source="empty",
        )

    live = _fetch_live(days=days, splitwise_txns=splitwise_txns)
    _cache = live
    _cache_at = now
    return live
