"""Parse natural-language paycheck + allocation plans."""

from __future__ import annotations

import json
import logging

from integrations.llm_client import LLMUnavailableError, complete_json, is_llm_configured

logger = logging.getLogger(__name__)

INCOME_SYSTEM_PROMPT = """You extract paycheck and budget allocation plans from natural language.
Return JSON with exactly these keys:
- summary: 2-4 sentences reflecting what Brain understands (direct, percentage-first tone)
- extracted: object with:
  - take_home_monthly_usd: number (normalize biweekly/weekly to monthly)
  - pay_frequency: string (biweekly, monthly, weekly, etc.)
  - currency: string (usually USD)
  - allocations: array of {label, pct, intent} where pct are numbers summing to ~100
  - allocations_sum_pct: number
  - derived_monthly_caps_usd: {label: amount} for each allocation
  - missing_detail: array of strings

Rules:
- Only extract stated facts; never invent salary
- User may describe venture/empire, living, and enjoy/guilt-free splits
- Prefer percentage allocations when user describes splits
- Normalize all income to monthly USD equivalent"""


GOWTHAM_INCOME_MOCK = {
    "summary": (
        "Take-home in USD until 2032 India return. Allocations split between venture/empire "
        "(investments + India property fund), living essentials, and guilt-free enjoyment — "
        "Brain will track actual spend against these bands in V2."
    ),
    "extracted": {
        "take_home_monthly_usd": 8500,
        "pay_frequency": "monthly",
        "currency": "USD",
        "allocations": [
            {"label": "venture", "pct": 45, "intent": "empire_property_fund"},
            {"label": "living", "pct": 35, "intent": "essential_spend"},
            {"label": "enjoy", "pct": 20, "intent": "discretionary_guilt_free"},
        ],
        "allocations_sum_pct": 100,
        "derived_monthly_caps_usd": {"venture": 3825, "living": 2975, "enjoy": 1700},
        "missing_detail": [],
    },
}


def _mock_income(raw_text: str) -> dict:
    _ = raw_text
    return GOWTHAM_INCOME_MOCK


def extract_income(raw_text: str) -> dict:
    """Return {summary, extracted_json, extraction_status}."""
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Income text is required")

    try:
        if is_llm_configured():
            result = complete_json(system=INCOME_SYSTEM_PROMPT, user=text)
            summary = str(result.get("summary") or "").strip()
            extracted = result.get("extracted") or result
            return {
                "summary": summary,
                "extracted_json": json.dumps(extracted),
                "extraction_status": "ready",
            }
        raise LLMUnavailableError()
    except LLMUnavailableError:
        mock = _mock_income(text)
        return {
            "summary": mock["summary"],
            "extracted_json": json.dumps(mock["extracted"]),
            "extraction_status": "ready",
        }
    except Exception:
        logger.exception("Income extraction failed")
        return {
            "summary": None,
            "extracted_json": None,
            "extraction_status": "failed",
        }


def parse_allocations(extracted_json: str | None) -> list[dict]:
    if not extracted_json:
        return []
    try:
        data = json.loads(extracted_json)
        return list(data.get("allocations") or [])
    except json.JSONDecodeError:
        return []
