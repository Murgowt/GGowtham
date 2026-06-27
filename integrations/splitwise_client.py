import logging
from datetime import datetime, timezone

import httpx

from config import settings
from db.database import get_splitwise_api_key
from integrations.medium import resolve_medium

logger = logging.getLogger(__name__)

SPLITWISE_BASE = "https://secure.splitwise.com/api/v3.0"
SPLITWISE_USER_ID_KEY = "splitwise_user_id"


def is_configured() -> bool:
    return bool(get_splitwise_api_key())


def _headers() -> dict[str, str]:
    api_key = get_splitwise_api_key()
    if not api_key:
        raise RuntimeError("Splitwise API key not configured")
    return {"Authorization": f"Bearer {api_key}"}


def _get(path: str, params: dict | None = None) -> dict:
    with httpx.Client(timeout=20.0) as client:
        response = client.get(
            f"{SPLITWISE_BASE}{path}",
            headers=_headers(),
            params=params or {},
        )
        response.raise_for_status()
        return response.json()


def get_current_user_id() -> int:
    from db.database import get_setting, set_setting

    stored = get_setting(SPLITWISE_USER_ID_KEY)
    if stored:
        return int(stored)

    data = _get("/get_current_user")
    user = data.get("user") or {}
    user_id = user.get("id")
    if not user_id:
        raise RuntimeError("Could not load Splitwise user")
    set_setting(SPLITWISE_USER_ID_KEY, str(user_id))
    return int(user_id)


def _parse_expense_date(raw: str) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    if raw.endswith("Z"):
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.fromisoformat(f"{raw}T00:00:00+00:00")


def _user_share(expense: dict, user_id: int) -> float | None:
    for user in expense.get("users") or []:
        if user.get("user_id") == user_id:
            owed = float(user.get("owed_share") or 0)
            return owed
    return None


def _group_label(expense: dict) -> str:
    group = expense.get("group") or {}
    if group.get("name"):
        return f"Splitwise · {group['name']}"
    return "Splitwise"


def _is_deleted(expense: dict) -> bool:
    return bool(expense.get("deleted_at"))


def fetch_expenses(*, days: int = 30) -> list[dict]:
    if settings.mock_integrations:
        return []

    if not is_configured():
        return []

    user_id = get_current_user_id()
    cutoff = datetime.now(timezone.utc).date().fromordinal(
        datetime.now(timezone.utc).date().toordinal() - days
    )
    dated_after = cutoff.isoformat()

    transactions: list[dict] = []
    offset = 0
    limit = 100

    while True:
        try:
            data = _get(
                "/get_expenses",
                params={
                    "limit": limit,
                    "offset": offset,
                    "dated_after": dated_after,
                    "visible": True,
                },
            )
        except httpx.HTTPError:
            logger.exception("Splitwise API request failed")
            raise RuntimeError("Failed to fetch Splitwise expenses") from None

        expenses = data.get("expenses") or []
        if not expenses:
            break

        for expense in expenses:
            if _is_deleted(expense):
                continue

            share = _user_share(expense, user_id)
            if share is None or share == 0:
                continue

            expense_id = expense.get("id")
            description = (expense.get("description") or "Splitwise expense").strip()
            category = None
            cat = expense.get("category")
            if isinstance(cat, dict):
                category = cat.get("name")

            currency = (expense.get("currency_code") or "USD").upper()
            dt = _parse_expense_date(expense.get("date") or expense.get("created_at", ""))
            group_label = _group_label(expense)
            medium = resolve_medium(source="splitwise")

            transactions.append(
                {
                    "id": f"splitwise:{expense_id}",
                    "source": "splitwise",
                    "date": dt.isoformat(),
                    "amount": round(-share, 2),
                    "currency": currency,
                    "description": description,
                    "account_name": group_label,
                    "category": category,
                    **medium,
                }
            )

        if len(expenses) < limit:
            break
        offset += limit

    return transactions
