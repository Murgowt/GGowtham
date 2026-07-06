"""Application timezone helpers (Central Time by default)."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from config import settings


def app_tz() -> ZoneInfo:
    return ZoneInfo(settings.app_timezone)


def now_app() -> datetime:
    return datetime.now(app_tz())


def to_app_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(app_tz())


def app_midnight(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=app_tz())
