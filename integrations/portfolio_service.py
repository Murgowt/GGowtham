"""Merged portfolio: Robinhood (SnapTrade) + manual India investments."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

from config import settings
from db.database import count_manual_investments
from integrations.app_time import now_app
from integrations.manual_portfolio import get_manual_holdings
from integrations.snaptrade import (
    PortfolioData,
    _mock_portfolio,
    _total_invested,
    get_portfolio as get_snaptrade_portfolio,
    has_brokerage_connection,
    is_configured,
)

logger = logging.getLogger(__name__)


@dataclass
class MergedPortfolioData:
    total_value: float
    total_invested: float
    total_pnl: float | None
    holdings: list[dict]
    cached: bool
    updated_at: datetime
    source: str
    fx_rate: float | None = None
    fx_as_of: datetime | None = None


def _tag_us_holdings(holdings: list[dict]) -> list[dict]:
    tagged = []
    for h in holdings:
        row = dict(h)
        row.setdefault("region", "US")
        row.setdefault("source", "robinhood")
        row.setdefault("type", "equity")
        row.setdefault("currency", "USD")
        row["value_inr"] = None
        row["pnl_inr"] = None
        tagged.append(row)
    return tagged


def _merge_holdings(us: list[dict], india: list[dict]) -> list[dict]:
    combined = _tag_us_holdings(us) + india
    combined.sort(key=lambda h: h.get("value", 0), reverse=True)
    return combined


def _fetch_us_portfolio(*, force_refresh: bool) -> tuple[PortfolioData | None, str | None]:
    if not (is_configured() and has_brokerage_connection()):
        return None, None
    try:
        return get_snaptrade_portfolio(force_refresh=force_refresh), None
    except Exception as exc:
        logger.exception("US portfolio fetch failed")
        return None, str(exc)


def get_merged_portfolio(*, force_refresh: bool = False) -> MergedPortfolioData:
    now = now_app()
    manual_count = count_manual_investments()

    if settings.mock_integrations:
        mock = _mock_portfolio()
        india, fx_rate, fx_at = get_manual_holdings(force_refresh=force_refresh)
        holdings = _merge_holdings(mock.holdings, india)
        total_value = round(sum(h["value"] for h in holdings), 2)
        total_pnl = sum(h.get("pnl", 0) or 0 for h in holdings)
        return MergedPortfolioData(
            total_value=total_value,
            total_invested=_total_invested(holdings),
            total_pnl=round(total_pnl, 2),
            holdings=holdings,
            cached=False,
            updated_at=now,
            source="mock" if not india else "mock+manual",
            fx_rate=fx_rate or None,
            fx_as_of=fx_at,
        )

    if force_refresh:
        us_data, us_error = _fetch_us_portfolio(force_refresh=True)
        india, fx_rate, fx_at = get_manual_holdings(force_refresh=True)
    else:
        with ThreadPoolExecutor(max_workers=2) as executor:
            us_future = executor.submit(_fetch_us_portfolio, force_refresh=False)
            india_future = executor.submit(get_manual_holdings, force_refresh=False)
            us_data, us_error = us_future.result()
            india, fx_rate, fx_at = india_future.result()

    if us_data:
        holdings = _merge_holdings(us_data.holdings, india)
        total_value = round(sum(h["value"] for h in holdings), 2)
        total_pnl = sum(h.get("pnl", 0) or 0 for h in holdings)
        source = us_data.source
        if india:
            source = f"{source}+manual"
        return MergedPortfolioData(
            total_value=total_value,
            total_invested=_total_invested(holdings),
            total_pnl=round(total_pnl, 2),
            holdings=holdings,
            cached=us_data.cached,
            updated_at=us_data.updated_at,
            source=source,
            fx_rate=fx_rate or None,
            fx_as_of=fx_at,
        )

    if india:
        total_value = round(sum(h["value"] for h in india), 2)
        total_pnl = sum(h.get("pnl", 0) or 0 for h in india)
        return MergedPortfolioData(
            total_value=total_value,
            total_invested=_total_invested(india),
            total_pnl=round(total_pnl, 2),
            holdings=india,
            cached=False,
            updated_at=now,
            source="manual",
            fx_rate=fx_rate or None,
            fx_as_of=fx_at,
        )

    if manual_count > 0:
        raise RuntimeError("Unable to value manual investments. Check your entries.")

    if us_error:
        raise RuntimeError(us_error)

    if not is_configured():
        raise RuntimeError("Connect Robinhood or add India investments.")

    raise RuntimeError("Robinhood not connected. Tap Connect Robinhood or add India investments.")
