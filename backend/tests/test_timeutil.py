from datetime import datetime
from zoneinfo import ZoneInfo

from app import timeutil as t


def test_naive_is_read_as_accra_local():
    assert t.as_accra(datetime(2026, 10, 26, 7, 30)).tzinfo == t.ACCRA_TZ


def test_to_google_timestamp_is_utc_z():
    assert (
        t.to_google_timestamp(datetime(2026, 10, 26, 7, 30)) == "2026-10-26T07:30:00Z"
    )


def test_other_timezone_is_converted():
    # 08:30 in Lagos (UTC+1) is 07:30 in Accra
    lagos = datetime(2026, 10, 26, 8, 30, tzinfo=ZoneInfo("Africa/Lagos"))
    assert t.as_accra(lagos).hour == 7


def test_round_trip_utc():
    dt = t.as_accra(datetime(2026, 10, 26, 7, 30))
    assert t.from_utc(t.to_utc(dt)) == dt


def test_minutes_and_clock():
    a = datetime(2026, 10, 26, 7, 30)
    assert t.minutes_between(a, t.add_minutes(a, 42)) == 42
    assert t.format_clock(a) == "07:30"
