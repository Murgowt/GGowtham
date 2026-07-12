"""CRUD API for manual India investments."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from api.auth import require_auth
from db.database import (
    count_manual_investments,
    create_manual_investment,
    delete_manual_investment,
    get_manual_investment,
    list_manual_investments,
    update_manual_investment,
)
from integrations.india_market import search_mf_schemes

router = APIRouter(prefix="/api/investments", tags=["investments"])

VALID_TYPES = {"fd", "mf", "stock"}


class InvestmentCreateRequest(BaseModel):
    type: str = Field(pattern="^(fd|mf|stock)$")
    name: str = Field(min_length=1, max_length=200)
    invested_inr: float = Field(gt=0)
    details: dict = Field(default_factory=dict)


class InvestmentUpdateRequest(BaseModel):
    type: str = Field(pattern="^(fd|mf|stock)$")
    name: str = Field(min_length=1, max_length=200)
    invested_inr: float = Field(gt=0)
    details: dict = Field(default_factory=dict)


def _parse_date(value: str | None, field: str) -> None:
    if not value:
        raise ValueError(f"{field} is required")
    try:
        date.fromisoformat(value[:10])
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc


def _validate_details(inv_type: str, details: dict, invested_inr: float) -> dict:
    d = dict(details or {})
    if inv_type == "fd":
        principal = float(d.get("principal") or invested_inr)
        if principal <= 0:
            raise ValueError("principal must be positive")
        rate = float(d.get("rate") or 0)
        if rate <= 0:
            raise ValueError("rate is required")
        _parse_date(d.get("start_date"), "start_date")
        _parse_date(d.get("maturity_date"), "maturity_date")
        d.setdefault("compounding", "quarterly")
        d.setdefault("bank", "HDFC")
        d.setdefault("penalty_pct", 1.0)
        d["principal"] = principal
        d["rate"] = rate
    elif inv_type == "mf":
        if not d.get("scheme_code"):
            raise ValueError("scheme_code is required")
        units = float(d.get("units") or 0)
        if units <= 0:
            raise ValueError("units must be positive")
        purchase_nav = float(d.get("purchase_nav") or 0)
        if purchase_nav <= 0:
            purchase_nav = round(invested_inr / units, 4)
        d["units"] = units
        d["purchase_nav"] = purchase_nav
        d["scheme_code"] = int(d["scheme_code"])
    elif inv_type == "stock":
        symbol = (d.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        quantity = float(d.get("quantity") or 0)
        avg_buy = float(d.get("avg_buy_price") or 0)
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if avg_buy <= 0:
            raise ValueError("avg_buy_price must be positive")
        d["symbol"] = symbol
        d.setdefault("exchange", "NSE")
        d["quantity"] = quantity
        d["avg_buy_price"] = avg_buy
    return d


def _serialize(row) -> dict:
    return {
        "id": row.id,
        "type": row.type,
        "name": row.name,
        "currency": row.currency,
        "invested_inr": row.invested_inr,
        "details": row.details_json or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("")
def investments_list(request: Request):
    require_auth(request)
    return {"investments": [_serialize(r) for r in list_manual_investments()]}


@router.get("/count")
def investments_count(request: Request):
    require_auth(request)
    return {"count": count_manual_investments()}


@router.get("/mf/search")
def mf_search(request: Request, q: str = Query(min_length=2)):
    require_auth(request)
    return {"schemes": search_mf_schemes(q)}


@router.get("/{investment_id}")
def investment_detail(request: Request, investment_id: int):
    require_auth(request)
    row = get_manual_investment(investment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Investment not found")
    return _serialize(row)


@router.post("")
def investment_create(request: Request, body: InvestmentCreateRequest):
    require_auth(request)
    if body.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid investment type")
    try:
        details = _validate_details(body.type, body.details, body.invested_inr)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    row = create_manual_investment(
        type=body.type,
        name=body.name.strip(),
        currency="INR",
        invested_inr=body.invested_inr,
        details_json=details,
    )
    return _serialize(row)


@router.put("/{investment_id}")
def investment_update(request: Request, investment_id: int, body: InvestmentUpdateRequest):
    require_auth(request)
    try:
        details = _validate_details(body.type, body.details, body.invested_inr)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    row = update_manual_investment(
        investment_id,
        type=body.type,
        name=body.name.strip(),
        currency="INR",
        invested_inr=body.invested_inr,
        details_json=details,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Investment not found")
    return _serialize(row)


@router.delete("/{investment_id}")
def investment_remove(request: Request, investment_id: int):
    require_auth(request)
    if not delete_manual_investment(investment_id):
        raise HTTPException(status_code=404, detail="Investment not found")
    return {"ok": True}
