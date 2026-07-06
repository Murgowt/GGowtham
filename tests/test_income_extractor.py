"""Tests for income NL extraction and PIN auth."""

import pytest
from fastapi import HTTPException

from api.auth import require_income_pin
from integrations.income_extractor import extract_income, parse_allocations


INCOME_TEXT = """
Take-home about $8,500/month in USD until 2032. I want 45% to venture/empire,
35% living expenses, 20% enjoy guilt-free.
"""


def test_extract_income_mock():
    result = extract_income(INCOME_TEXT)
    assert result["extraction_status"] == "ready"
    assert result["summary"]
    assert result["extracted_json"]
    data = __import__("json").loads(result["extracted_json"])
    assert data["take_home_monthly_usd"] == 8500
    assert sum(a["pct"] for a in data["allocations"]) == 100


def test_parse_allocations_empty():
    assert parse_allocations(None) == []


def test_require_income_pin_missing():
    with pytest.raises(HTTPException) as exc:
        require_income_pin(None)
    assert exc.value.status_code == 401


def test_require_income_pin_invalid(monkeypatch):
    monkeypatch.setattr("api.auth.verify_pin", lambda p: False)
    with pytest.raises(HTTPException) as exc:
        require_income_pin("wrong")
    assert exc.value.status_code == 403
