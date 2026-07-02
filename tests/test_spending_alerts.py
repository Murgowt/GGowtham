from integrations.spending_alerts import format_spending_alert_body, spending_alert_key


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


def test_format_spending_alert_body():
    body = format_spending_alert_body(
        {"description": "Rent", "amount": 519.44},
        1745.0,
    )
    assert "Rent" in body
    assert "+$519.44" in body
    assert "$1,745 left" in body


def test_format_spending_alert_body_pending_card():
    body = format_spending_alert_body(
        {"description": "Metro Market", "amount": -17.9, "pending": True},
        1600.0,
    )
    assert "Metro Market" in body
    assert "−$17.90" in body
    assert "pending" in body
