"""Budget API — income (PIN-gated) and status."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import require_auth, require_income_pin
from db.database import get_income_profile, income_profile_configured, upsert_income_profile
from integrations.income_extractor import extract_income, parse_allocations
from integrations.llm_client import is_llm_configured

router = APIRouter(prefix="/api/budget", tags=["budget"])


class IncomePinRequest(BaseModel):
    pin: str = Field(min_length=1, max_length=20)


class IncomeSaveRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    pin: str = Field(min_length=1, max_length=20)


def _income_payload(profile, *, include_raw: bool = False) -> dict:
    allocations = parse_allocations(profile.extracted_json)
    payload = {
        "configured": True,
        "locked": False,
        "summary": profile.summary,
        "allocations": allocations,
        "extraction_status": profile.extraction_status,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }
    if include_raw:
        payload["raw_text"] = profile.raw_text
        if profile.extracted_json:
            try:
                payload["extracted"] = json.loads(profile.extracted_json)
            except json.JSONDecodeError:
                payload["extracted"] = None
    return payload


@router.get("/income/status")
def income_status(request: Request):
    require_auth(request)
    configured = income_profile_configured()
    return {
        "configured": configured,
        "locked": True,
        "llm_configured": is_llm_configured(),
    }


@router.get("/income")
def income_locked(request: Request):
    """Public income endpoint — no salary without PIN unlock."""
    require_auth(request)
    configured = income_profile_configured()
    return {"locked": True, "configured": configured}


@router.post("/income/unlock")
def income_unlock(request: Request, body: IncomePinRequest):
    require_auth(request)
    require_income_pin(body.pin)

    profile = get_income_profile()
    if not profile or not profile.raw_text.strip():
        return {"locked": False, "configured": False}

    return _income_payload(profile, include_raw=True) | {"locked": False}


@router.put("/income")
def income_save(request: Request, body: IncomeSaveRequest):
    require_auth(request)
    require_income_pin(body.pin)

    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Income text is required")

    try:
        extracted = extract_income(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    profile = upsert_income_profile(
        raw_text=text,
        summary=extracted.get("summary"),
        extracted_json=extracted.get("extracted_json"),
        extraction_status=extracted.get("extraction_status") or "failed",
    )
    return _income_payload(profile, include_raw=True)
