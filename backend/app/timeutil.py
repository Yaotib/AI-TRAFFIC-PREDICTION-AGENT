"""Time utilities.

Rule from the guide: all times are Accra local time, converted to UTC only
when talking to Google.
"""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

ACCRA_TZ = ZoneInfo("Africa/Accra")


def now_accra() -> datetime:
    """Current time as a timezone-aware Accra datetime."""
    return datetime.now(ACCRA_TZ)


def as_accra(dt: datetime) -> datetime:
    """Return dt as an Accra-local aware datetime.

    A naive datetime is read as Accra local time. An aware one is converted.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ACCRA_TZ)
    return dt.astimezone(ACCRA_TZ)


def to_utc(dt: datetime) -> datetime:
    """Convert to UTC. Use ONLY at the Google boundary."""
    return as_accra(dt).astimezone(UTC)


def to_google_timestamp(dt: datetime) -> str:
    """RFC 3339 UTC timestamp, e.g. 2026-10-26T07:30:00Z."""
    return to_utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


def from_utc(dt: datetime) -> datetime:
    """Convert a UTC datetime (e.g. from Google) back to Accra local time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(ACCRA_TZ)


def floor_to_minute(dt: datetime) -> datetime:
    return as_accra(dt).replace(second=0, microsecond=0)


def minutes_between(start: datetime, end: datetime) -> int:
    """Whole minutes from start to end."""
    return int((as_accra(end) - as_accra(start)).total_seconds() // 60)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    return as_accra(dt) + timedelta(minutes=minutes)


def format_clock(dt: datetime) -> str:
    """Human display such as '07:45' in Accra time."""
    return as_accra(dt).strftime("%H:%M")


def now_local() -> datetime:
    """Current time in Accra, as a timezone-aware datetime."""
    return now_accra()


def parse_local(text: str) -> datetime:
    """Parse a local time like '2026-10-26T08:30' as Accra time.

    Raises ValueError if the text isn't a valid ISO date and time.
    """
    return as_accra(datetime.fromisoformat(text.strip()))
