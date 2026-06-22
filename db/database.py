from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from db.models import AppSetting, Base, PortfolioSnapshot, PushSubscription

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


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
