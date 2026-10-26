# backend/app/providers/routing.py
import asyncio
import re
from datetime import datetime

import httpx

from ..config import get_settings
from ..schemas import Place, RouteOption
from ..timeutil import to_utc_rfc3339
from .demo import demo_routes

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
FIELD_MASK = "routes.duration,routes.staticDuration,routes.distanceMeters,routes.description"


class RoutingError(Exception):
    pass


def _secs(value: str | None) -> int | None:
    if not value:
        return None
    m = re.fullmatch(r"(\d+)(?:\.\d+)?s", value)
    return int(m.group(1)) if m else None


def _waypoint(p: Place) -> dict:
    return {"location": {"latLng": {"latitude": p.lat, "longitude": p.lng}}}


async def compute_routes(
    client: httpx.AsyncClient, origin: Place, dest: Place, departure: datetime
) -> list[RouteOption]:
    s = get_settings()
    body = {
        "origin": _waypoint(origin),
        "destination": _waypoint(dest),
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "departureTime": to_utc_rfc3339(departure),
        "computeAlternativeRoutes": True,
        "units": "METRIC",
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": s.google_maps_api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    try:
        r = await client.post(ROUTES_URL, json=body, headers=headers)
    except httpx.TimeoutException as e:
        raise RoutingError("The routing provider timed out.") from e
    except httpx.HTTPError as e:
        raise RoutingError("The routing provider could not be reached.") from e
    if r.status_code == 429:
        raise RoutingError("The routing provider rate limit was reached. Try again shortly.")
    if r.status_code in (401, 403):
        raise RoutingError("The routing provider rejected the API key, or the Routes API is not enabled.")
    if r.status_code >= 400:
        raise RoutingError(f"The routing provider returned an error ({r.status_code}).")
    try:
        routes = r.json().get("routes", [])
    except ValueError as e:
        raise RoutingError("The routing provider returned an unreadable response.") from e
    options: list[RouteOption] = []
    for item in routes:
        duration = _secs(item.get("duration"))
        if duration is None or "distanceMeters" not in item:
            continue  # skip malformed entries rather than guessing
        options.append(
            RouteOption(
                duration_s=duration,
                static_duration_s=_secs(item.get("staticDuration")),
                distance_m=item["distanceMeters"],
                description=item.get("description"),
            )
        )
    return options


async def sweep(
    origin: Place, dest: Place, departures: list[datetime]
) -> dict[datetime, list[RouteOption]]:
    """Fetch routes for every departure time. Returns only the slots that succeeded."""
    s = get_settings()
    if len(departures) > s.max_route_calls:
        raise RoutingError("Too many time slots requested.")
    if s.demo_mode:
        return {d: demo_routes(origin, dest, d) for d in departures}
    if not s.google_maps_api_key:
        raise RoutingError("GOOGLE_MAPS_API_KEY is not set.")
    sem = asyncio.Semaphore(4)
    async with httpx.AsyncClient(timeout=s.http_timeout_s) as client:

        async def one(d: datetime) -> list[RouteOption]:
            async with sem:
                return await compute_routes(client, origin, dest, d)

        outcomes = await asyncio.gather(*(one(d) for d in departures), return_exceptions=True)
    ok: dict[datetime, list[RouteOption]] = {}
    errors: list[Exception] = []
    for d, out in zip(departures, outcomes):
        if isinstance(out, Exception):
            errors.append(out)
        else:
            ok[d] = out
    if not ok and errors:
        raise errors[0]
    return ok