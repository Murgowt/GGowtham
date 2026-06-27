from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from api.auth import require_auth
from integrations import plaid_client, splitwise_client
from integrations.spending import (
    get_spending,
    get_spending_logos,
    get_spending_status,
    invalidate_spending_cache,
)
from db.database import set_splitwise_api_key

router = APIRouter(prefix="/api", tags=["spending"])


class SplitwiseConfigureRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=500)


class PlaidExchangeRequest(BaseModel):
    public_token: str = Field(min_length=1)


class PlaidDisconnectRequest(BaseModel):
    item_id: str = Field(min_length=1)


@router.get("/spending/status")
def spending_status(request: Request):
    require_auth(request)
    return get_spending_status()


@router.get("/spending/transactions")
def spending_transactions(request: Request, response: Response, refresh: bool = False, days: int = 30):
    require_auth(request)
    response.headers["Cache-Control"] = "no-store"
    days = max(1, min(days, 90))
    try:
        data = get_spending(force_refresh=refresh, days=days)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "transactions": data.transactions,
        "summary": data.summary,
        "logos": get_spending_logos(),
        "cached": data.cached,
        "source": data.source,
        "updated_at": data.updated_at.isoformat(),
    }


@router.get("/spending/summary")
def spending_summary(request: Request, refresh: bool = False, days: int = 30):
    require_auth(request)
    days = max(1, min(days, 90))
    data = get_spending(force_refresh=refresh, days=days)
    return {
        "summary": data.summary,
        "cached": data.cached,
        "source": data.source,
        "updated_at": data.updated_at.isoformat(),
    }


@router.post("/splitwise/configure")
def splitwise_configure(request: Request, body: SplitwiseConfigureRequest):
    require_auth(request)
    set_splitwise_api_key(body.api_key.strip())
    invalidate_spending_cache()
    if not splitwise_client.is_configured():
        raise HTTPException(status_code=400, detail="Invalid Splitwise API key")
    try:
        splitwise_client.get_current_user_id()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "configured": True}


@router.post("/plaid/link-token")
def plaid_link_token(request: Request):
    require_auth(request)
    if not plaid_client.is_configured():
        raise HTTPException(status_code=503, detail="Plaid credentials not configured")
    try:
        token = plaid_client.create_link_token()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"link_token": token}


@router.post("/plaid/exchange")
def plaid_exchange(request: Request, body: PlaidExchangeRequest):
    require_auth(request)
    if not plaid_client.is_configured():
        raise HTTPException(status_code=503, detail="Plaid credentials not configured")
    try:
        result = plaid_client.connect_item(body.public_token)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Plaid connection failed") from exc
    return result


@router.post("/plaid/disconnect")
def plaid_disconnect(request: Request, body: PlaidDisconnectRequest):
    require_auth(request)
    plaid_client.disconnect_item(body.item_id)
    return {"ok": True}
