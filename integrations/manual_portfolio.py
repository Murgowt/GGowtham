"""Value manual India investments and normalize to portfolio holding shape."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime

from db.database import list_manual_investments, update_manual_investment_details
from integrations.india_fd import fd_valuation
from integrations.india_market import get_mf_nav, get_stock_quote, get_usd_inr_rate

logger = logging.getLogger(__name__)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _value_fd(row, details: dict, as_of: date) -> dict:
    principal = float(details.get("principal") or row.invested_inr)
    rate_pct = float(details.get("rate") or 0)
    start_date = _parse_date(details.get("start_date"))
    maturity_date = _parse_date(details.get("maturity_date"))
    if not start_date or not maturity_date:
        raise ValueError(f"FD {row.id} missing start_date or maturity_date")

    compounding = details.get("compounding") or "quarterly"
    penalty_pct = float(details.get("penalty_pct") or 1.0)
    val = fd_valuation(
        principal=principal,
        rate_pct=rate_pct,
        start_date=start_date,
        maturity_date=maturity_date,
        as_of=as_of,
        compounding=compounding,
        penalty_pct=penalty_pct,
    )
    value_inr = val["close_today_inr"]
    invested_inr = float(row.invested_inr)
    pnl_inr = round(value_inr - invested_inr, 2)
    pnl_pct = round(pnl_inr / invested_inr * 100, 2) if invested_inr else 0.0

    return {
        "ticker": row.name,
        "type": "fd",
        "shares": 1.0,
        "price": value_inr,
        "value_inr": value_inr,
        "invested_inr": invested_inr,
        "pnl_inr": pnl_inr,
        "pnl_pct": pnl_pct,
        "region": "IN",
        "source": "manual",
        "currency": "INR",
        "stale": False,
        "meta": {
            **val,
            "bank": details.get("bank") or "HDFC",
            "rate_pct": rate_pct,
            "compounding": compounding,
        },
    }


def _value_mf(row, details: dict, *, force_refresh: bool = False) -> dict:
    scheme_code = int(details["scheme_code"])
    units = float(details.get("units") or 0)
    purchase_nav = float(details.get("purchase_nav") or 0)
    invested_inr = float(row.invested_inr)
    if units <= 0:
        raise ValueError(f"MF {row.id} missing units")

    quote = None
    stale = False
    if force_refresh:
        quote = get_mf_nav(scheme_code)
        if quote:
            details["last_quote"] = quote
            update_manual_investment_details(row.id, details)
    elif details.get("last_quote"):
        quote = details["last_quote"]
        stale = True

    if quote:
        nav = float(quote["nav"])
    elif purchase_nav > 0:
        nav = purchase_nav
        stale = True
    else:
        nav = round(invested_inr / units, 4)
        stale = True

    value_inr = round(units * nav, 2)
    if purchase_nav > 0:
        cost_basis = round(units * purchase_nav, 2)
    else:
        cost_basis = invested_inr
    pnl_inr = round(value_inr - cost_basis, 2)
    pnl_pct = round(pnl_inr / cost_basis * 100, 2) if cost_basis else 0.0

    ticker = details.get("scheme_name") or row.name
    display_name = row.name or ticker
    return {
        "ticker": display_name,
        "type": "mf",
        "shares": round(units, 4),
        "price": nav,
        "value_inr": value_inr,
        "invested_inr": invested_inr,
        "pnl_inr": pnl_inr,
        "pnl_pct": pnl_pct,
        "region": "IN",
        "source": "manual",
        "currency": "INR",
        "stale": stale,
        "meta": {
            "scheme_code": scheme_code,
            "nav_date": quote.get("date") if quote else details.get("last_quote", {}).get("date"),
            "purchase_nav": purchase_nav,
        },
    }


def _value_stock(row, details: dict, *, force_refresh: bool = False) -> dict:
    symbol = details.get("symbol") or row.name
    exchange = details.get("exchange")
    quantity = float(details.get("quantity") or 0)
    avg_buy = float(details.get("avg_buy_price") or 0)
    if quantity <= 0 or avg_buy <= 0:
        raise ValueError(f"Stock {row.id} missing quantity or avg_buy_price")

    quote = None
    stale = False
    if force_refresh:
        quote = get_stock_quote(symbol, exchange=exchange)
        if quote:
            details["last_quote"] = quote
            if not details.get("symbol"):
                details["symbol"] = quote["symbol"]
            update_manual_investment_details(row.id, details)
    elif details.get("last_quote"):
        quote = details["last_quote"]
        stale = True

    if quote:
        price = float(quote["price"])
    elif avg_buy > 0:
        price = avg_buy
        stale = True
    else:
        raise ValueError(f"Stock {row.id}: unable to fetch quote")

    value_inr = round(quantity * price, 2)
    invested_inr = float(row.invested_inr)
    cost_basis = round(quantity * avg_buy, 2)
    pnl_inr = round(value_inr - cost_basis, 2)
    pnl_pct = round(pnl_inr / cost_basis * 100, 2) if cost_basis else 0.0

    return {
        "ticker": details.get("symbol") or symbol,
        "type": "stock",
        "shares": round(quantity, 4),
        "price": price,
        "value_inr": value_inr,
        "invested_inr": invested_inr,
        "pnl_inr": pnl_inr,
        "pnl_pct": pnl_pct,
        "region": "IN",
        "source": "manual",
        "currency": "INR",
        "stale": stale,
        "meta": {
            "avg_buy_price": avg_buy,
            "exchange": exchange or "NSE",
        },
    }


def _value_investment(row, as_of: date, *, force_refresh: bool = False) -> dict | None:
    details = dict(row.details_json or {})
    try:
        if row.type == "fd":
            return _value_fd(row, details, as_of)
        if row.type == "mf":
            return _value_mf(row, details, force_refresh=force_refresh)
        if row.type == "stock":
            return _value_stock(row, details, force_refresh=force_refresh)
    except Exception:
        logger.exception("Failed to value manual investment %s", row.id)
    return None


def _inr_to_usd(amount_inr: float, fx_rate: float) -> float:
    if fx_rate <= 0:
        return 0.0
    return round(amount_inr / fx_rate, 2)


def _holding_from_row(row, valued: dict, fx_rate: float) -> dict:
    return {
        **valued,
        "id": row.id,
        "name": row.name,
        "value": _inr_to_usd(valued["value_inr"], fx_rate),
        "invested": _inr_to_usd(valued["invested_inr"], fx_rate),
        "pnl": _inr_to_usd(valued["pnl_inr"], fx_rate),
    }


def get_manual_holdings(*, force_refresh: bool = False) -> tuple[list[dict], float, datetime | None]:
    """Return INR holdings, USD/INR rate, and FX timestamp."""
    rows = list_manual_investments()
    if not rows:
        return [], 0.0, None

    as_of = date.today()
    holdings: list[dict] = []

    if force_refresh:
        fx_rate, fx_at = get_usd_inr_rate(force_refresh=True)
        for row in rows:
            valued = _value_investment(row, as_of, force_refresh=True)
            if valued:
                holdings.append(_holding_from_row(row, valued, fx_rate))
    else:
        max_workers = min(8, len(rows) + 1)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            fx_future = executor.submit(get_usd_inr_rate, force_refresh=False)
            valued_futures = {
                executor.submit(_value_investment, row, as_of, force_refresh=False): row
                for row in rows
            }
            fx_rate, fx_at = fx_future.result()
            for future in as_completed(valued_futures):
                row = valued_futures[future]
                valued = future.result()
                if valued:
                    holdings.append(_holding_from_row(row, valued, fx_rate))

    holdings.sort(key=lambda h: h["value"], reverse=True)
    return holdings, fx_rate, fx_at
