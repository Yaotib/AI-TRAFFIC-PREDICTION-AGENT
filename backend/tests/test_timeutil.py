from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

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


def test_now_local_is_aware_accra_time():
    n = t.now_local()
    assert n.tzinfo is not None
    assert n.utcoffset().total_seconds() == 0


def test_parse_local_reads_the_format_the_agent_uses():
    dt = t.parse_local("2026-10-26T08:30")
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 10, 26, 8, 30)
    assert dt.tzinfo == t.ACCRA_TZ


def test_parse_local_strips_spaces():
    assert t.parse_local("  2026-10-26T08:30 ").hour == 8


@pytest.mark.parametrize(
    "bad", ["", "tomorrow at 8", "26/10/2026 08:30", "2026-13-40T99:99"]
)
def test_parse_local_raises_value_error_on_bad_text(bad):
    # tools.py catches ValueError and tells the model the format.
    with pytest.raises(ValueError):
        t.parse_local(bad)
