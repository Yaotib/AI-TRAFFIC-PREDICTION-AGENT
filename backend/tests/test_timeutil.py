from datetime import datetime

from app import timeutil as t


def test_parse_naive_datetime_as_accra_local():
    dt = t.parse_local("2026-10-26T07:30")

    assert dt.tzinfo == t.tz()
    assert dt.hour == 7
    assert dt.minute == 30


def test_parse_datetime_with_timezone_converts_to_accra():
    dt = t.parse_local("2026-10-26T08:30+01:00")

    # 08:30 in UTC+1 is 07:30 in Accra (UTC+0).
    assert dt.hour == 7
    assert dt.minute == 30
    assert dt.tzinfo == t.tz()


def test_to_utc_rfc3339_formats_utc_timestamp():
    dt = datetime(2026, 10, 26, 7, 30, tzinfo=t.tz())

    assert t.to_utc_rfc3339(dt) == "2026-10-26T07:30:00Z"


def test_fmt_time():
    dt = datetime(2026, 10, 26, 7, 30, tzinfo=t.tz())

    assert t.fmt_time(dt) == "07:30"


def test_fmt_date():
    dt = datetime(2026, 10, 26, 7, 30, tzinfo=t.tz())

    assert t.fmt_date(dt) == "2026-10-26"


def test_accra_timezone_is_utc():
    assert datetime(2026, 10, 26, 7, 30, tzinfo=t.ACCRA_TZ).utcoffset().total_seconds() == 0