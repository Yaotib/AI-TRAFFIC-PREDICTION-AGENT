# backend/app/providers/context.py
import asyncio
from datetime import datetime

import httpx

from ..config import get_settings
from ..timeutil import tz

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
NAGER = "https://date.nager.at/api/v3/PublicHolidays/{year}/GH"
NOTE = "Context only. This is not traffic data."

_HOLIDAYS: dict[int, list[dict]] = {}  # holiday lists rarely change, so cache by year


async def _weather(lat: float, lng: float, when: datetime) -> dict:
    s = get_settings()
    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": "precipitation,precipitation_probability",
        "timezone": s.timezone,
        "forecast_days": 3,
    }
    try:
        async with httpx.AsyncClient(timeout=s.http_timeout_s) as client:
            r = await client.get(OPEN_METEO, params=params)
            r.raise_for_status()
            hourly = r.json()["hourly"]
        key = when.astimezone(tz()).strftime("%Y-%m-%dT%H:00")
        i = hourly["time"].index(key)
        return {
            "available": True,
            "source": "open-meteo",
            "hour_local": key[-5:],
            "precipitation_mm": hourly["precipitation"][i],
            "precipitation_probability_pct": hourly["precipitation_probability"][i],
        }
    except (httpx.HTTPError, KeyError, ValueError, IndexError):
        return {"available": False, "reason": "Weather data could not be retrieved for that time."}


async def _holidays(year: int) -> list[dict]:
    if year not in _HOLIDAYS:
        s = get_settings()
        async with httpx.AsyncClient(timeout=s.http_timeout_s) as client:
            r = await client.get(NAGER.format(year=year))
            r.raise_for_status()
            _HOLIDAYS[year] = r.json()
    return _HOLIDAYS[year]


async def _calendar(when: datetime) -> dict:
    local = when.astimezone(tz())
    try:
        holidays = await _holidays(local.year)
        today = local.strftime("%Y-%m-%d")
        match = next((h for h in holidays if h.get("date") == today), None)
        return {
            "available": True,
            "source": "nager.date",
            "day_of_week": local.strftime("%A"),
            "is_weekend": local.weekday() >= 5,
            "is_public_holiday": match is not None,
            "holiday_name": (match.get("name") or match.get("localName")) if match else None,
        }
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        return {"available": False, "reason": "Holiday calendar could not be retrieved."}


async def get_context(lat: float, lng: float, when: datetime) -> dict:
    weather, calendar = await asyncio.gather(_weather(lat, lng, when), _calendar(when))
    return {"weather": weather, "calendar": calendar, "note": NOTE}