"""Tests for manual investments API and merged portfolio."""

import os
import tempfile
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.name}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["MOCK_INTEGRATIONS"] = "true"

from config import settings  # noqa: E402
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


def _mock_fx():
    return patch(
        "integrations.manual_portfolio.get_usd_inr_rate",
        return_value=(83.0, __import__("integrations.app_time", fromlist=["now_app"]).now_app()),
    )


def _mock_mf_nav():
    return patch(
        "integrations.manual_portfolio.get_mf_nav",
        return_value={"nav": 100.0, "date": "01-01-2025", "scheme_name": "Test Fund"},
    )


def _mock_stock_quote():
    return patch(
        "integrations.manual_portfolio.get_stock_quote",
        return_value={"symbol": "RELIANCE.NS", "price": 2500.0, "as_of": "2025-01-01T00:00:00"},
    )


def test_investment_fd_crud_and_portfolio():
    _login()
    start = date.today() - timedelta(days=120)
    maturity = date.today() + timedelta(days=245)

    create = client.post(
        "/api/investments",
        json={
            "type": "fd",
            "name": "HDFC FD",
            "invested_inr": 110_000,
            "details": {
                "principal": 110_000,
                "rate": 7.25,
                "start_date": start.isoformat(),
                "maturity_date": maturity.isoformat(),
                "bank": "HDFC",
            },
        },
    )
    assert create.status_code == 200, create.text
    inv_id = create.json()["id"]

    with _mock_fx():
        portfolio = client.get("/api/portfolio?refresh=true")
    assert portfolio.status_code == 200
    body = portfolio.json()
    india = [h for h in body["holdings"] if h.get("region") == "IN"]
    assert len(india) >= 1
    assert body["fx_rate"] == 83.0
    assert body["total_value"] > 0

    listing = client.get("/api/investments")
    assert listing.status_code == 200
    assert any(i["id"] == inv_id for i in listing.json()["investments"])

    delete = client.delete(f"/api/investments/{inv_id}")
    assert delete.status_code == 200


def test_investment_mf_valuation():
    _login()
    create = client.post(
        "/api/investments",
        json={
            "type": "mf",
            "name": "Test MF",
            "invested_inr": 10_000,
            "details": {
                "scheme_code": 125497,
                "scheme_name": "Test Fund",
                "units": 100,
                "purchase_nav": 90,
            },
        },
    )
    assert create.status_code == 200
    inv_id = create.json()["id"]

    with _mock_fx(), _mock_mf_nav():
        portfolio = client.get("/api/portfolio?refresh=true")
    assert portfolio.status_code == 200
    mf = next(h for h in portfolio.json()["holdings"] if h.get("type") == "mf")
    assert mf["value_inr"] == 10_000
    assert mf["pnl_inr"] == 1_000

    client.delete(f"/api/investments/{inv_id}")


def test_investment_stock_valuation():
    _login()
    create = client.post(
        "/api/investments",
        json={
            "type": "stock",
            "name": "Reliance",
            "invested_inr": 25_000,
            "details": {
                "symbol": "RELIANCE",
                "exchange": "NSE",
                "quantity": 10,
                "avg_buy_price": 2500,
            },
        },
    )
    assert create.status_code == 200
    inv_id = create.json()["id"]

    with _mock_fx(), _mock_stock_quote():
        portfolio = client.get("/api/portfolio?refresh=true")
    assert portfolio.status_code == 200
    stock = next(h for h in portfolio.json()["holdings"] if h.get("type") == "stock")
    assert stock["value_inr"] == 25_000
    assert stock["pnl_inr"] == 0

    client.delete(f"/api/investments/{inv_id}")


def test_connection_status_with_manual_only():
    _login()
    start = date.today() - timedelta(days=30)
    maturity = date.today() + timedelta(days=335)
    client.post(
        "/api/investments",
        json={
            "type": "fd",
            "name": "HDFC FD",
            "invested_inr": 50_000,
            "details": {
                "principal": 50_000,
                "rate": 7.0,
                "start_date": start.isoformat(),
                "maturity_date": maturity.isoformat(),
            },
        },
    )
    status = client.get("/api/connection/status")
    assert status.status_code == 200
    assert status.json()["manual_count"] >= 1
    assert status.json()["has_holdings"] is True
