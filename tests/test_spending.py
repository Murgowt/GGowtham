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
        "net_balance": -9.0,
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


def test_splitwise_and_card_both_show_without_dedup():
    resolved = apply_spending_rules([_card(), _share()])
    card = next(t for t in resolved if t["id"] == "card:1")
    share = next(t for t in resolved if t["id"] == "splitwise:share:1")

    assert card.get("hidden") is not True
    assert share.get("hidden") is not True
    assert share["amount"] == -9.0

    summary = compute_summary(resolved)
    assert summary["month_outflow"] == 26.90


def test_splitwise_uses_net_balance_sign():
    resolved = apply_spending_rules([
        _share(amount=6.75, net_balance=6.75, description="Metra"),
    ])
    share = resolved[0]
    assert share["amount"] == 6.75
    summary = compute_summary(resolved)
    assert summary["month_inflow"] == 6.75
    assert summary["month_outflow"] == 0.0


def test_splitwise_you_owe_shows_negative():
    resolved = apply_spending_rules([
        _share(amount=-15.5, net_balance=-15.5, description="Groceries"),
    ])
    assert resolved[0]["amount"] == -15.5
    assert compute_summary(resolved)["month_outflow"] == 15.5


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
    assert zelle.get("hidden") is not True

    summary = compute_summary(resolved)
    assert summary["settlements_received"] == 9.0
    assert summary["month_inflow"] == 18.0


def test_pending_card_included_in_outflow():
    resolved = apply_spending_rules([
        _card(id="card:pending", amount=-42.0, description="Uber", pending=True),
    ])
    card = resolved[0]
    assert card.get("hidden") is not True
    assert card["pending"] is True
    assert compute_summary(resolved)["month_outflow"] == 42.0


def test_personal_card_without_splitwise_unchanged():
    resolved = apply_spending_rules([_card(amount=-42.0, description="Uber")])
    card = resolved[0]
    assert card.get("hidden") is not True
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
