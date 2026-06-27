from datetime import datetime, timedelta, timezone

from integrations.spending import apply_spending_rules, compute_summary


def _dt(days_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _share(**kwargs) -> dict:
    base = {
        "id": "splitwise:share:1",
        "source": "splitwise",
        "txn_type": "share",
        "date": _dt(1),
        "amount": -9.0,
        "owed_share": 9.0,
        "paid_share": 17.90,
        "expense_cost": 18.0,
        "description": "Indian store",
    }
    base.update(kwargs)
    return base


def _card(**kwargs) -> dict:
    base = {
        "id": "card:1",
        "source": "card",
        "date": _dt(1),
        "amount": -17.90,
        "description": "Metro Market",
    }
    base.update(kwargs)
    return base


def test_user_paid_counts_share_not_full_card():
    resolved = apply_spending_rules([_card(), _share()])
    card = next(t for t in resolved if t["id"] == "card:1")
    share = next(t for t in resolved if t["id"] == "splitwise:share:1")

    assert card["hidden"] is True
    assert card["effective_amount"] == 0
    assert share["effective_amount"] == -9.0
    assert share.get("hidden") is not True

    summary = compute_summary(resolved)
    assert summary["month_outflow"] == 9.0


def test_friend_paid_counts_share_only():
    resolved = apply_spending_rules([
        _share(paid_share=0, amount=-9.0, owed_share=9.0),
    ])
    assert resolved[0]["effective_amount"] == -9.0
    assert compute_summary(resolved)["month_outflow"] == 9.0


def test_bundled_cards_suppressed_when_user_paid():
    resolved = apply_spending_rules([
        _card(id="card:a", amount=-17.90, date=_dt(3)),
        _card(id="card:b", amount=-42.00, date=_dt(2)),
        _card(id="card:c", amount=-15.00, date=_dt(1)),
        _share(
            id="splitwise:share:bundle",
            paid_share=74.90,
            expense_cost=75.0,
            amount=-37.50,
            owed_share=37.50,
            description="Misc bundle",
        ),
    ])

    hidden_cards = [t for t in resolved if t["source"] == "card" and t.get("hidden")]
    share = next(t for t in resolved if t["id"] == "splitwise:share:bundle")

    assert len(hidden_cards) == 3
    assert share["effective_amount"] == -37.50
    assert compute_summary(resolved)["month_outflow"] == 37.50


def test_settlement_received_counts_as_inflow():
    resolved = apply_spending_rules([
        {
            "id": "splitwise:settlement:9",
            "source": "splitwise",
            "txn_type": "settlement",
            "settlement_direction": "received",
            "date": _dt(0),
            "amount": 9.0,
            "description": "Settlement received",
        },
        {
            "id": "bank:zelle",
            "source": "bank",
            "date": _dt(0),
            "amount": 9.0,
            "description": "Zelle from friend",
        },
    ])

    zelle = next(t for t in resolved if t["id"] == "bank:zelle")
    assert zelle.get("hidden") is True

    summary = compute_summary(resolved)
    assert summary["settlements_received"] == 9.0
    assert summary["month_inflow"] == 9.0


def test_personal_card_without_splitwise_unchanged():
    resolved = apply_spending_rules([_card(amount=-42.0, description="Uber")])
    card = resolved[0]
    assert card.get("hidden") is not True
    assert card["effective_amount"] == -42.0
    assert compute_summary(resolved)["month_outflow"] == 42.0


def test_robinhood_deposit_and_withdrawal_net_to_zero():
    resolved = apply_spending_rules([
        {
            "id": "bank:rh-out",
            "source": "bank",
            "date": _dt(10),
            "amount": -2000.0,
            "description": "Robinhood",
            "account_name": "Chase Checking",
        },
        {
            "id": "bank:rh-in",
            "source": "bank",
            "date": _dt(1),
            "amount": 2000.0,
            "description": "Robinhood",
            "account_name": "Chase Checking",
        },
    ])
    summary = compute_summary(resolved)
    assert summary["investments_outflow"] == 2000.0
    assert summary["investments_inflow"] == 2000.0
    assert summary["investments_net"] == 0.0


def test_robinhood_inflow_marked_as_investment():
    resolved = apply_spending_rules([
        {
            "id": "bank:rh-in",
            "source": "bank",
            "date": _dt(1),
            "amount": 2000.0,
            "description": "Robinhood",
            "counterparties": ["Robinhood"],
            "account_name": "Chase Checking",
        },
    ])
    txn = resolved[0]
    assert txn["txn_type"] == "investment"
    assert txn.get("investment_direction") == "withdrawal"
    assert compute_summary(resolved)["investments_inflow"] == 2000.0


def test_internal_transfer_hidden_from_spend():
    resolved = apply_spending_rules([
        {
            "id": "bank:sav",
            "source": "bank",
            "date": _dt(1),
            "amount": -900.0,
            "description": "Online Transfer to SAV ...2998",
            "plaid_category_detailed": "TRANSFER_OUT_SAVINGS",
            "account_name": "Chase Checking",
        },
    ])
    txn = resolved[0]
    assert txn["txn_type"] == "transfer"
    assert txn.get("hidden") is True
    assert compute_summary(resolved)["month_outflow"] == 0


def test_robinhood_transfer_marked_as_investment():
    resolved = apply_spending_rules([
        {
            "id": "bank:rh",
            "source": "bank",
            "date": _dt(1),
            "amount": -500.0,
            "description": "Robinhood Securities",
            "account_name": "Chase Checking",
        },
        _card(amount=-42.0, description="Uber"),
    ])
    rh = next(t for t in resolved if t["id"] == "bank:rh")
    assert rh["txn_type"] == "investment"
    assert rh["category"] == "Investments"

    summary = compute_summary(resolved)
    assert summary["investments_outflow"] == 500.0
    assert summary["month_outflow"] == 42.0


def test_plaid_investment_category_detected_without_robinhood_name():
    resolved = apply_spending_rules([
        {
            "id": "bank:ach",
            "source": "bank",
            "date": _dt(2),
            "amount": -900.0,
            "description": "ACH Debit",
            "account_name": "Chase Checking",
            "plaid_category_detailed": "TRANSFER_OUT_INVESTMENT_AND_RETIREMENT_FUNDS",
            "counterparties": ["Robinhood Securities"],
        },
    ])
    txn = resolved[0]
    assert txn["txn_type"] == "investment"
    assert compute_summary(resolved)["investments_outflow"] == 900.0


def test_bank_transfer_not_hidden_by_splitwise_card_match():
    resolved = apply_spending_rules([
        {
            "id": "bank:rh",
            "source": "bank",
            "date": _dt(1),
            "amount": -900.0,
            "description": "Robinhood Securities",
            "account_name": "Chase Checking",
        },
        _share(
            id="splitwise:share:900",
            paid_share=900.0,
            expense_cost=900.0,
            amount=-450.0,
            owed_share=450.0,
            description="Unrelated split",
        ),
    ])
    rh = next(t for t in resolved if t["id"] == "bank:rh")
    assert rh.get("hidden") is not True
    assert rh["txn_type"] == "investment"
