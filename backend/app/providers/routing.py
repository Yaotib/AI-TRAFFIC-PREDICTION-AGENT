
"""Traffic-aware routing with Mapbox and an OSRM fallback."""

import math
from datetime import datetime

import httpx

from ..config import get_settings
from ..schemas import Place, RouteOption
from ..timeutil import tz
from .demo import demo_routes

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
MAPBOX_URL = (
    "https://api.mapbox.com/directions/v5/"
    "mapbox/driving-traffic"
)


class RoutingError(Exception):
    """Raised when a routing request cannot be completed."""


def _traffic_multiplier(departure: datetime) -> float:
    """Estimate rush-hour effects; this is simulated, not live traffic."""
    local = departure.astimezone(tz())
    hour = local.hour + local.minute / 60

    return (
        1
        + 0.9 * math.exp(-(((hour - 7.75) / 1.1) ** 2))
        + 1.0 * math.exp(-(((hour - 17.5) / 1.4) ** 2))
    )


def _coordinates(origin: Place, dest: Place) -> str:
    """Mapbox and OSRM both expect longitude,latitude coordinates."""
    return (
        f"{origin.lng},{origin.lat};"
        f"{dest.lng},{dest.lat}"
    )


def _parse_routes(
    data: dict,
    provider: str,
) -> list[RouteOption]:
    """Parse route estimates and skip malformed route entries."""
    if data.get("code") != "Ok":
        message = (
            data.get("message")
            or data.get("code")
            or "Unknown error"
        )
        raise RoutingError(
            f"{provider} could not find a route: {message}"
        )

    options: list[RouteOption] = []

    for index, route in enumerate(data.get("routes", []), start=1):
        duration = route.get("duration")
        distance = route.get("distance")

        if duration is None or distance is None:
            continue

        typical_duration = route.get("duration_typical")
        geometry = route.get("geometry")
        coordinates = (
            geometry.get("coordinates")
            if isinstance(geometry, dict)
            else None
        )

        if not coordinates:
            coordinates = None

        if provider == "Mapbox":
            static_duration = (
                max(1, round(typical_duration))
                if typical_duration is not None
                else None
            )
            description = f"Mapbox traffic-aware route {index}"
        else:
            static_duration = max(1, round(duration))
            description = f"OSRM route {index}"

        options.append(
            RouteOption(
                duration_s=max(1, round(duration)),
                static_duration_s=static_duration,
                distance_m=max(1, round(distance)),
                description=description,
                coordinates=coordinates,
            )
        )

    if not options:
        raise RoutingError(
            f"{provider} did not return any usable routes."
        )

    return options


async def _fetch_base_routes(
    client: httpx.AsyncClient,
    origin: Place,
    dest: Place,
) -> list[RouteOption]:
    """Fetch ordinary OSRM routes without live traffic."""
    try:
        response = await client.get(
            f"{OSRM_URL}/{_coordinates(origin, dest)}",
            params={
                "alternatives": "true",
                "steps": "false",
                "overview": "full",
                "geometries": "geojson",
            },
            headers={"User-Agent": "TrafficPredictionAgent/0.1"},
        )
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException as exc:
        raise RoutingError(
            "OSRM routing request timed out."
        ) from exc
    except httpx.HTTPError as exc:
        raise RoutingError(
            f"OSRM could not be reached ({type(exc).__name__})."
        ) from exc
    except ValueError as exc:
        raise RoutingError("OSRM returned unreadable JSON.") from exc

    return _parse_routes(data, "OSRM")


async def _fetch_mapbox_routes(
    client: httpx.AsyncClient,
    origin: Place,
    dest: Place,
    departure: datetime,
    token: str,
) -> list[RouteOption]:
    """Fetch traffic-aware Mapbox estimates for one departure time."""
    try:
        response = await client.get(
            f"{MAPBOX_URL}/{_coordinates(origin, dest)}",
            params={
                "access_token": token,
                "depart_at": departure.isoformat(timespec="seconds"),
                "alternatives": "true",
                "steps": "false",
                "overview": "full",
                "geometries": "geojson",
            },
        )
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException as exc:
        raise RoutingError(
            "Mapbox routing request timed out."
        ) from exc
    except httpx.HTTPError as exc:
        raise RoutingError(
            f"Mapbox could not be reached ({type(exc).__name__})."
        ) from exc
    except ValueError as exc:
        raise RoutingError("Mapbox returned unreadable JSON.") from exc

    return _parse_routes(data, "Mapbox")


async def _sweep_mapbox(
    origin: Place,
    dest: Place,
    departures: list[datetime],
    token: str,
    timeout: float,
) -> dict[datetime, list[RouteOption]]:
    """Fetch estimates for every requested departure slot."""
    results: dict[datetime, list[RouteOption]] = {}

    async with httpx.AsyncClient(timeout=timeout) as client:
        for departure in departures:
            results[departure] = await _fetch_mapbox_routes(
                client,
                origin,
                dest,
                departure,
                token,
            )

    return results


async def _sweep_osrm(
    origin: Place,
    dest: Place,
    departures: list[datetime],
    timeout: float,
) -> dict[datetime, list[RouteOption]]:
    """Use OSRM and explicitly simulated rush-hour adjustments."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        base_routes = await _fetch_base_routes(
            client,
            origin,
            dest,
        )

    results: dict[datetime, list[RouteOption]] = {}

    for departure in departures:
        multiplier = _traffic_multiplier(departure)
        results[departure] = [
            RouteOption(
                duration_s=max(
                    1,
                    round(route.duration_s * multiplier),
                ),
                static_duration_s=route.static_duration_s,
                distance_m=route.distance_m,
                description=route.description,
                coordinates=route.coordinates,
            )
            for route in base_routes
        ]

    return results


async def sweep(
    origin: Place,
    dest: Place,
    departures: list[datetime],
) -> dict[datetime, list[RouteOption]]:
    """Prefer Mapbox for the complete sweep, then fall back to OSRM."""
    settings = get_settings()

    if len(departures) > settings.max_route_calls:
        raise RoutingError("Too many time slots requested.")

    if not departures:
        return {}

    if settings.demo_mode:
        return {
            departure: demo_routes(origin, dest, departure)
            for departure in departures
        }

    token = getattr(settings, "mapbox_access_token", "").strip()
    mapbox_enabled = getattr(settings, "mapbox_enabled", True)

    if mapbox_enabled and token:
        try:
            return await _sweep_mapbox(
                origin,
                dest,
                departures,
                token,
                settings.http_timeout_s,
            )
        except RoutingError:
            # Fall back for the entire sweep to avoid mixing providers.
            pass

    return await _sweep_osrm(
        origin,
        dest,
        departures,
        settings.http_timeout_s,
    )
