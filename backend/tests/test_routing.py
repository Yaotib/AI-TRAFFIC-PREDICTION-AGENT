
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest
import respx

from app.providers import routing
from app.providers.routing import RoutingError, sweep
from app.schemas import Place

OSRM_ROUTE_PATTERN = (
    r"https://router\.project-osrm\.org/route/v1/driving/.*"
)

MAPBOX_ROUTE_PATTERN = (
    r"https://api\.mapbox\.com/directions/v5/"
    r"mapbox/driving-traffic/.*"
)

MAPBOX_PAYLOAD = {
    "code": "Ok",
    "routes": [
        {
            "duration": 1000,
            "duration_typical": 800,
            "distance": 5000,
        },
    ],
}

A = Place(
    id="p1",
    name="University of Ghana, Legon",
    lat=5.6466,
    lng=-0.1880,
    source="openstreetmap_nominatim",
)
B = Place(
    id="p2",
    name="Accra Mall",
    lat=5.6228,
    lng=-0.1740,
    source="openstreetmap_nominatim",
)

MORNING = datetime(2026, 10, 26, 8, 0, tzinfo=UTC)
MIDDAY = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)

OSRM_PAYLOAD = {
    "code": "Ok",
    "routes": [
        {"duration": 1500, "distance": 12000},
        {"duration": 1800, "distance": 14000},
        {"distance": 9000},  # Malformed route: no duration
    ],
}


@pytest.fixture(autouse=True)
def routing_settings(monkeypatch):
    """Use OSRM mode without depending on local environment variables."""
    monkeypatch.setattr(
        routing,
        "get_settings",
        lambda: SimpleNamespace(
            demo_mode=False,
            max_route_calls=14,
            http_timeout_s=2.0,
        ),
    )


@respx.mock
async def test_sweep_parses_routes_and_skips_malformed():
    respx.get(url__regex=OSRM_ROUTE_PATTERN).mock(
        return_value=httpx.Response(200, json=OSRM_PAYLOAD)
    )

    results = await sweep(A, B, [MIDDAY])
    routes = results[MIDDAY]

    assert len(routes) == 2
    assert routes[0].distance_m == 12000
    assert routes[0].static_duration_s == 1500
    assert routes[0].duration_s == 1500
    assert routes[0].description == "OSRM route 1"


@respx.mock
async def test_sweep_applies_simulated_rush_hour_adjustment():
    respx.get(url__regex=OSRM_ROUTE_PATTERN).mock(
        return_value=httpx.Response(200, json=OSRM_PAYLOAD)
    )

    results = await sweep(A, B, [MORNING, MIDDAY])

    morning_route = results[MORNING][0]
    midday_route = results[MIDDAY][0]

    assert morning_route.static_duration_s == 1500
    assert midday_route.static_duration_s == 1500
    assert morning_route.duration_s > midday_route.duration_s
    assert morning_route.distance_m == midday_route.distance_m


@respx.mock
async def test_sweep_raises_on_rate_limit():
    respx.get(url__regex=OSRM_ROUTE_PATTERN).mock(
        return_value=httpx.Response(429)
    )

    with pytest.raises(RoutingError):
        await sweep(A, B, [MIDDAY])


@respx.mock
async def test_sweep_raises_on_timeout():
    respx.get(url__regex=OSRM_ROUTE_PATTERN).mock(
        side_effect=httpx.ReadTimeout("slow")
    )

    with pytest.raises(RoutingError):
        await sweep(A, B, [MIDDAY])


@respx.mock
async def test_sweep_raises_when_osrm_finds_no_route():
    respx.get(url__regex=OSRM_ROUTE_PATTERN).mock(
        return_value=httpx.Response(
            200,
            json={"code": "NoRoute", "routes": []},
        )
    )

    with pytest.raises(RoutingError, match="could not find a route"):
        await sweep(A, B, [MIDDAY])


async def test_sweep_rejects_too_many_departures():
    departures = [
        datetime(2026, 10, 26, hour, 0, tzinfo=UTC)
        for hour in range(15)
    ]

    with pytest.raises(RoutingError, match="Too many time slots"):
        await sweep(A, B, departures)

@respx.mock
async def test_sweep_uses_mapbox_traffic_estimates(monkeypatch):
    monkeypatch.setattr(
        routing,
        "get_settings",
        lambda: SimpleNamespace(
            demo_mode=False,
            max_route_calls=14,
            http_timeout_s=2.0,
            mapbox_access_token="test-token",
            mapbox_enabled=True,
        ),
    )

    request = respx.get(
        url__regex=MAPBOX_ROUTE_PATTERN
    ).mock(
        return_value=httpx.Response(
            200,
            json=MAPBOX_PAYLOAD,
        )
    )

    results = await sweep(A, B, [MIDDAY])
    route = results[MIDDAY][0]

    assert request.called
    assert route.duration_s == 1000
    assert route.static_duration_s == 800
    assert route.distance_m == 5000
    assert route.description == "Mapbox traffic-aware route 1"


@respx.mock
async def test_sweep_falls_back_to_osrm_when_mapbox_fails(
    monkeypatch,
):
    monkeypatch.setattr(
        routing,
        "get_settings",
        lambda: SimpleNamespace(
            demo_mode=False,
            max_route_calls=14,
            http_timeout_s=2.0,
            mapbox_access_token="test-token",
            mapbox_enabled=True,
        ),
    )

    respx.get(
        url__regex=MAPBOX_ROUTE_PATTERN
    ).mock(
        return_value=httpx.Response(401)
    )

    respx.get(
        url__regex=OSRM_ROUTE_PATTERN
    ).mock(
        return_value=httpx.Response(
            200,
            json=OSRM_PAYLOAD,
        )
    )

    results = await sweep(A, B, [MIDDAY])
    route = results[MIDDAY][0]

    assert route.description == "OSRM route 1"
    assert route.static_duration_s == 1500
    assert route.duration_s >= route.static_duration_s