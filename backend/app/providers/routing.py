"""Routes for one or many departure times, using Google (or demo mode).

Rules from the guide:
- Ask for traffic-aware routes for a specific departure time, with alternatives.
- Durations arrive as text such as "1500s". Read them carefully, and skip
  malformed route entries instead of guessing.
- The departure-time sweep fetches at most four times at once, with a hard cap
  on total calls per request. If some slots fail it keeps the rest, and it
  raises only if every slot failed.
"""

import asyncio
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from ..config import get_settings
from ..schemas import Place, RouteOption
from ..timeutil import to_google_timestamp
from . import demo
from .errors import (
    ProviderError,
    describe_status,
    network_message,
    not_configured_message,
    timeout_message,
    unreadable_message,
)

SERVICE = "Google routing"
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
FIELD_MASK = (
    "routes.duration,routes.staticDuration,routes.distanceMeters,routes.description"
)

_DURATION = re.compile(r"^(\d+(?:\.\d+)?)s$")


class RoutingError(ProviderError):
    """A route lookup failed. The message is safe to show to users."""


def _error(code_msg: tuple[str, str, bool]) -> RoutingError:
    code, message, retryable = code_msg
    return RoutingError(message, code=code, retryable=retryable)


# ------------------------------------------------------------------ parsing


def parse_duration(value: object) -> int:
    """Read a Google duration such as "1500s" into whole seconds.

    Raises ValueError for anything else: missing, not text, wrong unit,
    negative, or zero.
    """
    match = _DURATION.match(value.strip()) if isinstance(value, str) else None
    if not match:
        raise ValueError(f"unreadable duration {value!r}")
    seconds = round(float(match.group(1)))
    if seconds <= 0:
        raise ValueError("duration must be positive")
    return seconds


def _parse_route(entry: object) -> RouteOption | None:
    """One route entry -> RouteOption, or None if it is malformed."""
    if not isinstance(entry, dict):
        return None
    try:
        duration = parse_duration(entry.get("duration"))
    except ValueError:
        return None  # skip it, never guess

    static = None
    if entry.get("staticDuration") is not None:
        try:
            static = parse_duration(entry["staticDuration"])
        except ValueError:
            static = None  # the route is still usable without it

    distance = entry.get("distanceMeters")
    if not isinstance(distance, int) or isinstance(distance, bool) or distance < 0:
        distance = None

    description = entry.get("description")
    return RouteOption(
        summary=description if isinstance(description, str) else None,
        distance_meters=distance,
        duration_seconds=duration,
        static_duration_seconds=static,
    )


def parse_routes(payload: object) -> list[RouteOption]:
    """Read Google's answer. Malformed entries are skipped. May return []."""
    if not isinstance(payload, dict):
        raise RoutingError(
            unreadable_message(SERVICE), code="bad_response", retryable=True
        )
    routes = payload.get("routes")
    if routes is None:
        return []  # Google omits "routes" when there is no route
    if not isinstance(routes, list):
        raise RoutingError(
            unreadable_message(SERVICE), code="bad_response", retryable=True
        )
    return [r for r in (_parse_route(e) for e in routes) if r is not None]


# ------------------------------------------------------------------ one request


def _waypoint(place: Place) -> dict:
    return {"location": {"latLng": {"latitude": place.lat, "longitude": place.lng}}}


async def fetch_routes(
    origin: Place,
    destination: Place,
    departure: datetime,
    *,
    client: httpx.AsyncClient | None = None,
) -> list[RouteOption]:
    """Routes for one departure time. Raises RoutingError if none are usable."""
    settings = get_settings()
    if settings.demo_mode:
        return demo.demo_routes(origin, destination, departure)

    if settings.google_maps_api_key is None:
        raise RoutingError(not_configured_message(SERVICE), code="not_configured")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_maps_api_key.get_secret_value(),
        "X-Goog-FieldMask": FIELD_MASK,
    }
    body = {
        "origin": _waypoint(origin),
        "destination": _waypoint(destination),
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        # Accra time is converted to UTC here, and only here.
        "departureTime": to_google_timestamp(departure),
        "computeAlternativeRoutes": True,
    }

    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=settings.request_timeout_seconds)
    try:
        response = await http.post(ROUTES_URL, json=body, headers=headers)
    except httpx.TimeoutException:
        raise RoutingError(
            timeout_message(SERVICE), code="timeout", retryable=True
        ) from None
    except httpx.HTTPError:
        raise RoutingError(
            network_message(SERVICE), code="network", retryable=True
        ) from None
    finally:
        if owns_client:
            await http.aclose()

    if response.status_code != 200:
        raise _error(describe_status(response.status_code, SERVICE))

    try:
        payload = response.json()
    except ValueError:
        raise RoutingError(
            unreadable_message(SERVICE), code="bad_response", retryable=True
        ) from None

    options = parse_routes(payload)
    if not options:
        raise RoutingError(
            "No drivable route was found between those places for that time.",
            code="no_route",
        )
    return options


# ------------------------------------------------------------------ the sweep


@dataclass
class SweepResult:
    """Routes for the departure times that worked, and the ones that did not."""

    routes: dict[datetime, list[RouteOption]] = field(default_factory=dict)
    failed: list[datetime] = field(default_factory=list)
    errors: list[RoutingError] = field(default_factory=list)

    @property
    def failed_count(self) -> int:
        return len(self.failed)


async def sweep_departures(
    origin: Place,
    destination: Place,
    departures: Sequence[datetime],
) -> SweepResult:
    """Fetch routes for several departure times at once.

    - At most `sweep_concurrency` (four) calls run at the same time.
    - More than `max_route_calls_per_request` distinct times is refused.
    - Failed times are recorded and the successful ones are kept.
    - If every time fails, the first error is raised.
    """
    settings = get_settings()
    times = sorted(set(departures))
    if not times:
        raise RoutingError(
            "There were no departure times to check.", code="bad_request"
        )
    if len(times) > settings.max_route_calls_per_request:
        raise RoutingError(
            "Too many departure times were requested at once.", code="too_many"
        )

    semaphore = asyncio.Semaphore(max(1, settings.sweep_concurrency))

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:

        async def one(
            when: datetime,
        ) -> tuple[datetime, list[RouteOption] | None, RoutingError | None]:
            async with semaphore:
                try:
                    return (
                        when,
                        await fetch_routes(origin, destination, when, client=client),
                        None,
                    )
                except RoutingError as exc:
                    return when, None, exc

        outcomes = await asyncio.gather(*(one(t) for t in times))

    result = SweepResult()
    for when, options, error in outcomes:
        if options is not None:
            result.routes[when] = options
        else:
            result.failed.append(when)
            if error is not None:
                result.errors.append(error)

    if not result.routes:
        raise (
            result.errors[0]
            if result.errors
            else RoutingError(
                "Every departure time failed.", code="bad_response", retryable=True
            )
        )
    return result
