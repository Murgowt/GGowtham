import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from snaptrade_client import SnapTrade

from config import settings
from db.database import get_latest_snapshot, get_setting, save_snapshot, set_setting
from integrations.app_time import now_app, to_app_tz

logger = logging.getLogger(__name__)

MOCK_HOLDINGS = [
    {"ticker": "VOO", "shares": 0.39, "price": 688.55, "value": 688.55, "pnl": 19.68, "pnl_pct": 2.9},
    {"ticker": "JPM", "shares": 0.11, "price": 325.93, "value": 325.93, "pnl": 5.28, "pnl_pct": 1.6},
    {"ticker": "QQQM", "shares": 1.07, "price": 304.78, "value": 304.78, "pnl": 47.50, "pnl_pct": 18.5},
    {"ticker": "BA", "shares": 0.61, "price": 222.82, "value": 222.82, "pnl": -13.17, "pnl_pct": -5.6},
    {"ticker": "CVX", "shares": 0.94, "price": 173.94, "value": 173.94, "pnl": 8.20, "pnl_pct": 4.9},
]

SNAPTRADE_USER_ID_KEY = "snaptrade_user_id"
SNAPTRADE_USER_SECRET_KEY = "snaptrade_user_secret"


@dataclass
class PortfolioData:
    total_value: float
    total_invested: float
    total_pnl: float | None
    holdings: list[dict]
    cached: bool
    updated_at: datetime
    source: str


def _total_invested(holdings: list[dict]) -> float:
    total = 0.0
    for h in holdings:
        if "invested" in h:
            total += h["invested"]
        else:
            total += h["value"] - h.get("pnl", 0)
    return round(total, 2)


_cache: PortfolioData | None = None
_cache_at: datetime | None = None
_client: SnapTrade | None = None


def _mock_portfolio() -> PortfolioData:
    total_value = sum(h["value"] for h in MOCK_HOLDINGS)
    total_pnl = sum(h["pnl"] for h in MOCK_HOLDINGS)
    total_invested = _total_invested(MOCK_HOLDINGS)
    now = now_app()
    return PortfolioData(
        total_value=round(total_value, 2),
        total_invested=total_invested,
        total_pnl=round(total_pnl, 2),
        holdings=MOCK_HOLDINGS,
        cached=False,
        updated_at=now,
        source="mock",
    )


def _snapshot_to_portfolio(snapshot) -> PortfolioData:
    captured = to_app_tz(snapshot.captured_at)
    holdings = snapshot.holdings_json or []
    return PortfolioData(
        total_value=snapshot.total_value or 0.0,
        total_invested=_total_invested(holdings),
        total_pnl=snapshot.total_pnl,
        holdings=holdings,
        cached=True,
        updated_at=captured,
        source="snapshot",
    )


def is_configured() -> bool:
    return bool(settings.snaptrade_client_id and settings.snaptrade_consumer_key)


def is_personal_client() -> bool:
    return settings.snaptrade_client_id.startswith("PERS-")


def get_client() -> SnapTrade:
    global _client
    if not is_configured():
        raise RuntimeError("SnapTrade credentials not configured")
    if _client is None:
        _client = SnapTrade(
            client_id=settings.snaptrade_client_id,
            consumer_key=settings.snaptrade_consumer_key,
        )
    return _client


def get_user_credentials() -> tuple[str, str] | None:
    user_id = get_setting(SNAPTRADE_USER_ID_KEY) or settings.snaptrade_user_id
    user_secret = get_setting(SNAPTRADE_USER_SECRET_KEY) or settings.snaptrade_user_secret
    if user_id and user_secret:
        return user_id, user_secret
    return None


def _list_personal_user_ids() -> list[str]:
    client = get_client()
    response = client.authentication.list_snap_trade_users()
    body = response.body
    if isinstance(body, list):
        return [str(u) for u in body]
    return []


def _rotate_personal_user_secret(user_id: str) -> str:
    client = get_client()
    existing = get_user_credentials()
    body = {"userId": user_id}
    if existing and existing[0] == user_id:
        body["userSecret"] = existing[1]

    response = client.authentication.reset_snap_trade_user_secret(
        body=body,
        user_id=user_id,
        user_secret=body.get("userSecret"),
    )
    result = response.body
    secret = getattr(result, "user_secret", None) or getattr(result, "userSecret", None)
    if not secret and isinstance(result, dict):
        secret = result.get("userSecret") or result.get("user_secret")
    if not secret:
        raise RuntimeError("Could not obtain SnapTrade user secret")
    return secret


def ensure_snaptrade_user() -> tuple[str, str]:
    existing = get_user_credentials()
    if existing:
        return existing

    if is_personal_client():
        user_ids = _list_personal_user_ids()
        if not user_ids:
            raise RuntimeError(
                "No SnapTrade user found for your Personal API key. "
                "Check your key in the SnapTrade dashboard."
            )
        user_id = user_ids[0]

        if settings.snaptrade_user_secret:
            secret = settings.snaptrade_user_secret
        else:
            try:
                secret = _rotate_personal_user_secret(user_id)
            except Exception:
                logger.exception("Failed to rotate personal user secret")
                raise RuntimeError(
                    "SnapTrade user secret required. Add SNAPTRADE_USER_SECRET to .env "
                    "(SnapTrade dashboard → API), or contact SnapTrade support."
                ) from None

        set_setting(SNAPTRADE_USER_ID_KEY, user_id)
        set_setting(SNAPTRADE_USER_SECRET_KEY, secret)
        return user_id, secret

    client = get_client()
    user_id = f"brain-{uuid.uuid4().hex[:12]}"
    response = client.authentication.register_snap_trade_user(user_id=user_id)
    body = response.body
    registered_id = getattr(body, "user_id", None) or user_id
    user_secret = getattr(body, "user_secret", None)
    if not user_secret:
        raise RuntimeError("SnapTrade user registration failed")

    set_setting(SNAPTRADE_USER_ID_KEY, registered_id)
    set_setting(SNAPTRADE_USER_SECRET_KEY, user_secret)
    return registered_id, user_secret


def get_connection_portal_url() -> str:
    user_id, user_secret = ensure_snaptrade_user()
    client = get_client()
    redirect = f"{settings.app_base_url.rstrip('/')}/?connected=1"
    response = client.authentication.login_snap_trade_user(
        user_id=user_id,
        user_secret=user_secret,
        broker="ROBINHOOD",
        immediate_redirect=True,
        custom_redirect=redirect,
        connection_type="read",
    )
    body = response.body
    redirect_uri = getattr(body, "redirect_uri", None) or getattr(body, "redirectURI", None)
    if not redirect_uri and isinstance(body, dict):
        redirect_uri = body.get("redirectURI") or body.get("redirect_uri")
    if not redirect_uri:
        raise RuntimeError("Failed to generate SnapTrade connection portal URL")
    return redirect_uri


def has_brokerage_connection() -> bool:
    if settings.mock_integrations:
        return True
    if not is_configured():
        return False
    try:
        return len(list_accounts()) > 0
    except Exception:
        logger.exception("Failed to check SnapTrade connection")
        return False


def list_accounts() -> list:
    user_id, user_secret = get_user_credentials()
    if not user_id or not user_secret:
        user_id, user_secret = ensure_snaptrade_user()

    client = get_client()
    response = client.account_information.list_user_accounts(
        user_id=user_id,
        user_secret=user_secret,
    )
    body = response.body
    if isinstance(body, list):
        return body
    return getattr(body, "accounts", None) or []


def _position_to_holding(position) -> dict | None:
    if isinstance(position, dict):
        symbol_obj = position.get("symbol") or {}
        symbol = symbol_obj.get("symbol") if isinstance(symbol_obj, dict) else symbol_obj
        if isinstance(symbol, dict):
            ticker = symbol.get("raw_symbol") or symbol.get("symbol")
        else:
            ticker = symbol
        units = float(position.get("units") or 0)
        price = float(position.get("price") or 0)
        value = float(position.get("market_value") or units * price)
        open_pnl = position.get("open_pnl")
        pnl = float(open_pnl) if open_pnl is not None else 0.0
        avg_cost = float(position.get("average_purchase_price") or 0)
    else:
        symbol_obj = getattr(position, "symbol", None)
        ticker = None
        if symbol_obj is not None:
            symbol = getattr(symbol_obj, "symbol", None)
            ticker = getattr(symbol, "raw_symbol", None) or getattr(symbol, "symbol", None)
            if ticker is None and isinstance(symbol, dict):
                ticker = symbol.get("raw_symbol") or symbol.get("symbol")
        if not ticker:
            ticker = getattr(position, "symbol", "???")
            if not isinstance(ticker, str):
                ticker = "???"
        units = float(getattr(position, "units", 0) or 0)
        price = float(getattr(position, "price", 0) or 0)
        value = float(getattr(position, "market_value", None) or units * price)
        open_pnl = getattr(position, "open_pnl", None)
        pnl = float(open_pnl) if open_pnl is not None else 0.0
        avg_cost = float(getattr(position, "average_purchase_price", 0) or 0)

    if not ticker:
        return None

    cost_basis = avg_cost * units if avg_cost and units else value - pnl
    pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0.0

    return {
        "ticker": str(ticker).upper(),
        "shares": round(units, 4),
        "price": round(price, 2),
        "value": round(value, 2),
        "invested": round(cost_basis, 2),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
    }


def _fetch_live_holdings() -> PortfolioData | None:
    user_id, user_secret = get_user_credentials()
    if not user_id or not user_secret:
        user_id, user_secret = ensure_snaptrade_user()

    client = get_client()
    accounts = list_accounts()
    if not accounts:
        return None

    holdings: list[dict] = []
    total_value = 0.0
    total_invested = 0.0
    total_pnl = 0.0

    for account in accounts:
        account_id = (
            account.get("id") if isinstance(account, dict)
            else getattr(account, "id", None) or getattr(account, "account_id", None)
        )
        if not account_id:
            continue
        response = client.account_information.get_user_account_positions(
            account_id=account_id,
            user_id=user_id,
            user_secret=user_secret,
        )
        positions = response.body
        if not isinstance(positions, list):
            positions = getattr(positions, "positions", None) or []
        for position in positions:
            holding = _position_to_holding(position)
            if holding and holding["shares"] > 0:
                holdings.append(holding)
                total_value += holding["value"]
                total_invested += holding["invested"]
                total_pnl += holding["pnl"]

    if not holdings:
        return None

    holdings.sort(key=lambda h: h["value"], reverse=True)
    now = now_app()
    save_snapshot(round(total_value, 2), round(total_pnl, 2), holdings)
    return PortfolioData(
        total_value=round(total_value, 2),
        total_invested=round(total_invested, 2),
        total_pnl=round(total_pnl, 2),
        holdings=holdings,
        cached=False,
        updated_at=now,
        source="live",
    )


def get_portfolio(*, force_refresh: bool = False) -> PortfolioData:
    global _cache, _cache_at

    if settings.mock_integrations:
        return _mock_portfolio()

    if not is_configured():
        raise RuntimeError("SnapTrade is not configured")

    if not has_brokerage_connection():
        raise RuntimeError("Robinhood not connected. Tap Connect Robinhood first.")

    now = now_app()
    cache_ttl = timedelta(minutes=settings.portfolio_cache_minutes)

    if not force_refresh and _cache and _cache_at and (now - _cache_at) < cache_ttl:
        return PortfolioData(
            total_value=_cache.total_value,
            total_invested=_cache.total_invested,
            total_pnl=_cache.total_pnl,
            holdings=_cache.holdings,
            cached=True,
            updated_at=_cache.updated_at,
            source="cache",
        )

    live = _fetch_live_holdings()
    if live:
        _cache = live
        _cache_at = now
        return live

    snapshot = get_latest_snapshot()
    if snapshot:
        return _snapshot_to_portfolio(snapshot)

    raise RuntimeError("Unable to fetch portfolio and no cached snapshot available")
