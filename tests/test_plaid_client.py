from integrations.plaid_client import _drop_superseded_pending


def test_drop_superseded_pending_keeps_pending_only():
    txns = [
        {"id": "plaid:pending123", "pending": True, "amount": -20.0},
    ]
    result = _drop_superseded_pending(txns)
    assert len(result) == 1


def test_drop_superseded_pending_removes_pending_when_posted_exists():
    txns = [
        {"id": "plaid:pending123", "pending": True, "amount": -20.0},
        {
            "id": "plaid:posted456",
            "pending": False,
            "pending_transaction_id": "pending123",
            "amount": -20.0,
        },
    ]
    result = _drop_superseded_pending(txns)
    assert [t["id"] for t in result] == ["plaid:posted456"]


def test_drop_superseded_pending_does_not_drop_unrelated_pending():
    txns = [
        {"id": "plaid:pending999", "pending": True, "amount": -15.0},
        {
            "id": "plaid:posted456",
            "pending": False,
            "pending_transaction_id": "other",
            "amount": -20.0,
        },
    ]
    result = _drop_superseded_pending(txns)
    assert len(result) == 2
