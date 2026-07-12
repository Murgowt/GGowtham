from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    total_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    holdings_json: Mapped[list | None] = mapped_column(JSON, nullable=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    subscription_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class PlaidItem(Base):
    __tablename__ = "plaid_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    access_token: Mapped[str] = mapped_column(String(500), nullable=False)
    institution_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    institution_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    institution_logo: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_cursor: Mapped[str | None] = mapped_column(String(500), nullable=True)
    accounts_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    transactions_cache_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class SpendingSnapshot(Base):
    __tablename__ = "spending_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    transactions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SpendingExclusion(Base):
    """User-hidden transactions excluded from monthly spend totals."""

    __tablename__ = "spending_exclusions"

    txn_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    excluded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class SpendingAmountOverride(Base):
    """User-edited budget amounts for individual transactions."""

    __tablename__ = "spending_amount_overrides"

    txn_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    edited_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class SpendingAlertSent(Base):
    """Tracks purchase/split push alerts already delivered."""

    __tablename__ = "spending_alert_sent"

    alert_key: Mapped[str] = mapped_column(String(220), primary_key=True)
    alerted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Goal(Base):
    """Natural-language financial goal with LLM-extracted structure."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="Goal")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ManualInvestment(Base):
    """User-entered India investment (FD, MF, stock) valued on refresh."""

    __tablename__ = "manual_investments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    invested_inr: Mapped[float] = mapped_column(Float, nullable=False)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class IncomeProfile(Base):
    """Single NL paycheck + allocation plan (PIN-gated in API)."""

    __tablename__ = "income_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
