import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from config import settings
from db.database import get_latest_spending_snapshot, get_plaid_institution_logos, save_spending_snapshot
from integrations import plaid_client, splitwise_client
from integrations.medium import resolve_medium

logger = logging.getLogger(__name__)

CARD_MATCH_DAYS = 21
SETTLEMENT_MATCH_DAYS = 7
AMOUNT_TOLERANCE = 1.0
BUNDLE_TOLERANCE = 2.0

ROBINHOOD_MARKERS = (
    "robinhood",
    "robin hood",
    "rh securities",
    "rh secu",
    "robinhood securities",
    "robinhood markets",
    "robinhood debit",
)

INVESTMENT_PLAID_DETAILED = {
    "TRANSFER_OUT_INVESTMENT_AND_RETIREMENT_FUNDS",
    "TRANSFER_IN_INVESTMENT_AND_RETIREMENT_FUNDS",
    "INVESTMENT_AND_RETIREMENT_FUNDS",
}

INTERNAL_TRANSFER_DETAILED = {
    "TRANSFER_OUT_SAVINGS",
    "TRANSFER_IN_SAVINGS",
    "TRANSFER_IN_ACCOUNT_TRANSFER",
    "TRANSFER_OUT_ACCOUNT_TRANSFER",
}

INVESTMENT_PERIOD_GRACE_DAYS = 7

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
        "txn_type": "share",
        "date": "",
        "amount": -400.00,
        "currency": "USD",
        "description": "June rent split",
        "account_name": "Splitwise · Roommates",
        "category": "Rent",
        "paid_share": 800.00,
        "owed_share": 400.00,
        "expense_cost": 800.00,
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


def _amounts_match(a: float, b: float, *, tolerance: float = AMOUNT_TOLERANCE) -> bool:
    if b == 0:
        return a == 0
    return abs(a - b) <= max(tolerance, 0.01 * b)


def _within_days(a: datetime, b: datetime, days: int) -> bool:
    return abs((a - b).days) <= days


def _parse_date(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def _is_plaid_charge(txn: dict) -> bool:
    return (
        txn.get("source") in ("card", "bank")
        and txn.get("amount", 0) != 0
        and txn.get("txn_type") not in ("investment", "transfer")
    )


def _robinhood_haystack(txn: dict) -> str:
    parts = [
        txn.get("description"),
        txn.get("original_description"),
        txn.get("merchant_name"),
        txn.get("account_name"),
        txn.get("category"),
        txn.get("institution_name"),
    ]
    for name in txn.get("counterparties") or []:
        parts.append(name)
    return " ".join(str(p) for p in parts if p).lower()


def _matches_robinhood(txn: dict) -> bool:
    if txn.get("source") not in ("bank", "card"):
        return False
    if any(marker in _robinhood_haystack(txn) for marker in ROBINHOOD_MARKERS):
        return True
    detailed = (txn.get("plaid_category_detailed") or "").upper()
    if detailed in INVESTMENT_PLAID_DETAILED:
        return True
    if "INVESTMENT" in detailed and "TRANSFER" in detailed:
        return True
    return False


def _is_robinhood_transfer(txn: dict) -> bool:
    return _matches_robinhood(txn) and txn.get("amount", 0) < 0


def _is_internal_transfer(txn: dict) -> bool:
    if txn.get("source") != "bank":
        return False
    if _matches_robinhood(txn):
        return False
    detailed = (txn.get("plaid_category_detailed") or "").upper()
    if detailed in INTERNAL_TRANSFER_DETAILED:
        return True
    desc = _robinhood_haystack(txn)
    internal_phrases = (
        "online transfer to sav",
        "online transfer from chk",
        "online transfer to chk",
        "transfer to sav",
        "transfer from chk",
    )
    return any(phrase in desc for phrase in internal_phrases)


def _mark_investment_transfers(txns: list[dict]) -> None:
    for txn in txns:
        if not _matches_robinhood(txn):
            continue
        txn["txn_type"] = "investment"
        txn["category"] = "Investments"
        if txn.get("amount", 0) > 0:
            txn["investment_direction"] = "withdrawal"
        else:
            txn["investment_direction"] = "deposit"
        if "robinhood" not in (txn.get("description") or "").lower():
            label = "Withdrawal" if txn.get("amount", 0) > 0 else "Transfer"
            txn["description"] = f"Robinhood · {label}"


def _mark_internal_transfers(txns: list[dict]) -> None:
    for txn in txns:
        if txn.get("txn_type") or txn.get("source") != "bank":
            continue
        if not _is_internal_transfer(txn):
            continue
        txn["txn_type"] = "transfer"
        txn["category"] = "Transfer"
        txn["effective_amount"] = 0
        txn["hidden"] = True


def _link_investment_hops(txns: list[dict]) -> None:
    """Hide checking↔savings shuffles that fund a nearby Robinhood deposit."""
    investments = [
        t for t in txns
        if t.get("txn_type") == "investment" and t.get("investment_direction") == "deposit"
    ]
    for inv in investments:
        amount = abs(inv.get("amount", 0))
        inv_dt = _parse_date(inv["date"])
        for txn in txns:
            if txn.get("txn_type") != "transfer":
                continue
            if not _amounts_match(abs(txn.get("amount", 0)), amount):
                continue
            if not _within_days(_parse_date(txn["date"]), inv_dt, CARD_MATCH_DAYS):
                continue
            txn["effective_amount"] = 0
            txn["hidden"] = True


def _find_single_charge_match(
    charges: list[dict],
    *,
    target: float,
    anchor: datetime,
    days: int,
    matched: set[str],
) -> dict | None:
    best: dict | None = None
    best_day_delta: int | None = None
    for charge in charges:
        if charge["id"] in matched:
            continue
        charge_amt = abs(charge["amount"])
        charge_dt = _parse_date(charge["date"])
        day_delta = abs((charge_dt - anchor).days)
        if day_delta > days:
            continue
        if not _amounts_match(charge_amt, target):
            continue
        if best is None or day_delta < best_day_delta:
            best = charge
            best_day_delta = day_delta
    return best


def _find_bundle_charge_match(
    charges: list[dict],
    *,
    target: float,
    anchor: datetime,
    days: int,
    matched: set[str],
) -> list[dict] | None:
    candidates = [
        c for c in charges
        if c["id"] not in matched and _within_days(_parse_date(c["date"]), anchor, days)
    ]
    if not candidates:
        return None

    total = sum(abs(c["amount"]) for c in candidates)
    if _amounts_match(total, target, tolerance=BUNDLE_TOLERANCE):
        return candidates

    picked: list[dict] = []
    running = 0.0
    for charge in sorted(candidates, key=lambda c: abs(c["amount"]), reverse=True):
        next_total = running + abs(charge["amount"])
        if next_total <= target + BUNDLE_TOLERANCE:
            picked.append(charge)
            running = next_total
            if _amounts_match(running, target, tolerance=BUNDLE_TOLERANCE):
                return picked
    return None


def _suppress_charges(charges: list[dict]) -> None:
    for charge in charges:
        charge["effective_amount"] = 0
        charge["hidden"] = True


def apply_spending_rules(transactions: list[dict]) -> list[dict]:
    """Compute true personal spend: shares, card dedup, settlements."""
    txns = [dict(t) for t in transactions]
    _mark_investment_transfers(txns)
    _mark_internal_transfers(txns)
    _link_investment_hops(txns)
    matched_plaid: set[str] = set()

    splitwise_shares = [
        t for t in txns
        if t.get("source") == "splitwise" and t.get("txn_type") == "share"
    ]
    splitwise_settlements = [
        t for t in txns
        if t.get("source") == "splitwise" and t.get("txn_type") == "settlement"
    ]
    plaid = [t for t in txns if _is_plaid_charge(t)]

    for sw in splitwise_shares:
        owed = abs(sw.get("amount", 0))
        paid = sw.get("paid_share", 0)
        cost = sw.get("expense_cost", 0)
        sw_dt = _parse_date(sw["date"])
        sw["effective_amount"] = round(-owed, 2)

        if paid <= 0:
            continue

        match_targets = [paid]
        if cost > 0 and not _amounts_match(cost, paid):
            match_targets.append(cost)

        matched_charges: list[dict] = []
        for target in match_targets:
            single = _find_single_charge_match(
                plaid,
                target=target,
                anchor=sw_dt,
                days=CARD_MATCH_DAYS,
                matched=matched_plaid,
            )
            if single:
                matched_charges = [single]
                break

            bundle = _find_bundle_charge_match(
                plaid,
                target=target,
                anchor=sw_dt,
                days=CARD_MATCH_DAYS,
                matched=matched_plaid,
            )
            if bundle:
                matched_charges = bundle
                break

        if matched_charges:
            for charge in matched_charges:
                matched_plaid.add(charge["id"])
            _suppress_charges(matched_charges)

    for settlement in splitwise_settlements:
        settlement["effective_amount"] = settlement["amount"]
        amt = abs(settlement["amount"])
        anchor = _parse_date(settlement["date"])
        direction = settlement.get("settlement_direction")

        if direction == "received":
            bank_match = _find_single_charge_match(
                [t for t in plaid if t.get("amount", 0) > 0],
                target=amt,
                anchor=anchor,
                days=SETTLEMENT_MATCH_DAYS,
                matched=matched_plaid,
            )
            if bank_match:
                matched_plaid.add(bank_match["id"])
                _suppress_charges([bank_match])
        elif direction == "sent":
            bank_match = _find_single_charge_match(
                [t for t in plaid if t.get("amount", 0) < 0],
                target=amt,
                anchor=anchor,
                days=SETTLEMENT_MATCH_DAYS,
                matched=matched_plaid,
            )
            if bank_match:
                matched_plaid.add(bank_match["id"])
                _suppress_charges([bank_match])

    for txn in txns:
        if "effective_amount" not in txn:
            txn["effective_amount"] = txn.get("amount", 0)

    return txns


def _txn_amount(txn: dict) -> float:
    return txn.get("effective_amount", txn["amount"])


def _public_transactions(transactions: list[dict]) -> list[dict]:
    public: list[dict] = []
    skip_keys = {
        "paid_share", "owed_share", "expense_cost", "hidden", "effective_amount",
        "settlement_direction",
        "original_description", "merchant_name",
        "counterparties", "plaid_category_primary", "plaid_category_detailed",
    }

    for txn in transactions:
        if txn.get("hidden"):
            continue
        row = {k: v for k, v in txn.items() if k not in skip_keys}
        if txn.get("txn_type") == "share" and txn.get("source") == "splitwise":
            row["paid_share"] = txn.get("paid_share")
            row["owed_share"] = txn.get("owed_share")
        effective = txn.get("effective_amount", txn["amount"])
        if effective != txn.get("amount"):
            row["amount"] = effective
        public.append(row)

    return public


def compute_summary(transactions: list[dict], *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    period_start, period_end = _period_bounds(now)
    investment_start = period_start - timedelta(days=INVESTMENT_PERIOD_GRACE_DAYS)

    period_txns = [
        t for t in transactions
        if period_start <= _parse_date(t["date"]) < period_end
    ]
    investment_period_txns = [
        t for t in transactions
        if investment_start <= _parse_date(t["date"]) < period_end
    ]

    outflow = sum(
        abs(_txn_amount(t))
        for t in period_txns
        if _txn_amount(t) < 0 and t.get("txn_type") not in ("investment", "transfer")
    )
    inflow = sum(
        _txn_amount(t) for t in period_txns
        if _txn_amount(t) > 0 and t.get("txn_type") not in ("investment", "transfer")
    )

    by_source = {"bank": 0.0, "card": 0.0, "splitwise": 0.0}
    investments_out = 0.0
    investments_in = 0.0
    settlements_in = 0.0
    settlements_out = 0.0
    shared_share_out = 0.0

    for t in period_txns:
        amt = _txn_amount(t)
        src = t.get("source", "bank")

        if t.get("txn_type") in ("investment", "transfer"):
            continue

        if t.get("txn_type") == "settlement":
            if amt > 0:
                settlements_in += amt
            else:
                settlements_out += abs(amt)
            if src in by_source and amt < 0:
                by_source[src] += abs(amt)
            continue

        if t.get("txn_type") == "share" and amt < 0:
            shared_share_out += abs(amt)

        if amt >= 0:
            continue
        if src in by_source:
            by_source[src] += abs(amt)

    for t in investment_period_txns:
        if t.get("txn_type") != "investment":
            continue
        amt = _txn_amount(t)
        if amt < 0:
            investments_out += abs(amt)
        elif amt > 0:
            investments_in += amt

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
        "shared_share_outflow": round(shared_share_out, 2),
        "settlements_received": round(settlements_in, 2),
        "settlements_paid": round(settlements_out, 2),
        "investments_outflow": round(investments_out, 2),
        "investments_inflow": round(investments_in, 2),
        "investments_net": round(investments_out - investments_in, 2),
    }


def _fetch_days(now: datetime, default_days: int) -> int:
    period_start, _ = _period_bounds(now)
    needed = (now - period_start).days + CARD_MATCH_DAYS + 7
    return max(default_days, needed)


def _snapshot_to_spending(snapshot) -> SpendingData:
    captured = snapshot.captured_at
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=timezone.utc)
    transactions = snapshot.transactions_json or []
    resolved = apply_spending_rules(transactions)
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
    resolved = apply_spending_rules(unique)
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
    resolved = apply_spending_rules(txns)
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
        try:
            plaid_txns = plaid_client.fetch_plaid_transactions(days=days, force_refresh=True)
        except Exception:
            logger.exception("Plaid fetch failed on cache refresh")
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

# Backwards-compatible alias for any internal callers
resolve_splitwise_overlaps = apply_spending_rules
