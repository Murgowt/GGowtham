import logging
import time
from datetime import date, datetime, timedelta

import httpx

from config import settings
from db.database import (
    delete_plaid_item,
    list_plaid_items,
    save_plaid_item,
    update_plaid_item_sync,
)
from integrations.app_time import now_app, to_app_tz
from integrations.medium import resolve_medium

logger = logging.getLogger(__name__)

PLAID_HOSTS = {
    "sandbox": "https://sandbox.plaid.com",
    "production": "https://production.plaid.com",
    "development": "https://development.plaid.com",
}


def is_configured() -> bool:
    return bool(settings.plaid_client_id and settings.plaid_secret)


def has_connection() -> bool:
    if settings.mock_integrations:
        return True
    return len(list_plaid_items()) > 0


def _host() -> str:
    env = (settings.plaid_env or "sandbox").lower()
    host = PLAID_HOSTS.get(env)
    if not host:
        raise RuntimeError(f"Invalid PLAID_ENV: {settings.plaid_env}")
    return host


def _post(path: str, body: dict) -> dict:
    payload = {
        "client_id": settings.plaid_client_id,
        "secret": settings.plaid_secret,
        **body,
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{_host()}{path}", json=payload)
        if not response.is_success:
            logger.error("Plaid %s failed: %s", path, response.text)
            response.raise_for_status()
        return response.json()


def create_link_token(*, user_id: str = "brain-user") -> str:
    if not is_configured():
        raise RuntimeError("Plaid credentials not configured")

    data = _post(
        "/link/token/create",
        {
            "user": {"client_user_id": user_id},
            "client_name": "Brain",
            "products": ["transactions"],
            "country_codes": ["US"],
            "language": "en",
        },
    )
    token = data.get("link_token")
    if not token:
        raise RuntimeError("Plaid did not return a link token")
    return token


def exchange_public_token(public_token: str) -> dict:
    data = _post("/item/public_token/exchange", {"public_token": public_token})
    access_token = data.get("access_token")
    item_id = data.get("item_id")
    if not access_token or not item_id:
        raise RuntimeError("Plaid token exchange failed")
    return {"access_token": access_token, "item_id": item_id}


def _accounts_for_item(access_token: str) -> tuple[list[dict], str | None, str | None]:
    data = _post("/accounts/get", {"access_token": access_token})
    accounts = data.get("accounts") or []
    item_meta = data.get("item") or {}
    institution_name = item_meta.get("institution_name")
    institution_id = item_meta.get("institution_id")
    normalized = []
    for account in accounts:
        account_type = account.get("type", "")
        subtype = account.get("subtype", "")
        if account_type == "depository":
            source = "bank"
        elif account_type == "credit":
            source = "card"
        else:
            continue
        normalized.append(
            {
                "account_id": account.get("account_id"),
                "name": account.get("name") or account.get("official_name") or "Account",
                "type": account_type,
                "subtype": subtype,
                "source": source,
                "mask": account.get("mask"),
                "institution_name": institution_name,
                "institution_id": institution_id,
            }
        )
    return normalized, institution_name, institution_id


def fetch_institution_logo(institution_id: str) -> str | None:
    if not institution_id:
        return None
    try:
        data = _post(
            "/institutions/get_by_id",
            {
                "institution_id": institution_id,
                "country_codes": ["US"],
                "options": {"include_optional_metadata": True},
            },
        )
    except httpx.HTTPError:
        logger.exception("Plaid institutions/get_by_id failed for %s", institution_id)
        return None
    institution = data.get("institution") or {}
    logo = institution.get("logo")
    return logo if logo else None


def _ensure_item_metadata(
    *,
    item_id: str,
    access_token: str,
    institution_name: str | None,
    institution_id: str | None,
    existing_logo: str | None = None,
) -> tuple[list[dict], str | None, str | None, str | None]:
    accounts, inst_name, inst_id = _accounts_for_item(access_token)
    institution_name = inst_name or institution_name
    institution_id = inst_id or institution_id
    logo = existing_logo
    if institution_id and not logo:
        logo = fetch_institution_logo(institution_id)
    for account in accounts:
        account["institution_name"] = institution_name
        account["institution_id"] = institution_id
    save_plaid_item(
        item_id=item_id,
        access_token=access_token,
        institution_name=institution_name,
        institution_id=institution_id,
        institution_logo=logo,
        accounts_json=accounts,
    )
    return accounts, institution_name, institution_id, logo


def connect_item(public_token: str) -> dict:
    exchanged = exchange_public_token(public_token)
    access_token = exchanged["access_token"]
    item_id = exchanged["item_id"]
    accounts, institution_name, institution_id, logo = _ensure_item_metadata(
        item_id=item_id,
        access_token=access_token,
        institution_name=None,
        institution_id=None,
    )
    update_plaid_item_sync(
        item_id,
        sync_cursor=None,
        last_synced_at=now_app(),
        accounts_json=accounts,
    )
    return {
        "item_id": item_id,
        "institution_name": institution_name,
        "institution_id": institution_id,
        "accounts": accounts,
        "has_logo": bool(logo),
    }


def disconnect_item(item_id: str) -> None:
    item = next((i for i in list_plaid_items() if i.item_id == item_id), None)
    if not item:
        return
    try:
        _post("/item/remove", {"access_token": item.access_token})
    except httpx.HTTPError:
        logger.exception("Plaid item remove failed for %s", item_id)
    delete_plaid_item(item_id)


def _plaid_category(txn: dict) -> str | None:
    personal = txn.get("personal_finance_category") or {}
    if personal.get("primary"):
        return str(personal["primary"]).replace("_", " ").title()
    category = txn.get("category")
    if isinstance(category, list) and category:
        return category[-1]
    return None


def _counterparty_names(txn: dict) -> list[str]:
    names: list[str] = []
    for party in txn.get("counterparties") or []:
        if isinstance(party, dict) and party.get("name"):
            names.append(str(party["name"]))
    return names


def _map_plaid_transaction(txn: dict, account_lookup: dict[str, dict]) -> dict | None:
    account_id = txn.get("account_id")
    account = account_lookup.get(account_id)
    if not account:
        return None

    raw_amount = float(txn.get("amount") or 0)
    amount = round(-raw_amount, 2)

    date_raw = (
        txn.get("authorized_datetime")
        or txn.get("authorized_date")
        or txn.get("datetime")
        or txn.get("date")
        or ""
    )
    if not date_raw and txn.get("pending"):
        dt = now_app()
    elif "T" in date_raw:
        dt = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
    else:
        dt = datetime.fromisoformat(f"{date_raw}T12:00:00+00:00")

    name = txn.get("merchant_name") or txn.get("name") or "Transaction"
    txn_id = txn.get("transaction_id") or txn.get("pending_transaction_id")
    if not txn_id:
        return None

    personal = txn.get("personal_finance_category") or {}
    counterparties = _counterparty_names(txn)

    medium = resolve_medium(
        source=account["source"],
        institution_name=account.get("institution_name"),
        account_name=account.get("name"),
        subtype=account.get("subtype"),
    )
    mask = account.get("mask")
    account_label = account.get("name") or "Account"
    if mask:
        account_label = f"{account_label} ···{mask}"

    return {
        "id": f"plaid:{txn_id}",
        "source": account["source"],
        "date": dt.isoformat(),
        "amount": amount,
        "currency": (txn.get("iso_currency_code") or "USD").upper(),
        "description": name,
        "pending": bool(txn.get("pending")),
        "pending_transaction_id": txn.get("pending_transaction_id"),
        "original_description": txn.get("name"),
        "merchant_name": txn.get("merchant_name"),
        "counterparties": counterparties,
        "plaid_category_primary": personal.get("primary"),
        "plaid_category_detailed": personal.get("detailed"),
        "account_name": account_label,
        "institution_name": account.get("institution_name"),
        "institution_id": account.get("institution_id"),
        "category": _plaid_category(txn),
        **medium,
    }


PLAID_REFRESH_MIN_INTERVAL = timedelta(minutes=15)
PLAID_CARD_REFRESH_MIN_INTERVAL = timedelta(minutes=2)
PLAID_CARD_REFRESH_POLL_PASSES = 4
PLAID_CARD_REFRESH_POLL_DELAY_SEC = 2


def _item_is_card_only(accounts: list[dict]) -> bool:
    active = [a for a in accounts if a.get("account_id")]
    return bool(active) and all(a.get("source") == "card" for a in active)


def _refresh_min_interval(accounts: list[dict]) -> timedelta:
    if _item_is_card_only(accounts):
        return PLAID_CARD_REFRESH_MIN_INTERVAL
    return PLAID_REFRESH_MIN_INTERVAL


def _txn_date(mapped: dict) -> date:
    raw = mapped.get("date") or ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return date.today()


def _drop_superseded_pending(transactions: list[dict]) -> list[dict]:
    """Remove pending rows when the posted version exists."""
    superseded = {
        t["pending_transaction_id"]
        for t in transactions
        if t.get("pending_transaction_id") and not t.get("pending")
    }
    if not superseded:
        return transactions
    return [
        t for t in transactions
        if not (t.get("pending") and t["id"].removeprefix("plaid:") in superseded)
    ]


def _request_item_refresh(
    access_token: str,
    item_id: str,
    *,
    accounts: list[dict],
) -> bool:
    """Ask Plaid to pull latest transactions from the bank (rate-limited)."""
    from db.database import get_setting, set_setting

    key = f"plaid_refresh_{item_id}"
    now = now_app()
    min_interval = _refresh_min_interval(accounts)
    last_raw = get_setting(key)
    if last_raw:
        try:
            last = to_app_tz(datetime.fromisoformat(last_raw))
            if now - last < min_interval:
                logger.info("Skipping Plaid refresh for %s (recent)", item_id)
                return False
        except ValueError:
            pass

    try:
        _post("/transactions/refresh", {"access_token": access_token})
        set_setting(key, now.isoformat())
        logger.info("Requested Plaid transaction refresh for %s", item_id)
        return True
    except httpx.HTTPError:
        logger.warning("Plaid transactions/refresh failed for %s", item_id, exc_info=True)
        return False


def _sync_item_transactions(
    access_token: str,
    accounts: list[dict],
    cursor: str | None,
    cache: dict[str, dict],
    *,
    start: date,
    end: date,
    force_refresh: bool = False,
    item_id: str | None = None,
) -> tuple[list[dict], str | None, dict[str, dict]]:
    """Use /transactions/sync — merge into cache so incremental updates keep history."""
    account_lookup = {a["account_id"]: a for a in accounts if a.get("account_id")}
    store = dict(cache)
    current_cursor = cursor

    refreshed = False
    if force_refresh and item_id:
        refreshed = _request_item_refresh(
            access_token, item_id, accounts=accounts,
        )

    poll_passes = (
        PLAID_CARD_REFRESH_POLL_PASSES
        if refreshed and _item_is_card_only(accounts)
        else 1
    )

    for pass_idx in range(poll_passes):
        if pass_idx > 0:
            time.sleep(PLAID_CARD_REFRESH_POLL_DELAY_SEC)

        while True:
            body: dict = {"access_token": access_token}
            if current_cursor:
                body["cursor"] = current_cursor
            data = _post("/transactions/sync", body)

            for txn in (data.get("added") or []) + (data.get("modified") or []):
                mapped = _map_plaid_transaction(txn, account_lookup)
                if mapped:
                    store[mapped["id"]] = mapped

            for removed in data.get("removed") or []:
                txn_id = removed.get("transaction_id")
                if txn_id:
                    store.pop(f"plaid:{txn_id}", None)

            current_cursor = data.get("next_cursor")
            if not data.get("has_more"):
                break

    prune_before = start - timedelta(days=7)
    store = {
        txn_id: txn
        for txn_id, txn in store.items()
        if _txn_date(txn) >= prune_before
    }
    in_window = [
        txn for txn in store.values()
        if start <= _txn_date(txn) <= end
    ]
    return _drop_superseded_pending(in_window), current_cursor, store


def fetch_plaid_transactions(*, days: int = 30, force_refresh: bool = False) -> list[dict]:
    if settings.mock_integrations:
        return []

    if not has_connection():
        return []

    start = date.today() - timedelta(days=days)
    end = date.today() + timedelta(days=1)
    merged: list[dict] = []
    seen: set[str] = set()

    for item in list_plaid_items():
        try:
            accounts, institution_name, institution_id, _logo = _ensure_item_metadata(
                item_id=item.item_id,
                access_token=item.access_token,
                institution_name=item.institution_name,
                institution_id=item.institution_id,
                existing_logo=item.institution_logo,
            )
        except httpx.HTTPError:
            logger.exception("Plaid accounts/get failed for item %s", item.item_id)
            accounts = item.accounts_json or []
            institution_name = item.institution_name
            institution_id = item.institution_id
            for account in accounts:
                account.setdefault("institution_name", institution_name)
                account.setdefault("institution_id", institution_id)

        try:
            cache = dict(item.transactions_cache_json or {})
            txns, new_cursor, new_cache = _sync_item_transactions(
                item.access_token,
                accounts,
                item.sync_cursor,
                cache,
                start=start,
                end=end,
                force_refresh=force_refresh,
                item_id=item.item_id,
            )
        except httpx.HTTPError:
            logger.exception("Plaid transactions/sync failed for item %s", item.item_id)
            continue

        update_plaid_item_sync(
            item.item_id,
            sync_cursor=new_cursor,
            last_synced_at=now_app(),
            accounts_json=accounts,
            transactions_cache_json=new_cache,
        )

        for txn in txns:
            if txn["id"] not in seen:
                seen.add(txn["id"])
                merged.append(txn)

    return merged


def fetch_plaid_transactions_between(
    *,
    start: date,
    end: date,
    force_refresh: bool = False,
) -> list[dict]:
    if settings.mock_integrations or not has_connection():
        return []

    merged: list[dict] = []
    seen: set[str] = set()

    for item in list_plaid_items():
        try:
            accounts, institution_name, institution_id, _logo = _ensure_item_metadata(
                item_id=item.item_id,
                access_token=item.access_token,
                institution_name=item.institution_name,
                institution_id=item.institution_id,
                existing_logo=item.institution_logo,
            )
        except httpx.HTTPError:
            logger.exception("Plaid accounts/get failed for item %s", item.item_id)
            accounts = item.accounts_json or []
            institution_name = item.institution_name
            institution_id = item.institution_id
            for account in accounts:
                account.setdefault("institution_name", institution_name)
                account.setdefault("institution_id", institution_id)

        try:
            cache = dict(item.transactions_cache_json or {})
            txns, new_cursor, new_cache = _sync_item_transactions(
                item.access_token,
                accounts,
                item.sync_cursor,
                cache,
                start=start,
                end=end,
                force_refresh=force_refresh,
                item_id=item.item_id,
            )
        except httpx.HTTPError:
            logger.exception("Plaid transactions/sync failed for item %s", item.item_id)
            continue

        update_plaid_item_sync(
            item.item_id,
            sync_cursor=new_cursor,
            last_synced_at=now_app(),
            accounts_json=accounts,
            transactions_cache_json=new_cache,
        )

        for txn in txns:
            if txn["id"] not in seen:
                seen.add(txn["id"])
                merged.append(txn)

    return merged


def list_connected_accounts() -> list[dict]:
    accounts: list[dict] = []
    for item in list_plaid_items():
        for account in item.accounts_json or []:
            accounts.append(
                {
                    **account,
                    "institution_name": item.institution_name,
                    "item_id": item.item_id,
                }
            )
    return accounts
