from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from db.models import AppSetting, Base, PlaidItem, PortfolioSnapshot, PushSubscription, SpendingAlertSent, SpendingAmountOverride, SpendingExclusion, SpendingSnapshot

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_schema()


def _migrate_schema() -> None:
    """Add columns to existing SQLite DBs without Alembic."""
    if not settings.database_url.startswith("sqlite"):
        return
    columns = [
        ("plaid_items", "institution_id", "VARCHAR(100)"),
        ("plaid_items", "institution_logo", "TEXT"),
    ]
    with engine.begin() as conn:
        for table, column, col_type in columns:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            except Exception:
                pass


def get_setting(key: str) -> str | None:
    with SessionLocal() as session:
        row = session.get(AppSetting, key)
        return row.value if row else None


def set_setting(key: str, value: str) -> None:
    with SessionLocal() as session:
        row = session.get(AppSetting, key)
        if row:
            row.value = value
        else:
            session.add(AppSetting(key=key, value=value))
        session.commit()


def save_snapshot(total_value: float, total_pnl: float | None, holdings: list) -> None:
    with SessionLocal() as session:
        session.add(
            PortfolioSnapshot(
                total_value=total_value,
                total_pnl=total_pnl,
                holdings_json=holdings,
            )
        )
        session.commit()


def get_latest_snapshot() -> PortfolioSnapshot | None:
    with SessionLocal() as session:
        stmt = select(PortfolioSnapshot).order_by(PortfolioSnapshot.captured_at.desc()).limit(1)
        return session.scalars(stmt).first()


def save_push_subscription(endpoint: str, subscription_json: dict) -> None:
    with SessionLocal() as session:
        row = session.scalar(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
        if row:
            row.subscription_json = subscription_json
        else:
            session.add(PushSubscription(endpoint=endpoint, subscription_json=subscription_json))
        session.commit()


def delete_push_subscription(endpoint: str) -> None:
    with SessionLocal() as session:
        row = session.scalar(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
        if row:
            session.delete(row)
            session.commit()


def list_push_subscriptions() -> list[dict]:
    with SessionLocal() as session:
        rows = session.scalars(select(PushSubscription)).all()
        return [
            {"endpoint": row.endpoint, "subscription_json": row.subscription_json}
            for row in rows
        ]


SPLITWISE_API_KEY_SETTING = "splitwise_api_key"
MONTHLY_BUDGET_SETTING = "monthly_budget"
DEFAULT_MONTHLY_BUDGET = 2200.0


def get_splitwise_api_key() -> str | None:
    stored = get_setting(SPLITWISE_API_KEY_SETTING)
    if stored:
        return stored
    from config import settings

    return settings.splitwise_api_key or None


def set_splitwise_api_key(value: str) -> None:
    set_setting(SPLITWISE_API_KEY_SETTING, value)


def get_monthly_budget() -> float:
    stored = get_setting(MONTHLY_BUDGET_SETTING)
    if stored is None:
        return DEFAULT_MONTHLY_BUDGET
    try:
        return max(0.0, float(stored))
    except ValueError:
        return DEFAULT_MONTHLY_BUDGET


def set_monthly_budget(amount: float) -> None:
    set_setting(MONTHLY_BUDGET_SETTING, str(round(max(0.0, amount), 2)))


def list_plaid_items() -> list[PlaidItem]:
    with SessionLocal() as session:
        return list(session.scalars(select(PlaidItem)).all())


def get_plaid_item_by_item_id(item_id: str) -> PlaidItem | None:
    with SessionLocal() as session:
        return session.scalar(select(PlaidItem).where(PlaidItem.item_id == item_id))


def save_plaid_item(
    *,
    item_id: str,
    access_token: str,
    institution_name: str | None = None,
    institution_id: str | None = None,
    institution_logo: str | None = None,
    accounts_json: list | None = None,
) -> PlaidItem:
    with SessionLocal() as session:
        row = session.scalar(select(PlaidItem).where(PlaidItem.item_id == item_id))
        if row:
            row.access_token = access_token
            if institution_name:
                row.institution_name = institution_name
            if institution_id:
                row.institution_id = institution_id
            if institution_logo:
                row.institution_logo = institution_logo
            if accounts_json is not None:
                row.accounts_json = accounts_json
        else:
            row = PlaidItem(
                item_id=item_id,
                access_token=access_token,
                institution_name=institution_name,
                institution_id=institution_id,
                institution_logo=institution_logo,
                accounts_json=accounts_json or [],
            )
            session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_plaid_institution_logos() -> dict[str, str]:
    logos: dict[str, str] = {}
    for item in list_plaid_items():
        if item.institution_id and item.institution_logo:
            logos[item.institution_id] = f"data:image/png;base64,{item.institution_logo}"
    return logos


def update_plaid_item_sync(
    item_id: str,
    *,
    sync_cursor: str | None,
    last_synced_at,
    accounts_json: list | None = None,
) -> None:
    with SessionLocal() as session:
        row = session.scalar(select(PlaidItem).where(PlaidItem.item_id == item_id))
        if not row:
            return
        row.sync_cursor = sync_cursor
        row.last_synced_at = last_synced_at
        if accounts_json is not None:
            row.accounts_json = accounts_json
        session.commit()


def delete_plaid_item(item_id: str) -> None:
    with SessionLocal() as session:
        row = session.scalar(select(PlaidItem).where(PlaidItem.item_id == item_id))
        if row:
            session.delete(row)
            session.commit()


def save_spending_snapshot(transactions: list, summary: dict) -> None:
    with SessionLocal() as session:
        session.add(
            SpendingSnapshot(
                transactions_json=transactions,
                summary_json=summary,
            )
        )
        session.commit()


def get_latest_spending_snapshot() -> SpendingSnapshot | None:
    with SessionLocal() as session:
        stmt = select(SpendingSnapshot).order_by(SpendingSnapshot.captured_at.desc()).limit(1)
        return session.scalars(stmt).first()


def get_spending_exclusion_ids() -> set[str]:
    with SessionLocal() as session:
        rows = session.scalars(select(SpendingExclusion.txn_id)).all()
        return set(rows)


def exclude_spending_txn(txn_id: str) -> None:
    with SessionLocal() as session:
        if session.get(SpendingExclusion, txn_id):
            return
        session.add(SpendingExclusion(txn_id=txn_id))
        session.commit()


def include_spending_txn(txn_id: str) -> None:
    with SessionLocal() as session:
        row = session.get(SpendingExclusion, txn_id)
        if row:
            session.delete(row)
            session.commit()


def get_spending_amount_overrides() -> dict[str, float]:
    with SessionLocal() as session:
        rows = session.scalars(select(SpendingAmountOverride)).all()
        return {row.txn_id: float(row.amount) for row in rows}


def set_spending_amount_override(txn_id: str, amount: float) -> None:
    amount = round(float(amount), 2)
    with SessionLocal() as session:
        row = session.get(SpendingAmountOverride, txn_id)
        if row:
            row.amount = amount
        else:
            session.add(SpendingAmountOverride(txn_id=txn_id, amount=amount))
        session.commit()


def clear_spending_amount_override(txn_id: str) -> None:
    with SessionLocal() as session:
        row = session.get(SpendingAmountOverride, txn_id)
        if row:
            session.delete(row)
            session.commit()


def get_spending_alert_keys() -> set[str]:
    with SessionLocal() as session:
        rows = session.scalars(select(SpendingAlertSent.alert_key)).all()
        return set(rows)


def mark_spending_alerts_sent(keys: list[str]) -> None:
    if not keys:
        return
    with SessionLocal() as session:
        for key in keys:
            if session.get(SpendingAlertSent, key):
                continue
            session.add(SpendingAlertSent(alert_key=key))
        session.commit()
