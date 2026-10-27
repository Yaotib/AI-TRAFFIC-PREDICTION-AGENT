
"""Geocoding using OpenStreetMap's Nominatim service."""

import asyncio
import time

import httpx

from ..config import get_settings
from ..schemas import Place
from .demo import demo_geocode

GEOCODE_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "DepartWiseAPI/0.1 (hackathon prototype)"

# Respect Nominatim's public-service usage limit.
_request_lock = asyncio.Lock()
_last_request_at = 0.0


class GeocodingError(Exception):
    pass


async def geocode(query: str, limit: int = 3) -> list[Place]:
    global _last_request_at

    s = get_settings()

    if s.demo_mode:
        return demo_geocode(query)[:limit]

    params = {
        "q": query,
        "countrycodes": "gh",
        "format": "jsonv2",
        "limit": min(max(limit, 1), 5),
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        async with _request_lock:
            wait = 1.05 - (time.monotonic() - _last_request_at)
            if wait > 0:
                await asyncio.sleep(wait)

            async with httpx.AsyncClient(
                timeout=s.http_timeout_s
            ) as client:
                response = await client.get(
                    GEOCODE_URL,
                    params=params,
                    headers=headers,
                )

            _last_request_at = time.monotonic()
            response.raise_for_status()
            data = response.json()

    except (httpx.HTTPError, ValueError) as exc:
        raise GeocodingError(
            f"OpenStreetMap geocoding failed ({type(exc).__name__})."
        ) from exc

    if not isinstance(data, list):
        raise GeocodingError(
            "OpenStreetMap returned an unexpected response."
        )

    places: list[Place] = []

    for index, item in enumerate(data, start=1):
        try:
            places.append(
                Place(
                    id=f"place_{index}",
                    name=item["display_name"],
                    lat=float(item["lat"]),
                    lng=float(item["lon"]),
                    source="openstreetmap_nominatim",
                )
            )
        except (KeyError, TypeError, ValueError):
            continue

    return places
