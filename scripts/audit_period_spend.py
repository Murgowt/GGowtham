#!/usr/bin/env python3
"""
Print a numbered audit of every transaction in a billing period and how
compute_period_spend treats it under the golden rules.

Usage:
  PYTHONPATH=. python scripts/audit_period_spend.py 2026-03-06
"""

from __future__ import annotations

import sys

from integrations.app_time import now_app
from integrations.spending import (
    _is_settlement_share,
    _parse_date,
    _period_label,
    _splitwise_net_amount,
    apply_spending_rules,
    compute_period_spend,
)
from integrations.spending_history import _fetch_period_transactions, _resolve_period


def _classify_items(transactions: list[dict], period_start, period_end) -> list[dict]:
    period_txns = [
        t for t in transactions
        if period_start <= _parse_date(t["date"]) < period_end
    ]
    splitwise_shares = [
        t for t in period_txns
        if t.get("source") == "splitwise" and t.get("txn_type") == "share"
    ]

    items: list[dict] = []

    for sw in splitwise_shares:
        net = _splitwise_net_amount(sw)
        desc = sw.get("description", "Splitwise")
        if _is_settlement_share(sw):
            treatment = "IGNORED"
            effect = 0.0
            reason = "Settlement — money paid back, no spend effect"
        else:
            treatment = "SPLITWISE"
            effect = -net
            if net < 0:
                reason = f"You owe ${abs(net):.2f} → adds to spend"
            elif net > 0:
                reason = f"You're owed ${net:.2f} → deducts from spend"
            else:
                reason = "Zero balance"

        items.append({
            "date": sw["date"][:10],
            "source": "splitwise",
            "description": desc,
            "amount": net,
            "treatment": treatment,
            "effect": round(effect, 2),
            "reason": reason,
        })

    plaid_debits = [
        t for t in period_txns
        if t.get("source") in ("bank", "card")
        and t.get("amount", 0) < 0
        and t.get("txn_type") not in ("investment", "transfer", "cc_payment")
    ]

    from integrations.spending import _find_plaid_match_for_paid

    billable = [t for t in splitwise_shares if not _is_settlement_share(t)]
    matched: set[str] = set()
    match_reason: dict[str, str] = {}
    for sw in billable:
        if _splitwise_net_amount(sw) > 0:
            continue
        owed = sw.get("owed_share", 0)
        if owed <= 0:
            continue
        match = _find_plaid_match_for_paid(
            plaid_debits,
            target=owed,
            anchor=_parse_date(sw["date"]),
            matched=matched,
            tolerance=0.02,
        )
        if match:
            matched.add(match["id"])
            match_reason[match["id"]] = f"Matched Splitwise: {sw.get('description', '')} (you owe ${owed:.2f})"

    for txn in plaid_debits:
        desc = txn.get("description", txn.get("merchant_name", ""))
        out = abs(txn.get("amount", 0))
        src = txn.get("source", "plaid")
        if txn["id"] in matched:
            items.append({
                "date": txn["date"][:10],
                "source": src,
                "description": desc,
                "amount": -out,
                "treatment": "MATCHED",
                "effect": 0.0,
                "reason": match_reason.get(txn["id"], "Matched to Splitwise"),
            })
            continue
        items.append({
            "date": txn["date"][:10],
            "source": src,
            "description": desc,
            "amount": -out,
            "treatment": "PLAID",
            "effect": out,
            "reason": "Bank/card outflow",
        })

    excluded = [
        t for t in period_txns
        if t.get("txn_type") in ("cc_payment", "transfer", "investment", "settlement")
        or (t.get("source") in ("bank", "card") and t.get("amount", 0) >= 0)
    ]
    for txn in excluded:
        tt = txn.get("txn_type", "inflow")
        items.append({
            "date": txn["date"][:10],
            "source": txn.get("source", "?"),
            "description": txn.get("description", ""),
            "amount": txn.get("amount", 0),
            "treatment": "IGNORED",
            "effect": 0.0,
            "reason": tt.replace("_", " ").title(),
        })

    items.sort(key=lambda r: (r["date"], r["source"], r["description"]))
    return items


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: PYTHONPATH=. python scripts/audit_period_spend.py YYYY-MM-DD")
        return 1

    period_key = sys.argv[1]
    now = now_app()
    resolved = _resolve_period(period_key, now)
    if not resolved:
        print(f"Unknown period key: {period_key}")
        return 1

    period_start, period_end = resolved
    txns = _fetch_period_transactions(period_start, period_end)
    spend = compute_period_spend(txns, period_start, period_end)
    items = _classify_items(txns, period_start, period_end)

    label = _period_label(period_start, period_end)
    print(f"\n{'=' * 72}")
    print(f"SPEND AUDIT: {label}")
    print(f"Formula: Plaid outflow − Splitwise net = total")
    print(f"{'=' * 72}")
    print(f"Plaid outflow:        ${spend['plaid_outflow']:,.2f}")
    print(f"Splitwise net:        ${spend['splitwise_net']:,.2f}  (positive = friends owe you)")
    print(f"Splitwise adjustment: ${spend['splitwise_adjustment']:,.2f}")
    print(f"TOTAL SPEND:          ${spend['total_spend']:,.2f}")
    print(f"{'=' * 72}\n")

    effect_sum = 0.0
    for i, row in enumerate(items, 1):
        effect_sum += row["effect"]
        amt = row["amount"]
        amt_str = f"${abs(amt):,.2f}"
        if amt < 0:
            amt_str = f"-{amt_str}"
        elif amt > 0:
            amt_str = f"+{amt_str}"
        else:
            amt_str = "$0.00"

        sign = "+" if row["effect"] >= 0 else ""
        print(f"{i:3}. [{row['treatment']:9}] {row['date']}  {row['source']:10}  {amt_str:>12}  effect {sign}${row['effect']:.2f}")
        print(f"     {row['description'][:65]}")
        print(f"     → {row['reason']}")
        print()

    print(f"{'=' * 72}")
    print(f"Sum of line effects: ${effect_sum:,.2f}  (should match total)")
    print(f"{'=' * 72}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
