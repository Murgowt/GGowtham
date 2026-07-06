"""API tests for goals and budget income."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from config import settings

_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.name}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["MOCK_INTEGRATIONS"] = "true"

from db.database import init_db  # noqa: E402
from main import app  # noqa: E402

init_db()
client = TestClient(app)
TEST_PIN = "9999"


@pytest.fixture(autouse=True)
def _pin(monkeypatch):
    monkeypatch.setattr(settings, "app_pin", TEST_PIN)


def _login():
    res = client.post("/api/login", json={"pin": TEST_PIN})
    assert res.status_code == 200, res.text


def test_goals_crud():
    _login()
    create = client.post(
        "/api/goals",
        json={"text": "₹2.5 Cr plot venture in 5 years with ₹50k/mo passive income"},
    )
    assert create.status_code == 200
    goal = create.json()
    assert goal["id"]
    assert goal["summary"]

    listing = client.get("/api/goals")
    assert listing.status_code == 200
    assert len(listing.json()["goals"]) >= 1

    update = client.put(
        f"/api/goals/{goal['id']}",
        json={"text": "Updated: ₹2 lakhs/mo life passive income inflation adjusted"},
    )
    assert update.status_code == 200
    assert update.json()["summary"]

    delete = client.delete(f"/api/goals/{goal['id']}")
    assert delete.status_code == 200


def test_income_pin_gated():
    _login()

    locked = client.get("/api/budget/income")
    assert locked.status_code == 200
    assert locked.json()["locked"] is True

    no_pin = client.post("/api/budget/income/unlock", json={})
    assert no_pin.status_code == 422

    bad_pin = client.post("/api/budget/income/unlock", json={"pin": "0000"})
    assert bad_pin.status_code == 403

    save_bad = client.put(
        "/api/budget/income",
        json={"text": "Take home $8500", "pin": "0000"},
    )
    assert save_bad.status_code == 403

    save = client.put(
        "/api/budget/income",
        json={
            "text": "Take-home $8,500/month. 45% venture, 35% living, 20% enjoy.",
            "pin": TEST_PIN,
        },
    )
    assert save.status_code == 200
    assert save.json()["summary"]
    assert len(save.json()["allocations"]) == 3

    unlock = client.post("/api/budget/income/unlock", json={"pin": TEST_PIN})
    assert unlock.status_code == 200
    assert unlock.json()["raw_text"]
    assert unlock.json()["locked"] is False
