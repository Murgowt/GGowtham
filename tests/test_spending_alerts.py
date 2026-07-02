from integrations.spending_alerts import (
    format_daily_budget_body,
    format_spending_alert_body,
    spending_alert_key,
    spending_alert_tone,
)


def test_spending_alert_key_dedupes_pending_posted():
    pending = {
        "id": "plaid:pending123",
        "source": "card",
        "pending_transaction_id": "pending123",
    }
    posted = {
        "id": "plaid:posted456",
        "source": "card",
        "pending_transaction_id": "pending123",
    }
    assert spending_alert_key(pending) == spending_alert_key(posted)


def test_spending_alert_tone_tiers():
    assert spending_alert_tone(budget_used=500, budget_remaining=1700, description="Rent") == "Okay Rent!!"
    assert spending_alert_tone(budget_used=1200, budget_remaining=1000) == "Be careful!!"
    assert spending_alert_tone(budget_used=1600, budget_remaining=600) == "STOP!!!"
    assert spending_alert_tone(budget_used=2300, budget_remaining=-100) == "IDIOT STOP!!!"


def test_format_spending_alert_body():
    title, body = format_spending_alert_body(
        {"description": "Rent", "amount": 519.44},
        {"budget_remaining": 1745.0, "budget_used": 455.0},
    )
    assert title == "$1,745 left"
    assert body == "Okay Rent!!"


def test_format_spending_alert_body_careful_tier():
    title, body = format_spending_alert_body(
        {"description": "Metro Market", "amount": -17.9, "pending": True},
        {"budget_remaining": 1000.0, "budget_used": 1200.0},
    )
    assert title == "$1,000 left"
    assert body == "Be careful!!"


def test_format_daily_budget_body():
    title, body = format_daily_budget_body(
        {"budget_remaining": 1745.56, "budget_used": 454.44},
    )
    assert title == "$1,746 left"
    assert body == "Okay!!"
