import logging
import time
from datetime import date, datetime, timedelta, timezone

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
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(
                    f"{SPLITWISE_BASE}{path}",
                    headers=_headers(),
                    params=params or {},
                )
                if response.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning("Splitwise rate limited (429), retry in %ss", wait)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("Splitwise request failed")


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


def _user_balance(expense: dict, user_id: int) -> dict[str, float] | None:
    for user in expense.get("users") or []:
        if user.get("user_id") == user_id:
            return {
                "net": float(user.get("net_balance") or 0),
                "owed": float(user.get("owed_share") or 0),
                "paid": float(user.get("paid_share") or 0),
            }
    return None


def _group_label(expense: dict) -> str:
    group = expense.get("group") or {}
    if group.get("name"):
        return f"Splitwise · {group['name']}"
    return "Splitwise"


def _is_deleted(expense: dict) -> bool:
    return bool(expense.get("deleted_at"))


def _base_txn(
    expense: dict,
    *,
    expense_id: int,
    amount: float,
    dt: datetime,
    description: str,
    txn_type: str,
    medium: dict,
    **extra,
) -> dict:
    category = None
    cat = expense.get("category")
    if isinstance(cat, dict):
        category = cat.get("name")

    return {
        "id": f"splitwise:{txn_type}:{expense_id}",
        "source": "splitwise",
        "date": dt.isoformat(),
        "amount": round(amount, 2),
        "currency": (expense.get("currency_code") or "USD").upper(),
        "description": description,
        "account_name": _group_label(expense),
        "category": category,
        "txn_type": txn_type,
        **medium,
        **extra,
    }


def fetch_expenses(*, days: int = 30) -> list[dict]:
    cutoff = datetime.now(timezone.utc).date().fromordinal(
        datetime.now(timezone.utc).date().toordinal() - days
    )
    return fetch_expenses_between(start=cutoff, end=datetime.now(timezone.utc).date())


def _paginate_expenses(params: dict) -> list[dict]:
    expenses: list[dict] = []
    offset = 0
    limit = 100
    while True:
        try:
            data = _get(
                "/get_expenses",
                params={
                    "limit": limit,
                    "offset": offset,
                    "visible": True,
                    **params,
                },
            )
        except httpx.HTTPError:
            logger.exception("Splitwise API request failed")
            raise RuntimeError("Failed to fetch Splitwise expenses") from None

        page = data.get("expenses") or []
        if not page:
            break
        expenses.extend(page)
        if len(page) < limit:
            break
        offset += limit
    return expenses


def _expenses_to_transactions(expenses: list[dict], *, user_id: int, medium: dict) -> list[dict]:
    transactions: list[dict] = []
    for expense in expenses:
        if _is_deleted(expense):
            continue

        expense_id = expense.get("id")
        description = (expense.get("description") or "Splitwise expense").strip()
        dt = _parse_expense_date(expense.get("date") or expense.get("created_at", ""))

        if expense.get("payment"):
            for rep in expense.get("repayments") or []:
                rep_amt = float(rep.get("amount") or 0)
                if rep_amt <= 0:
                    continue
                rep_key = f"{rep.get('from')}:{rep.get('to')}"
                if rep.get("to") == user_id:
                    label = description or "Settlement received"
                    transactions.append(
                        _base_txn(
                            expense,
                            expense_id=f"{expense_id}:{rep_key}",
                            amount=rep_amt,
                            dt=dt,
                            description=label,
                            txn_type="settlement",
                            medium=medium,
                            settlement_direction="received",
                        )
                    )
                elif rep.get("from") == user_id:
                    label = description or "Settlement paid"
                    transactions.append(
                        _base_txn(
                            expense,
                            expense_id=f"{expense_id}:{rep_key}",
                            amount=-rep_amt,
                            dt=dt,
                            description=label,
                            txn_type="settlement",
                            medium=medium,
                            settlement_direction="sent",
                        )
                    )
            continue

        balance = _user_balance(expense, user_id)
        if balance is None or balance["net"] == 0:
            continue

        transactions.append(
            _base_txn(
                expense,
                expense_id=expense_id,
                amount=round(balance["net"], 2),
                dt=dt,
                description=description,
                txn_type="share",
                medium=medium,
                net_balance=round(balance["net"], 2),
                owed_share=round(balance["owed"], 2),
                paid_share=round(balance["paid"], 2),
            )
        )
    return transactions


def fetch_expenses_between(*, start: date, end: date) -> list[dict]:
    if settings.mock_integrations:
        return []

    if not is_configured():
        return []

    user_id = get_current_user_id()
    dated_after = start.isoformat()
    # Splitwise dated_before is exclusive — add 1 day so expenses dated `end` are included.
    dated_before = (end + timedelta(days=1)).isoformat()
    medium = resolve_medium(source="splitwise")

    # By expense date (billing window).
    by_date = _paginate_expenses({"dated_after": dated_after, "dated_before": dated_before})

    # Also fetch recently *updated* expenses — catches new splits backdated before `start`.
    updated_after = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%dT00:00:00Z")
    by_updated = _paginate_expenses({"updated_after": updated_after, "dated_before": dated_before})

    merged: dict[int, dict] = {}
    for expense in by_date + by_updated:
        expense_id = expense.get("id")
        if expense_id is not None:
            merged[int(expense_id)] = expense

    logger.info(
        "Splitwise: %s by date, %s by updated, %s unique expenses",
        len(by_date),
        len(by_updated),
        len(merged),
    )
    return _expenses_to_transactions(list(merged.values()), user_id=user_id, medium=medium)
