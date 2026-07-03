import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from config import settings
from db.database import (
    get_latest_spending_snapshot,
    get_monthly_budget,
    get_plaid_institution_logos,
    save_spending_snapshot,
)
from integrations import plaid_client, splitwise_client
from integrations.medium import resolve_medium

logger = logging.getLogger(__name__)

CARD_MATCH_DAYS = 21
AMOUNT_TOLERANCE = 1.0

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

HISTORY_EPOCH = datetime(2026, 1, 6, tzinfo=timezone.utc)

CREDIT_CARD_PAYMENT_DETAILED = {
    "LOAN_PAYMENTS_CREDIT_CARD_PAYMENT",
}

CREDIT_CARD_PAYMENT_PHRASES = (
    "payment to chase card",
    "discover e-payment",
    "american express ach",
    "credit card payment",
    "card ending in",
    "autopay card",
    "e-payment",
    "ach pmt",
)

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
        "net_balance": -400.00,
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


def _next_period_start(period_start: datetime) -> datetime:
    start_day = settings.spending_period_start_day
    if period_start.month == 12:
        return period_start.replace(year=period_start.year + 1, month=1, day=start_day)
    return period_start.replace(month=period_start.month + 1, day=start_day)


def iter_billing_periods(from_start: datetime, now: datetime):
    """Yield (period_start, period_end) from from_start through the period containing now."""
    current_start, _ = _period_bounds(now)
    cursor = from_start.replace(hour=0, minute=0, second=0, microsecond=0)
    while cursor <= current_start:
        yield cursor, _next_period_start(cursor)
        cursor = _next_period_start(cursor)


def _is_credit_card_payment(txn: dict) -> bool:
    if txn.get("source") != "bank" or txn.get("amount", 0) >= 0:
        return False
    detailed = (txn.get("plaid_category_detailed") or "").upper()
    if detailed in CREDIT_CARD_PAYMENT_DETAILED:
        return True
    if "CREDIT_CARD_PAYMENT" in detailed:
        return True
    hay = _robinhood_haystack(txn)
    return any(phrase in hay for phrase in CREDIT_CARD_PAYMENT_PHRASES)


def _mark_credit_card_payments(txns: list[dict]) -> None:
    for txn in txns:
        if txn.get("txn_type") or txn.get("source") != "bank":
            continue
        if not _is_credit_card_payment(txn):
            continue
        txn["txn_type"] = "cc_payment"
        txn["category"] = "Credit card payment"


RENT_USER_SHARE = 956.0
DEBT_SHARE_PHRASES = ("all splits", "more debt")
SETTLEMENT_PAYMENT_MIN = 200.0


def _is_debt_share(share: dict) -> bool:
    desc = (share.get("description") or "").lower()
    return any(phrase in desc for phrase in DEBT_SHARE_PHRASES)


def _is_bilt_housing(txn: dict) -> bool:
    desc = (txn.get("description") or "").upper()
    return "BILT" in desc and "HOUSING" in desc


def _rent_roommate_fronted(billable_shares: list[dict]) -> float:
    return sum(
        _splitwise_net_amount(share)
        for share in billable_shares
        if _is_rent_splitwise(share) and _splitwise_net_amount(share) > 0
    )


def _bilt_counted_amount(full: float, billable_shares: list[dict]) -> float:
    fronted = _rent_roommate_fronted(billable_shares)
    if fronted > 0:
        return max(0.0, full - fronted)
    return min(RENT_USER_SHARE, full)


def _is_settlement_payment(match: dict, owed: float) -> bool:
    if owed < SETTLEMENT_PAYMENT_MIN:
        return False
    if match.get("source") != "bank":
        return False
    hay = (match.get("description") or "").lower()
    return "zelle" in hay or "venmo" in hay


SETTLEMENT_SHARE_PHRASES = (
    "settle balances",
    "settle balance",
    "settle all balances",
    "settle up balances",
    "settle up balance",
    "simplify debts",
    "simplifying debts",
)


def _is_splitwise_settlement(txn: dict) -> bool:
    """Splitwise settle-up / balance settlement — not day-to-day consumption."""
    if txn.get("source") != "splitwise":
        return False
    if txn.get("txn_type") == "settlement":
        return True
    if txn.get("txn_type") != "share":
        return False

    desc = (txn.get("description") or "").lower().strip()
    category = (txn.get("category") or "").lower().strip()
    if category == "settlement":
        return True
    if any(phrase in desc for phrase in SETTLEMENT_SHARE_PHRASES):
        return True
    return "settle" in desc and "balance" in desc


def _is_settlement_share(share: dict) -> bool:
    return _is_splitwise_settlement(share)


def _is_expense_record(txn: dict) -> bool:
    """Card/bank outflows only — no credits, refunds, or non-spend types."""
    amt = _txn_amount(txn)
    if amt >= 0:
        return False
    if txn.get("txn_type") in ("investment", "transfer", "cc_payment", "settlement"):
        return False
    if txn.get("source") == "splitwise" and _is_splitwise_settlement(txn):
        return False
    return True


def _is_budget_list_record(txn: dict) -> bool:
    """Card debits plus all Splitwise shares (±) shown on the Spend tab."""
    if txn.get("txn_type") in ("investment", "transfer", "cc_payment", "settlement"):
        return False
    if txn.get("source") == "splitwise":
        return txn.get("txn_type") == "share" and not _is_splitwise_settlement(txn)
    return _is_expense_record(txn)


def _filter_budget_list_records(transactions: list[dict]) -> list[dict]:
    return [t for t in transactions if _is_budget_list_record(t)]


def _filter_expense_records(transactions: list[dict]) -> list[dict]:
    return _filter_budget_list_records(transactions)


def _is_rent_splitwise(share: dict) -> bool:
    desc = (share.get("description") or "").strip().lower()
    category = (share.get("category") or "").strip().lower()
    return desc == "rent" or category == "rent"


def _splitwise_net_amount(share: dict) -> float:
    return float(share.get("net_balance", share.get("amount", 0)) or 0)


def compute_period_spend(
    transactions: list[dict],
    period_start: datetime,
    period_end: datetime,
    *,
    excluded_ids: frozenset[str] | None = None,
) -> dict:
    """
    Personal spend aligned with typical Splitwise workflow:

    - Bilt rent → your share only (~$956); roommate Splitwise rent split adjusts if present.
    - Group expenses → sum owed_share on each split (your portion).
    - Plaid charges tied to a Splitwise split are excluded (already in owed_share).
    - Pure fronting (owed=0) and settlements/debt lumps → not your spend.
    """
    excluded = excluded_ids or frozenset()
    period_txns = [
        t for t in transactions
        if period_start <= _parse_date(t["date"]) < period_end
        and t.get("id") not in excluded
    ]

    splitwise_shares = [
        t for t in period_txns
        if t.get("source") == "splitwise" and t.get("txn_type") == "share"
    ]
    billable_shares = [
        t for t in splitwise_shares
        if not _is_settlement_share(t) and not _is_debt_share(t)
    ]
    splitwise_net = round(sum(_splitwise_net_amount(t) for t in billable_shares), 2)

    plaid_debits = [
        t for t in period_txns
        if t.get("source") in ("bank", "card")
        and _txn_amount(t) < 0
        and t.get("txn_type") not in ("investment", "transfer", "cc_payment")
    ]

    excluded_cc_payments = 0.0
    excluded_transfers = 0.0
    excluded_investments = 0.0
    for txn in period_txns:
        amt = abs(_txn_amount(txn))
        tt = txn.get("txn_type")
        if tt == "cc_payment":
            excluded_cc_payments += amt
        elif tt == "transfer":
            excluded_transfers += amt
        elif tt == "investment":
            excluded_investments += amt

    matched_paid: set[str] = set()
    matched_owed: set[str] = set()
    excluded_from_plaid: set[str] = set()
    matched_to_splitwise = 0.0
    splitwise_consumption = 0.0

    for sw in billable_shares:
        owed = sw.get("owed_share", 0)
        paid = sw.get("paid_share", 0)
        anchor = _parse_date(sw["date"])

        if paid > 0:
            match = _find_plaid_match_for_paid(
                plaid_debits,
                target=paid,
                anchor=anchor,
                matched=matched_paid,
                tolerance=1.0,
            )
            if match:
                excluded_from_plaid.add(match["id"])
                matched_to_splitwise += abs(_txn_amount(match))

        if owed <= 0:
            continue

        owed_match = _find_plaid_match_for_paid(
            plaid_debits,
            target=owed,
            anchor=anchor,
            matched=matched_owed,
            tolerance=0.02,
        )
        if owed_match:
            excluded_from_plaid.add(owed_match["id"])
            matched_to_splitwise += abs(_txn_amount(owed_match))
            if _is_settlement_payment(owed_match, owed):
                continue

        splitwise_consumption += owed

    personal_bank = 0.0
    personal_card = 0.0
    rent_counted = 0.0
    for txn in plaid_debits:
        if txn["id"] in excluded_from_plaid:
            continue
        out = abs(_txn_amount(txn))
        if _is_bilt_housing(txn):
            out = _bilt_counted_amount(out, billable_shares)
            rent_counted += out
        if txn.get("source") == "card":
            personal_card += out
        else:
            personal_bank += out

    plaid_personal = round(personal_bank + personal_card, 2)
    splitwise_consumption = round(splitwise_consumption, 2)
    total_spend = round(splitwise_consumption + plaid_personal, 2)

    return {
        "total_spend": total_spend,
        "splitwise_consumption": splitwise_consumption,
        "plaid_personal": plaid_personal,
        "gross_plaid": plaid_personal,
        "plaid_outflow": plaid_personal,
        "rent_counted": round(rent_counted, 2),
        "splitwise_net": splitwise_net,
        "splitwise_additions": splitwise_consumption,
        "splitwise_deductions": 0.0,
        "splitwise_adjustment": splitwise_consumption,
        "splitwise_your_shares": splitwise_consumption,
        "card_spend": round(personal_card, 2),
        "bank_spend": round(personal_bank, 2),
        "plaid_direct": plaid_personal,
        "plaid_matched_to_splitwise": round(matched_to_splitwise, 2),
        "excluded_cc_payments": round(excluded_cc_payments, 2),
        "excluded_transfers": round(excluded_transfers, 2),
        "excluded_investments": round(excluded_investments, 2),
        "user_excluded_count": len(excluded),
    }


def _find_plaid_match_for_paid(
    debits: list[dict],
    *,
    target: float,
    anchor: datetime,
    matched: set[str],
    tolerance: float | None = None,
) -> dict | None:
    best: dict | None = None
    best_day_delta: int | None = None
    amount_tolerance = AMOUNT_TOLERANCE if tolerance is None else tolerance
    for txn in debits:
        if txn["id"] in matched:
            continue
        amt = abs(_txn_amount(txn))
        txn_dt = _parse_date(txn["date"])
        day_delta = abs((txn_dt - anchor).days)
        if day_delta > CARD_MATCH_DAYS:
            continue
        if not _amounts_match(amt, target, tolerance=amount_tolerance):
            continue
        if best is None or day_delta < best_day_delta:
            best = txn
            best_day_delta = day_delta
    return best


def _amounts_match(a: float, b: float, *, tolerance: float = AMOUNT_TOLERANCE) -> bool:
    if b == 0:
        return a == 0
    return abs(a - b) <= max(tolerance, 0.01 * b)


def _within_days(a: datetime, b: datetime, days: int) -> bool:
    return abs((a - b).days) <= days


def _parse_date(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


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


def apply_spending_rules(transactions: list[dict]) -> list[dict]:
    """Tag investments, transfers, and CC payments. Splitwise amounts are used as-is."""
    txns = [dict(t) for t in transactions]
    _mark_investment_transfers(txns)
    _mark_internal_transfers(txns)
    _mark_credit_card_payments(txns)
    _link_investment_hops(txns)

    for txn in txns:
        txn.setdefault("effective_amount", txn.get("amount", 0))

    return txns


def apply_amount_overrides(
    transactions: list[dict],
    overrides: dict[str, float] | None = None,
) -> None:
    """Apply persisted user amount edits for budget calculations and display."""
    if overrides is None:
        from db.database import get_spending_amount_overrides
        overrides = get_spending_amount_overrides()
    if not overrides:
        return

    for txn in transactions:
        txn_id = txn.get("id")
        if not txn_id or txn_id not in overrides:
            continue
        original = _txn_amount(txn)
        new_amount = round(float(overrides[txn_id]), 2)
        if abs(new_amount - original) < 0.005:
            continue
        txn["original_amount"] = original
        txn["amount_edited"] = True
        txn["amount"] = new_amount
        txn["effective_amount"] = new_amount
        if txn.get("source") == "splitwise":
            txn["net_balance"] = new_amount


def resolve_spending_transactions(transactions: list[dict]) -> list[dict]:
    resolved = apply_spending_rules(transactions)
    apply_amount_overrides(resolved)
    return resolved


def _txn_amount(txn: dict) -> float:
    return txn.get("effective_amount", txn["amount"])


def _public_transactions(transactions: list[dict]) -> list[dict]:
    public: list[dict] = []
    skip_keys = {
        "paid_share", "owed_share", "expense_cost", "hidden", "effective_amount",
        "settlement_direction", "net_balance",
        "original_description", "merchant_name", "pending_transaction_id",
        "counterparties", "plaid_category_primary", "plaid_category_detailed",
    }

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


def compute_budget_status(
    transactions: list[dict],
    period_start: datetime,
    period_end: datetime,
    budget: float,
    *,
    excluded_ids: frozenset[str] | None = None,
) -> dict:
    """
    Budget tracking for the current billing period (6th–5th).

    Used = card purchases − Splitwise net (all shares: + increases remaining, − decreases it).
    Remaining = budget − used.

    Settle-balances entries and manually excluded transactions are skipped.
    """
    excluded = excluded_ids or frozenset()
    period_all = [
        t for t in transactions
        if period_start <= _parse_date(t["date"]) < period_end
    ]
    period_txns = [t for t in period_all if t.get("id") not in excluded]

    card_spend = sum(
        abs(_txn_amount(t))
        for t in period_txns
        if t.get("source") == "card"
        and _txn_amount(t) < 0
        and t.get("txn_type") not in ("investment", "transfer", "cc_payment")
    )

    splitwise_net = sum(
        _splitwise_net_amount(t)
        for t in period_txns
        if t.get("source") == "splitwise"
        and t.get("txn_type") == "share"
        and not _is_splitwise_settlement(t)
    )

    budget_used = round(card_spend - splitwise_net, 2)
    budget_remaining = round(budget - budget_used, 2)

    return {
        "monthly_budget": round(budget, 2),
        "budget_used": budget_used,
        "budget_remaining": budget_remaining,
        "budget_card_spend": round(card_spend, 2),
        "budget_splitwise_net": round(splitwise_net, 2),
        "budget_splitwise_expenses": round(
            sum(
                abs(_splitwise_net_amount(t))
                for t in period_txns
                if t.get("source") == "splitwise"
                and t.get("txn_type") == "share"
                and not _is_splitwise_settlement(t)
                and _splitwise_net_amount(t) < 0
            ),
            2,
        ),
        "budget_user_excluded_count": sum(
            1 for t in period_all if t.get("id") in excluded
        ),
    }


def _annotate_excluded_flag(transactions: list[dict], excluded_ids: frozenset[str]) -> None:
    for row in transactions:
        row["excluded_from_total"] = row.get("id") in excluded_ids


def _summary_with_budget(
    transactions: list[dict],
    *,
    now: datetime,
    excluded_ids: frozenset[str] | None = None,
) -> dict:
    from db.database import get_monthly_budget, get_spending_exclusion_ids

    excluded = excluded_ids if excluded_ids is not None else frozenset(get_spending_exclusion_ids())
    summary = compute_summary(transactions, now=now)
    period_start, period_end = _period_bounds(now)
    summary.update(compute_budget_status(
        transactions, period_start, period_end, get_monthly_budget(),
        excluded_ids=excluded,
    ))
    return summary


def _fetch_days(now: datetime, default_days: int) -> int:
    period_start, _ = _period_bounds(now)
    needed = (now - period_start).days + CARD_MATCH_DAYS + 7
    return max(default_days, needed)


def _snapshot_to_spending(snapshot) -> SpendingData:
    captured = snapshot.captured_at
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=timezone.utc)
    transactions = snapshot.transactions_json or []
    resolved = resolve_spending_transactions(transactions)
    from db.database import get_monthly_budget, get_spending_exclusion_ids

    excluded_ids = frozenset(get_spending_exclusion_ids())
    summary = compute_summary(resolved, now=captured)
    period_start, period_end = _period_bounds(captured)
    summary.update(compute_budget_status(
        resolved, period_start, period_end, get_monthly_budget(),
        excluded_ids=excluded_ids,
    ))
    visible = _public_transactions(resolved)
    _annotate_excluded_flag(visible, excluded_ids)
    return SpendingData(
        transactions=_filter_budget_list_records(visible),
        summary=summary,
        cached=True,
        updated_at=captured,
        source="snapshot",
    )


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
        raise RuntimeError("Failed to fetch Splitwise expenses — try again in a few minutes") from None


def _build_spending(
    plaid_txns: list[dict],
    splitwise_txns: list[dict],
    *,
    now: datetime,
    source: str,
    cached: bool = False,
) -> SpendingData:
    unique = _dedupe_and_sort(plaid_txns + splitwise_txns)
    resolved = resolve_spending_transactions(unique)
    from db.database import get_spending_exclusion_ids

    excluded_ids = frozenset(get_spending_exclusion_ids())
    summary = _summary_with_budget(resolved, now=now, excluded_ids=excluded_ids)
    visible = _public_transactions(resolved)
    _annotate_excluded_flag(visible, excluded_ids)
    expenses = _filter_budget_list_records(visible)
    if not expenses and source == "live":
        source = "empty"
    return SpendingData(
        transactions=expenses,
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
    resolved = resolve_spending_transactions(txns)
    from db.database import get_spending_exclusion_ids

    excluded_ids = frozenset(get_spending_exclusion_ids())
    summary = _summary_with_budget(resolved, now=now, excluded_ids=excluded_ids)
    visible = _public_transactions(resolved)
    _annotate_excluded_flag(visible, excluded_ids)
    return SpendingData(
        transactions=_filter_budget_list_records(visible),
        summary=summary,
        cached=False,
        updated_at=now,
        source="mock",
    )


def _fetch_live(*, days: int, splitwise_txns: list[dict] | None = None, force_plaid_refresh: bool = False) -> SpendingData:
    now = datetime.now(timezone.utc)
    plaid_txns: list[dict] = []

    try:
        plaid_txns = plaid_client.fetch_plaid_transactions(days=days, force_refresh=force_plaid_refresh)
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
        "monthly_budget": get_monthly_budget(),
    }


def get_spending(*, force_refresh: bool = False, days: int = 30) -> SpendingData:
    if settings.mock_integrations:
        return _mock_spending(days=days)

    now = datetime.now(timezone.utc)
    days = _fetch_days(now, days)
    splitwise_txns = _fetch_splitwise(days=days)

    has_any_source = plaid_client.has_connection() or splitwise_client.is_configured()
    if not has_any_source:
        snapshot = get_latest_spending_snapshot()
        if snapshot:
            return _snapshot_to_spending(snapshot)
        return SpendingData(
            transactions=[],
            summary=_summary_with_budget([], now=now),
            cached=False,
            updated_at=now,
            source="empty",
        )

    return _fetch_live(
        days=days,
        splitwise_txns=splitwise_txns,
        force_plaid_refresh=force_refresh,
    )

# Backwards-compatible alias for any internal callers
resolve_splitwise_overlaps = apply_spending_rules
