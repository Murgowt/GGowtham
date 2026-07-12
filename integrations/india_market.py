"""Market data for India: MF NAV (mfapi.in), stocks (yfinance), USD/INR FX."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import httpx

from integrations.app_time import now_app

logger = logging.getLogger(__name__)

MFAPI_BASE = "https://api.mfapi.in"
FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest?from=USD&to=INR"
HTTP_TIMEOUT = 20.0

_fx_cache: tuple[float, datetime] | None = None
_fx_cache_ttl = timedelta(hours=1)


def _normalize_stock_symbol(symbol: str, exchange: str | None = None) -> str:
    sym = symbol.strip().upper()
    if sym.endswith(".NS") or sym.endswith(".BO"):
        return sym
    ex = (exchange or "NSE").upper()
    suffix = ".BO" if ex == "BSE" else ".NS"
    return f"{sym}{suffix}"


def get_usd_inr_rate(*, force_refresh: bool = False) -> tuple[float, datetime]:
    global _fx_cache
    now = now_app()
    if not force_refresh and _fx_cache and (now - _fx_cache[1]) < _fx_cache_ttl:
        return _fx_cache[0], _fx_cache[1]

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(FRANKFURTER_URL)
            resp.raise_for_status()
            rate = float(resp.json()["rates"]["INR"])
            _fx_cache = (rate, now)
            return rate, now
    except Exception:
        logger.exception("Failed to fetch USD/INR rate")
        if _fx_cache:
            return _fx_cache[0], _fx_cache[1]
        return 83.0, now


def search_mf_schemes(query: str, *, limit: int = 20) -> list[dict]:
    q = query.strip()
    if len(q) < 2:
        return []
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(f"{MFAPI_BASE}/mf/search", params={"q": q})
            resp.raise_for_status()
            rows = resp.json()
    except Exception:
        logger.exception("MF scheme search failed")
        return []

    if not isinstance(rows, list):
        return []
    return [
        {
            "scheme_code": int(row["schemeCode"]),
            "scheme_name": row["schemeName"],
        }
        for row in rows[:limit]
        if row.get("schemeCode") and row.get("schemeName")
    ]


def get_mf_nav(scheme_code: int) -> dict | None:
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(f"{MFAPI_BASE}/mf/{scheme_code}/latest")
            resp.raise_for_status()
            payload = resp.json()
    except Exception:
        logger.exception("MF NAV fetch failed for scheme %s", scheme_code)
        return None

    if payload.get("status") != "SUCCESS":
        return None
    data = payload.get("data") or []
    if not data:
        return None
    latest = data[0]
    meta = payload.get("meta") or {}
    return {
        "nav": float(latest["nav"]),
        "date": latest.get("date"),
        "scheme_name": meta.get("scheme_name"),
    }


def get_stock_quote(symbol: str, *, exchange: str | None = None) -> dict | None:
    yf_symbol = _normalize_stock_symbol(symbol, exchange)
    try:
        import yfinance as yf

        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="5d", auto_adjust=False)
        if hist.empty:
            return None
        price = float(hist["Close"].iloc[-1])
        as_of = hist.index[-1].to_pydatetime()
        return {
            "symbol": yf_symbol,
            "price": round(price, 2),
            "as_of": as_of.isoformat(),
        }
    except Exception:
        logger.exception("Stock quote fetch failed for %s", yf_symbol)
        return None
