
# backend/app/timeutil.py
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from .config import get_settings

ACCRA_TZ = ZoneInfo("Africa/Accra")


def tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def now_local() -> datetime:
    return datetime.now(tz())


def parse_local(value: str) -> datetime:
    """Parse 'YYYY-MM-DDTHH:MM' as Accra local time."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz())
    return dt.astimezone(tz())


def to_utc_rfc3339(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fmt_time(dt: datetime) -> str:
    return dt.astimezone(tz()).strftime("%H:%M")


def fmt_date(dt: datetime) -> str:
    return dt.astimezone(tz()).strftime("%Y-%m-%d")
