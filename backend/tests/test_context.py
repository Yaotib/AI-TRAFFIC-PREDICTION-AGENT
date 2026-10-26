# backend/tests/test_context.py
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import respx

from app.providers import context
from app.providers.context import NAGER, OPEN_METEO, get_context

TZ = ZoneInfo("Africa/Accra")
WHEN = datetime(2026, 10, 26, 8, 5, tzinfo=TZ)  # a Monday
WEATHER = {
    "hourly": {
        "time": ["2026-10-26T08:00"],
        "precipitation": [0.2],
        "precipitation_probability": [40],
    }
}
HOLIDAYS = [{"date": "2026-12-25", "localName": "Christmas Day", "name": "Christmas Day"}]


@respx.mock
async def test_context_combines_weather_and_calendar(monkeypatch):
    monkeypatch.setattr(context, "_HOLIDAYS", {})
    respx.get(OPEN_METEO).mock(return_value=httpx.Response(200, json=WEATHER))
    respx.get(NAGER.format(year=2026)).mock(return_value=httpx.Response(200, json=HOLIDAYS))
    out = await get_context(5.6, -0.2, WHEN)
    assert out["weather"]["precipitation_probability_pct"] == 40
    assert out["calendar"]["day_of_week"] == "Monday"
    assert out["calendar"]["is_public_holiday"] is False


@respx.mock
async def test_weather_failure_does_not_break_calendar(monkeypatch):
    monkeypatch.setattr(context, "_HOLIDAYS", {})
    respx.get(OPEN_METEO).mock(return_value=httpx.Response(500))
    respx.get(NAGER.format(year=2026)).mock(
        return_value=httpx.Response(200, json=[{"date": "2026-10-26", "name": "Test Holiday"}])
    )
    out = await get_context(5.6, -0.2, WHEN)
    assert out["weather"]["available"] is False
    assert out["calendar"]["is_public_holiday"] is True
    assert out["calendar"]["holiday_name"] == "Test Holiday"


@respx.mock
async def test_calendar_failure_does_not_break_weather(monkeypatch):
    monkeypatch.setattr(context, "_HOLIDAYS", {})
    respx.get(OPEN_METEO).mock(return_value=httpx.Response(200, json=WEATHER))
    respx.get(NAGER.format(year=2026)).mock(return_value=httpx.Response(503))
    out = await get_context(5.6, -0.2, WHEN)
    assert out["weather"]["available"] is True
    assert out["calendar"]["available"] is False