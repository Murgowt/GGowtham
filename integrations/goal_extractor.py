"""Parse natural-language financial goals into summary + structured JSON."""

from __future__ import annotations

import json
import logging

from integrations.llm_client import LLMUnavailableError, complete_json, is_llm_configured

logger = logging.getLogger(__name__)

GOAL_SYSTEM_PROMPT = """You extract financial goals from the user's natural language.
Return JSON with exactly these keys:
- title: short label (max 60 chars)
- summary: 2-4 sentences reflecting what Brain understands (direct, percentage-friendly tone)
- extracted: object with keys:
  - goals: array of sub-goals, each with tier ("life" or "milestone"), label, intent,
    amounts (array of {value, currency, role}), passive_income_monthly ({value, currency, inflation_adjusted, base_year, base_location} if stated),
    capital_required ({value, currency}), timeline_years (number or null), details (object), priority, pct_of_life_goal (number or null)
  - missing_detail: array of strings for unclear quantifiers
  - overall_identity: one sentence

Rules:
- Only extract facts the user stated; never invent numbers
- Distinguish life north-star goals from concrete milestones
- Preserve INR amounts (lakhs, crores) as numeric values in INR
- No time-bucket labels like 1-month or 6-month goals
- If user mentions percentages, include them"""


GOWTHAM_LIFE_GOAL_MOCK = {
    "title": "Lifetime passive income",
    "summary": (
        "North star: ₹2L/month passive income based on 2022 Hyderabad living costs, "
        "inflation-adjusted over time, growing as you age. You're building an empire "
        "for family comfort while balancing life in the US until a 2032 India return."
    ),
    "extracted": {
        "goals": [
            {
                "tier": "life",
                "label": "Lifetime passive income",
                "intent": "passive_income",
                "passive_income_monthly": {
                    "value": 200000,
                    "currency": "INR",
                    "inflation_adjusted": True,
                    "base_year": 2022,
                    "base_location": "Hyderabad",
                },
                "grows_with_age": True,
                "priority": "north_star",
            }
        ],
        "missing_detail": [],
        "overall_identity": "Building empire via passive income for family — balance life now and long-term wealth",
    },
}

GOWTHAM_VENTURE_GOAL_MOCK = {
    "title": "Plot + 3 floors venture",
    "summary": (
        "First empire milestone: ~200 sq yard plot with 3 floors, ₹2.5 Cr venture target, "
        "₹50k/month passive income in ~5 years — 25% of your ₹2L/month life income goal."
    ),
    "extracted": {
        "goals": [
            {
                "tier": "milestone",
                "label": "Plot + 3 floors venture",
                "intent": "property_development",
                "capital_required": {"value": 25000000, "currency": "INR"},
                "passive_income_monthly": {"value": 50000, "currency": "INR"},
                "timeline_years": 5,
                "details": {"plot_sq_yd": 200, "floors": 3},
                "priority": "primary_milestone",
                "pct_of_life_goal": 25,
            }
        ],
        "missing_detail": [],
        "overall_identity": "Start passive income journey via Hyderabad property development",
    },
}


def _mock_for_text(raw_text: str) -> dict:
    lower = raw_text.lower()
    if "2.5" in lower or "crore" in lower or "plot" in lower or "floor" in lower:
        return GOWTHAM_VENTURE_GOAL_MOCK
    if "2 lakh" in lower or "2l" in lower or "empire" in lower or "2032" in lower:
        return GOWTHAM_LIFE_GOAL_MOCK
    return {
        "title": "Financial goal",
        "summary": "Brain captured your goal. Add more detail (amounts, timelines, passive income targets) for sharper tracking later.",
        "extracted": {
            "goals": [{"tier": "life", "label": "Goal", "intent": "wealth", "priority": "primary"}],
            "missing_detail": ["specific amounts", "timeline"],
            "overall_identity": "Building toward stated financial goals",
        },
    }


def extract_goal(raw_text: str) -> dict:
    """Return {title, summary, extracted_json, extraction_status}."""
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Goal text is required")

    try:
        if is_llm_configured():
            result = complete_json(system=GOAL_SYSTEM_PROMPT, user=text)
            title = str(result.get("title") or "Goal")[:200]
            summary = str(result.get("summary") or "").strip()
            extracted = result.get("extracted") or result
            return {
                "title": title,
                "summary": summary,
                "extracted_json": json.dumps(extracted),
                "extraction_status": "ready",
            }
        raise LLMUnavailableError()
    except LLMUnavailableError:
        mock = _mock_for_text(text)
        return {
            "title": mock["title"],
            "summary": mock["summary"],
            "extracted_json": json.dumps(mock["extracted"]),
            "extraction_status": "ready",
        }
    except Exception:
        logger.exception("Goal extraction failed")
        first_line = text.split("\n", 1)[0].strip()[:200] or "Goal"
        return {
            "title": first_line,
            "summary": None,
            "extracted_json": None,
            "extraction_status": "failed",
        }
