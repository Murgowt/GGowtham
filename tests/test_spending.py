from datetime import timedelta

from integrations.app_time import now_app

from integrations.spending import apply_spending_rules, compute_summary


def _dt(days_ago: int = 0) -> str:
    return (now_app() - timedelta(days=days_ago)).isoformat()


def _share(**kwargs) -> dict:
    base = {
        "id": "splitwise:share:1",
        "source": "splitwise",
        "txn_type": "share",
        "date": _dt(1),
        "amount": -9.0,
        "net_balance": -9.0,
        "owed_share": 9.0,
        "paid_share": 0.0,
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


def test_credit_card_payment_excluded_from_period_spend():
    from integrations.spending import compute_period_spend, iter_billing_periods, HISTORY_EPOCH

    now = now_app()
    period_start, period_end = next(iter_billing_periods(HISTORY_EPOCH, now))
    txns = apply_spending_rules([
        _card(amount=-100.0, date=period_start.isoformat()),
        {
            "id": "bank:ccpay",
            "source": "bank",
            "date": period_start.isoformat(),
            "amount": -500.0,
            "description": "Payment to Chase card ending in 0133",
            "plaid_category_detailed": "LOAN_PAYMENTS_CREDIT_CARD_PAYMENT",
        },
        _share(amount=-20.0, net_balance=-20.0, owed_share=20.0, paid_share=0.0, date=period_start.isoformat()),
    ])
    spend = compute_period_spend(txns, period_start, period_end)
    assert spend["card_spend"] == 100.0
    assert spend["excluded_cc_payments"] == 500.0
    assert spend["splitwise_adjustment"] == 20.0
    assert spend["total_spend"] == 120.0


def test_period_spend_splitwise_adjusts_fronted_expense():
    from integrations.spending import compute_period_spend, iter_billing_periods, HISTORY_EPOCH

    now = now_app()
    period_start, period_end = next(iter_billing_periods(HISTORY_EPOCH, now))
    txns = apply_spending_rules([
        _card(amount=-6.75, description="Metra", date=period_start.isoformat()),
        _share(
            amount=6.75,
            net_balance=6.75,
            owed_share=0.0,
            paid_share=6.75,
            description="Metra",
            date=period_start.isoformat(),
        ),
    ])
    spend = compute_period_spend(txns, period_start, period_end)
    assert spend["splitwise_net"] == 6.75
    assert spend["total_spend"] == 0.0


def test_period_spend_fronted_for_friends_deducts():
    from integrations.spending import compute_period_spend, iter_billing_periods, HISTORY_EPOCH

    now = now_app()
    period_start, period_end = next(iter_billing_periods(HISTORY_EPOCH, now))
    txns = apply_spending_rules([
        _share(
            amount=300.0,
            net_balance=300.0,
            owed_share=0.0,
            paid_share=300.0,
            description="Horseshoe",
            date=period_start.isoformat(),
        ),
    ])
    spend = compute_period_spend(txns, period_start, period_end)
    assert spend["splitwise_net"] == 300.0
    assert spend["total_spend"] == 0.0


def test_period_spend_rent_and_splitwise_shares():
    from integrations.spending import compute_period_spend, iter_billing_periods, HISTORY_EPOCH

    now = now_app()
    period_start, period_end = next(iter_billing_periods(HISTORY_EPOCH, now))
    txns = apply_spending_rules([
        {
            "id": "bank:rent",
            "source": "bank",
            "date": period_start.isoformat(),
            "amount": -950.0,
            "description": "BILT CARD HOUSING",
            "plaid_category_detailed": "RENT_AND_UTILITIES_RENT",
        },
        _share(
            amount=-25.0,
            net_balance=-25.0,
            owed_share=25.0,
            paid_share=0.0,
            description="Groceries",
            date=period_start.isoformat(),
        ),
    ])
    spend = compute_period_spend(txns, period_start, period_end)
    assert spend["splitwise_adjustment"] == 25.0
    assert spend["bank_spend"] == 950.0
    assert spend["total_spend"] == 975.0


def test_period_spend_apartment_rent_only_counts_your_share():
    from integrations.spending import compute_period_spend, iter_billing_periods, HISTORY_EPOCH

    now = now_app()
    period_start, period_end = next(iter_billing_periods(HISTORY_EPOCH, now))
    txns = apply_spending_rules([
        {
            "id": "bank:rent",
            "source": "bank",
            "date": period_start.isoformat(),
            "amount": -1901.95,
            "description": "BILT CARD HOUSING PPD ID: 1844372402",
            "plaid_category_detailed": "RENT_AND_UTILITIES_RENT",
        },
        _share(
            amount=950.75,
            net_balance=950.75,
            owed_share=0.0,
            paid_share=950.75,
            description="Rent",
            date=period_start.isoformat(),
        ),
        _share(
            amount=-25.05,
            net_balance=-25.05,
            owed_share=25.05,
            paid_share=0.0,
            description="Food Poison 101",
            date=period_start.isoformat(),
        ),
        {
            "id": "bank:zelle",
            "source": "bank",
            "date": period_start.isoformat(),
            "amount": -25.05,
            "description": "Zelle payment to friend",
        },
    ])
    spend = compute_period_spend(txns, period_start, period_end)
    assert spend["splitwise_net"] == 925.7
    assert spend["bank_spend"] == 951.2
    assert spend["splitwise_consumption"] == 25.05
    assert spend["total_spend"] == 976.25


def test_period_spend_user_exclusion():
    from integrations.spending import compute_period_spend, iter_billing_periods, HISTORY_EPOCH

    now = now_app()
    period_start, period_end = next(iter_billing_periods(HISTORY_EPOCH, now))
    txns = apply_spending_rules([
        _card(amount=-100.0, date=period_start.isoformat()),
        _share(
            amount=-50.0,
            net_balance=-50.0,
            owed_share=50.0,
            paid_share=0.0,
            description="Dinner",
            date=period_start.isoformat(),
        ),
    ])
    full = compute_period_spend(txns, period_start, period_end)
    excluded = compute_period_spend(
        txns, period_start, period_end, excluded_ids=frozenset({"splitwise:share:1"}),
    )
    assert full["total_spend"] == 150.0
    assert excluded["total_spend"] == 100.0


def test_budget_status_card_and_splitwise():
    from integrations.spending import apply_spending_rules, compute_budget_status, iter_billing_periods, HISTORY_EPOCH

    now = now_app()
    period_start, period_end = next(iter_billing_periods(HISTORY_EPOCH, now))
    txns = apply_spending_rules([
        _card(amount=-200.0, date=period_start.isoformat()),
        _share(
            amount=150.0,
            net_balance=150.0,
            owed_share=0.0,
            paid_share=150.0,
            description="Reimbursement",
            date=period_start.isoformat(),
        ),
    ])
    status = compute_budget_status(txns, period_start, period_end, 2200.0)
    assert status["budget_card_spend"] == 200.0
    assert status["budget_splitwise_net"] == 150.0
    assert status["budget_used"] == 50.0
    assert status["budget_remaining"] == 2150.0

    # $1800 budget − $50 used (card $200 − splitwise +$150) → $1750 left
    status2 = compute_budget_status(txns, period_start, period_end, 1800.0)
    assert status2["budget_remaining"] == 1750.0


def test_budget_splitwise_net_includes_all_splits():
    from integrations.spending import (
        apply_spending_rules,
        compute_budget_status,
        iter_billing_periods,
        HISTORY_EPOCH,
        _filter_budget_list_records,
        _public_transactions,
    )

    now = now_app()
    period_start, period_end = next(iter_billing_periods(HISTORY_EPOCH, now))
    txns = apply_spending_rules([
        _card(amount=-200.0, date=period_start.isoformat()),
        _share(
            amount=150.0,
            net_balance=150.0,
            owed_share=0.0,
            paid_share=150.0,
            description="Reimbursement",
            date=period_start.isoformat(),
        ),
        _share(
            amount=-40.0,
            net_balance=-40.0,
            owed_share=40.0,
            paid_share=0.0,
            description="Dinner",
            date=period_start.isoformat(),
        ),
    ])
    status = compute_budget_status(txns, period_start, period_end, 2200.0)
    assert status["budget_splitwise_net"] == 110.0
    assert status["budget_used"] == 90.0
    assert status["budget_remaining"] == 2110.0

    visible = _filter_budget_list_records(_public_transactions(txns))
    assert len(visible) == 3


def test_budget_status_user_exclusion():
    from integrations.spending import apply_spending_rules, compute_budget_status, iter_billing_periods, HISTORY_EPOCH

    now = now_app()
    period_start, period_end = next(iter_billing_periods(HISTORY_EPOCH, now))
    txns = apply_spending_rules([
        _card(amount=-100.0, date=period_start.isoformat()),
        _share(
            amount=-50.0,
            net_balance=-50.0,
            owed_share=50.0,
            paid_share=0.0,
            description="Dinner",
            date=period_start.isoformat(),
        ),
    ])
    full = compute_budget_status(txns, period_start, period_end, 2200.0)
    excluded = compute_budget_status(
        txns, period_start, period_end, 2200.0,
        excluded_ids=frozenset({"splitwise:share:1"}),
    )
    assert full["budget_used"] == 150.0
    assert full["budget_remaining"] == 2050.0
    assert excluded["budget_used"] == 100.0
    assert excluded["budget_remaining"] == 2100.0
    assert excluded["budget_user_excluded_count"] == 1


def test_budget_status_includes_bilt_bank_rent():
    from integrations.spending import apply_spending_rules, compute_budget_status, iter_billing_periods, HISTORY_EPOCH

    now = now_app()
    period_start, period_end = next(iter_billing_periods(HISTORY_EPOCH, now))
    txns = apply_spending_rules([
        _card(amount=-200.0, date=period_start.isoformat()),
        {
            "id": "bank:rent",
            "source": "bank",
            "date": period_start.isoformat(),
            "amount": -1901.95,
            "description": "BILT CARD HOUSING PPD ID: 1844372402",
            "plaid_category_detailed": "RENT_AND_UTILITIES_RENT",
        },
        _share(
            amount=950.75,
            net_balance=950.75,
            owed_share=0.0,
            paid_share=950.75,
            description="Rent - july",
            category="Rent",
            date=period_start.isoformat(),
        ),
    ])
    status = compute_budget_status(txns, period_start, period_end, 2000.0)
    assert status["budget_card_spend"] == 200.0
    assert status["budget_rent_spend"] == 1901.95
    assert status["budget_splitwise_net"] == 950.75
    assert status["budget_used"] == 1151.2
    assert status["budget_remaining"] == 848.8


def test_budget_excludes_settle_balances():
    from integrations.spending import apply_spending_rules, compute_budget_status, iter_billing_periods, HISTORY_EPOCH

    now = now_app()
    period_start, period_end = next(iter_billing_periods(HISTORY_EPOCH, now))
    txns = apply_spending_rules([
        _card(amount=-200.0, date=period_start.isoformat()),
        _share(
            amount=-150.0,
            net_balance=-150.0,
            owed_share=150.0,
            paid_share=0.0,
            description="Settle balances",
            date=period_start.isoformat(),
        ),
        _share(
            amount=75.0,
            net_balance=75.0,
            owed_share=0.0,
            paid_share=75.0,
            description="Settle up balances",
            date=period_start.isoformat(),
        ),
    ])
    status = compute_budget_status(txns, period_start, period_end, 2200.0)
    assert status["budget_card_spend"] == 200.0
    assert status["budget_splitwise_net"] == 0.0
    assert status["budget_used"] == 200.0
    assert status["budget_remaining"] == 2000.0


def test_budget_amount_override():
    from integrations.spending import (
        apply_amount_overrides,
        apply_spending_rules,
        compute_budget_status,
        iter_billing_periods,
        HISTORY_EPOCH,
    )

    now = now_app()
    period_start, period_end = next(iter_billing_periods(HISTORY_EPOCH, now))
    txns = apply_spending_rules([
        _card(amount=-200.0, date=period_start.isoformat()),
    ])
    full = compute_budget_status(txns, period_start, period_end, 2200.0)
    assert full["budget_used"] == 200.0

    apply_amount_overrides(txns, {"card:1": -150.0})
    edited = compute_budget_status(txns, period_start, period_end, 2200.0)
    assert edited["budget_used"] == 150.0
    assert edited["budget_remaining"] == 2050.0
    assert txns[0]["amount_edited"] is True


def test_current_period_budget_records_excludes_prior_period():
    from integrations.spending import (
        _current_period_budget_records,
        _period_bounds,
        _public_transactions,
        apply_spending_rules,
    )

    now = now_app()
    period_start, _ = _period_bounds(now)
    prior = (period_start - timedelta(days=1)).isoformat()

    txns = apply_spending_rules([
        _card(id="card:current", amount=-50.0, date=period_start.isoformat()),
        _card(id="card:prior", amount=-99.0, date=prior),
    ])
    visible = _current_period_budget_records(_public_transactions(txns), now)
    assert [t["id"] for t in visible] == ["card:current"]
