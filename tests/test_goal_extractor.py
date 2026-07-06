"""Tests for goal NL extraction."""

from integrations.goal_extractor import (
    GOWTHAM_LIFE_GOAL_MOCK,
    GOWTHAM_VENTURE_GOAL_MOCK,
    extract_goal,
)


LIFE_TEXT = """
I am Gowtham. My life financial goal is ₹2 lakhs per month passive income
based on 2022 Hyderabad expenses, inflation adjusted. I want to return to India by 2032.
"""

VENTURE_TEXT = """
I want to buy a 200 sq yard plot and build 3 floors. Venture worth ₹2.5 Crores.
Expected passive income ₹50,000 per month. Finish in 5 years.
"""


def test_extract_life_goal_mock():
    result = extract_goal(LIFE_TEXT)
    assert result["extraction_status"] == "ready"
    assert "2" in result["summary"] or "passive" in result["summary"].lower()
    assert result["title"]


def test_extract_venture_goal_mock():
    result = extract_goal(VENTURE_TEXT)
    assert result["extraction_status"] == "ready"
    assert "2.5" in result["summary"] or "50" in result["summary"]
    assert result["extracted_json"]
    assert "25000000" in result["extracted_json"] or "2.5" in result["summary"]


def test_gowtham_mock_fixtures_have_key_fields():
    venture = GOWTHAM_VENTURE_GOAL_MOCK["extracted"]["goals"][0]
    assert venture["capital_required"]["value"] == 25000000
    assert venture["passive_income_monthly"]["value"] == 50000
    assert venture["pct_of_life_goal"] == 25

    life = GOWTHAM_LIFE_GOAL_MOCK["extracted"]["goals"][0]
    assert life["passive_income_monthly"]["value"] == 200000
    assert life["passive_income_monthly"]["inflation_adjusted"] is True
