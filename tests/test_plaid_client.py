from datetime import date
from unittest.mock import patch

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


def test_sync_merge_keeps_cached_transactions_outside_delta():
    """Incremental sync must merge into cache, not replace the full list."""
    from integrations.plaid_client import _sync_item_transactions

    cached = {
        "plaid:old1": {
            "id": "plaid:old1",
            "date": "2026-07-01T12:00:00+00:00",
            "amount": -16.2,
            "description": "Discourse",
            "pending": False,
            "source": "card",
        },
    }

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    calls = {"n": 0}

    def fake_post(path, body):
        calls["n"] += 1
        assert path == "/transactions/sync"
        return {
            "added": [
                {
                    "account_id": "acc1",
                    "transaction_id": "newpending",
                    "amount": 25.0,
                    "pending": True,
                    "date": "2026-07-02",
                    "name": "Coffee Shop",
                },
            ],
            "modified": [],
            "removed": [],
            "next_cursor": "cursor-2",
            "has_more": False,
        }

    import integrations.plaid_client as plaid_mod

    accounts = [{"account_id": "acc1", "source": "card", "name": "Sapphire"}]
    with (
        patch.object(plaid_mod, "_post", side_effect=fake_post),
        patch.object(plaid_mod, "_map_plaid_transaction", side_effect=lambda txn, lookup: {
            "id": f"plaid:{txn['transaction_id']}",
            "date": f"{txn['date']}T12:00:00+00:00",
            "amount": -float(txn["amount"]),
            "description": txn.get("name") or "Txn",
            "pending": bool(txn.get("pending")),
            "source": "card",
        }),
    ):
        txns, cursor, store = _sync_item_transactions(
            "token",
            accounts,
            "cursor-1",
            cached,
            start=date(2026, 6, 1),
            end=date(2026, 7, 3),
        )

    assert cursor == "cursor-2"
    assert "plaid:old1" in store
    assert "plaid:newpending" in store
    descriptions = {t["description"] for t in txns}
    assert "Discourse" in descriptions
    assert "Coffee Shop" in descriptions
