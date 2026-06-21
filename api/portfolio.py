from fastapi import APIRouter, HTTPException, Request

from api.auth import require_auth
from integrations.snaptrade import (
    get_connection_portal_url,
    get_portfolio,
    has_brokerage_connection,
    is_configured,
)

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/portfolio")
def portfolio(request: Request, refresh: bool = False):
    require_auth(request)
    try:
        data = get_portfolio(force_refresh=refresh)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "total_value": data.total_value,
        "total_invested": data.total_invested,
        "total_pnl": data.total_pnl,
        "holdings": data.holdings,
        "cached": data.cached,
        "source": data.source,
        "updated_at": data.updated_at.isoformat(),
    }


@router.get("/connection/status")
def connection_status(request: Request):
    require_auth(request)
    return {
        "configured": is_configured(),
        "connected": has_brokerage_connection(),
    }


@router.post("/connection/portal")
def connection_portal(request: Request):
    require_auth(request)
    if not is_configured():
        raise HTTPException(status_code=503, detail="SnapTrade credentials not configured")
    try:
        url = get_connection_portal_url()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"url": url}
