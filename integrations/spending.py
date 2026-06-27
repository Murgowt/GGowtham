import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from config import settings
from db.database import get_latest_spending_snapshot, get_plaid_institution_logos, save_spending_snapshot
from integrations import plaid_client, splitwise_client
from integrations.medium import resolve_medium

logger = logging.getLogger(__name__)

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


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def compute_summary(transactions: list[dict], *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    month_start = _month_start(now)

    month_txns = [
        t for t in transactions
        if datetime.fromisoformat(t["date"]) >= month_start
    ]

    outflow = sum(abs(t["amount"]) for t in month_txns if t["amount"] < 0)
    inflow = sum(t["amount"] for t in month_txns if t["amount"] > 0)

    by_source = {"bank": 0.0, "card": 0.0, "splitwise": 0.0}
    for t in month_txns:
        if t["amount"] >= 0:
            continue
        src = t.get("source", "bank")
        if src in by_source:
            by_source[src] += abs(t["amount"])

    return {
        "month_outflow": round(outflow, 2),
        "month_inflow": round(inflow, 2),
        "month_net": round(inflow - outflow, 2),
        "transaction_count": len(transactions),
        "month_transaction_count": len(month_txns),
        "by_source": {k: round(v, 2) for k, v in by_source.items()},
        "month_label": month_start.strftime("%B %Y"),
    }


def _snapshot_to_spending(snapshot) -> SpendingData:
    captured = snapshot.captured_at
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=timezone.utc)
    transactions = snapshot.transactions_json or []
    summary = snapshot.summary_json or compute_summary(transactions, now=captured)
    return SpendingData(
        transactions=transactions,
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
    summary = compute_summary(unique, now=now)
    if not unique and source == "live":
        source = "empty"
    return SpendingData(
        transactions=unique,
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
    summary = compute_summary(txns, now=now)
    return SpendingData(
        transactions=txns,
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
