import logging
from datetime import date, datetime, timedelta, timezone

import httpx

from config import settings
from db.database import (
    delete_plaid_item,
    list_plaid_items,
    save_plaid_item,
    update_plaid_item_sync,
)

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
        last_synced_at=datetime.now(timezone.utc),
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

    date_raw = txn.get("datetime") or txn.get("date") or ""
    if "T" in date_raw:
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


def _fetch_item_transactions(access_token: str, accounts: list[dict], *, days: int) -> list[dict]:
    end = date.today()
    start = end - timedelta(days=days)
    account_lookup = {a["account_id"]: a for a in accounts if a.get("account_id")}

    transactions: list[dict] = []
    offset = 0
    count = 500
    total = None

    while total is None or offset < total:
        data = _post(
            "/transactions/get",
            {
                "access_token": access_token,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "options": {"count": count, "offset": offset},
            },
        )
        total = data.get("total_transactions", 0)
        for txn in data.get("transactions") or []:
            mapped = _map_plaid_transaction(txn, account_lookup)
            if mapped:
                transactions.append(mapped)
        offset += count
        if not data.get("transactions"):
            break

    return transactions


def fetch_plaid_transactions(*, days: int = 30, force_refresh: bool = False) -> list[dict]:
    del force_refresh  # refresh always fetches live from Plaid

    if settings.mock_integrations:
        return []

    if not has_connection():
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
            txns = _fetch_item_transactions(item.access_token, accounts, days=days)
        except httpx.HTTPError:
            logger.exception("Plaid transactions/get failed for item %s", item.item_id)
            continue

        update_plaid_item_sync(
            item.item_id,
            sync_cursor=item.sync_cursor,
            last_synced_at=datetime.now(timezone.utc),
            accounts_json=accounts,
        )

        for txn in txns:
            if txn["id"] not in seen:
                seen.add(txn["id"])
                merged.append(txn)

    superseded_pending = {
        t["pending_transaction_id"]
        for t in merged
        if t.get("pending_transaction_id")
    }
    if superseded_pending:
        merged = [
            t for t in merged
            if not (t.get("pending") and t["id"].removeprefix("plaid:") in superseded_pending)
        ]

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
