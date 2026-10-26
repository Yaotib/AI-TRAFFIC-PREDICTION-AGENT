# backend/tests/test_routing.py
from datetime import UTC, datetime

import httpx
import pytest
import respx
from app.providers.routing import ROUTES_URL, RoutingError, compute_routes
from app.schemas import Place

A = Place(id="p1", name="A", lat=5.66, lng=-0.16, source="google_geocoding")
B = Place(id="p2", name="B", lat=5.55, lng=-0.20, source="google_geocoding")
DEP = datetime(2026, 10, 26, 8, 0, tzinfo=UTC)


@respx.mock
async def test_parses_valid_routes_and_skips_malformed():
    payload = {
        "routes": [
            {"duration": "1500s", "staticDuration": "1100s", "distanceMeters": 12000},
            {"distanceMeters": 9000},
        ]
    }
    respx.post(ROUTES_URL).mock(return_value=httpx.Response(200, json=payload))
    async with httpx.AsyncClient() as client:
        routes = await compute_routes(client, A, B, DEP)
    assert len(routes) == 1
    assert routes[0].duration_s == 1500
    assert routes[0].static_duration_s == 1100


@respx.mock
async def test_rate_limit_raises_routing_error():
    respx.post(ROUTES_URL).mock(return_value=httpx.Response(429))
    async with httpx.AsyncClient() as client:
        with pytest.raises(RoutingError):
            await compute_routes(client, A, B, DEP)


@respx.mock
async def test_timeout_raises_routing_error():
    respx.post(ROUTES_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    async with httpx.AsyncClient() as client:
        with pytest.raises(RoutingError):
            await compute_routes(client, A, B, DEP)