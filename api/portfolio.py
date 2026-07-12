from fastapi import APIRouter, HTTPException, Request

from api.auth import require_auth
from db.database import count_manual_investments
from integrations.portfolio_service import get_merged_portfolio
from integrations.snaptrade import (
    get_connection_portal_url,
    has_brokerage_connection,
    is_configured,
)

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/portfolio")
def portfolio(request: Request, refresh: bool = False):
    require_auth(request)
    try:
        data = get_merged_portfolio(force_refresh=refresh)
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
        "fx_rate": data.fx_rate,
        "fx_as_of": data.fx_as_of.isoformat() if data.fx_as_of else None,
        "manual_count": count_manual_investments(),
    }


@router.get("/connection/status")
def connection_status(request: Request):
    require_auth(request)
    manual_count = count_manual_investments()
    return {
        "configured": is_configured(),
        "connected": has_brokerage_connection(),
        "manual_count": manual_count,
        "has_holdings": has_brokerage_connection() or manual_count > 0,
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
