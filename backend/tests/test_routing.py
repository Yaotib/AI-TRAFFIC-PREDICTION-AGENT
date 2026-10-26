import asyncio
import json
import logging
from datetime import datetime, timedelta

import httpx
import pytest
import respx

from app.config import get_settings
from app.providers import routing
from app.providers.routing import (
    ROUTES_URL,
    RoutingError,
    fetch_routes,
    parse_duration,
    sweep_departures,
)
from app.schemas import Place
from app.timeutil import ACCRA_TZ

KEY = "SECRET-KEY-123"
ORIGIN = Place(id="p1", name="Madina", lat=5.6683, lng=-0.1654)
DEST = Place(id="p2", name="Airport", lat=5.6052, lng=-0.1668)
DEPARTURE = datetime(2026, 10, 26, 7, 30, tzinfo=ACCRA_TZ)


@pytest.fixture(autouse=True)
def google_env(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", KEY)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _route(
    duration="1500s", static="1200s", meters=12345, description="Via Liberation Rd"
):
    return {
        "duration": duration,
        "staticDuration": static,
        "distanceMeters": meters,
        "description": description,
    }


def _ok(*routes):
    return httpx.Response(200, json={"routes": list(routes)})


# ------------------------------------------------------------ duration text


@pytest.mark.parametrize(
    ("text", "seconds"),
    [("1500s", 1500), ("90s", 90), ("1500.4s", 1500), ("1500.6s", 1501), (" 60s ", 60)],
)
def test_parse_duration_reads_google_text(text, seconds):
    assert parse_duration(text) == seconds


@pytest.mark.parametrize(
    "bad",
    [None, 1500, "", "1500", "25m", "-5s", "0s", "abc", "1,500s", "1500s extra", {}],
)
def test_parse_duration_rejects_anything_else(bad):
    with pytest.raises(ValueError):
        parse_duration(bad)


# ------------------------------------------------------------ one request


@respx.mock
async def test_valid_response_returns_route_options():
    respx.post(ROUTES_URL).mock(
        return_value=_ok(_route(), _route("1700s", "1250s", 13000, "Via N1"))
    )
    options = await fetch_routes(ORIGIN, DEST, DEPARTURE)
    assert [o.duration_seconds for o in options] == [1500, 1700]
    assert options[0].static_duration_seconds == 1200
    assert options[0].distance_meters == 12345
    assert options[0].summary == "Via Liberation Rd"


@respx.mock
async def test_request_is_traffic_aware_with_alternatives_and_utc_time():
    route = respx.post(ROUTES_URL).mock(return_value=_ok(_route()))
    await fetch_routes(ORIGIN, DEST, DEPARTURE)
    request = route.calls.last.request
    body = json.loads(request.content)
    assert body["travelMode"] == "DRIVE"
    assert body["routingPreference"] == "TRAFFIC_AWARE"
    assert body["computeAlternativeRoutes"] is True
    assert body["departureTime"] == "2026-10-26T07:30:00Z"
    assert body["origin"]["location"]["latLng"]["latitude"] == pytest.approx(5.6683)
    assert request.headers["X-Goog-Api-Key"] == KEY
    assert "routes.duration" in request.headers["X-Goog-FieldMask"]
    assert KEY not in str(request.url)  # the key travels in a header, not the address


@respx.mock
async def test_malformed_entries_are_skipped_not_guessed():
    entries = [
        _route(),
        {"distanceMeters": 5},  # no duration
        _route(duration="soon"),  # unreadable duration
        _route(duration="-30s"),
        "nonsense",
        _route("1800s", "oops", "not a number", 42),  # usable, with bad extras
    ]
    respx.post(ROUTES_URL).mock(return_value=_ok(*entries))
    options = await fetch_routes(ORIGIN, DEST, DEPARTURE)
    assert [o.duration_seconds for o in options] == [1500, 1800]
    assert options[1].static_duration_seconds is None
    assert options[1].distance_meters is None
    assert options[1].summary is None


@pytest.mark.parametrize(
    "payload",
    [
        {},  # Google omits "routes" when there is no route
        {"routes": []},
        {"routes": [{"duration": "bad"}, "x"]},  # everything malformed
    ],
)
@respx.mock
async def test_no_usable_route_is_a_clear_error(payload):
    respx.post(ROUTES_URL).mock(return_value=httpx.Response(200, json=payload))
    with pytest.raises(RoutingError) as info:
        await fetch_routes(ORIGIN, DEST, DEPARTURE)
    assert info.value.code == "no_route"


# ------------------------------------------------------------ errors


@pytest.mark.parametrize(
    ("response", "code"),
    [
        (httpx.Response(429), "rate_limited"),
        (httpx.Response(401), "key_rejected"),
        (httpx.Response(403), "key_rejected"),
        (httpx.Response(400), "bad_request"),
        (httpx.Response(503), "unavailable"),
        (httpx.Response(200, text="<html>not json</html>"), "bad_response"),
        (httpx.Response(200, json=["a", "list"]), "bad_response"),
        (httpx.Response(200, json={"routes": "oops"}), "bad_response"),
    ],
)
@respx.mock
async def test_failures_become_friendly_errors(response, code):
    respx.post(ROUTES_URL).mock(return_value=response)
    with pytest.raises(RoutingError) as info:
        await fetch_routes(ORIGIN, DEST, DEPARTURE)
    assert info.value.code == code
    assert KEY not in str(info.value) and "googleapis" not in str(info.value)


@respx.mock
async def test_rate_limit_message_is_retryable_and_friendly():
    respx.post(ROUTES_URL).mock(return_value=httpx.Response(429))
    with pytest.raises(RoutingError) as info:
        await fetch_routes(ORIGIN, DEST, DEPARTURE)
    assert info.value.retryable is True
    assert "too many requests" in str(info.value)


@respx.mock
async def test_timeout_becomes_a_friendly_error():
    respx.post(ROUTES_URL).mock(
        side_effect=httpx.ReadTimeout(f"slow: {ROUTES_URL} {KEY}")
    )
    with pytest.raises(RoutingError) as info:
        await fetch_routes(ORIGIN, DEST, DEPARTURE)
    assert info.value.code == "timeout" and info.value.retryable is True
    assert KEY not in str(info.value) and "googleapis" not in str(info.value)


@respx.mock
async def test_network_failure_never_leaks_the_request_address():
    respx.post(ROUTES_URL).mock(
        side_effect=httpx.ConnectError(f"no route to {ROUTES_URL} {KEY}")
    )
    with pytest.raises(RoutingError) as info:
        await fetch_routes(ORIGIN, DEST, DEPARTURE)
    assert KEY not in str(info.value)
    assert info.value.__cause__ is None


async def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY")
    get_settings.cache_clear()
    with pytest.raises(RoutingError) as info:
        await fetch_routes(ORIGIN, DEST, DEPARTURE)
    assert info.value.code == "not_configured"


@respx.mock
async def test_the_key_never_reaches_the_logs(caplog):
    caplog.set_level(logging.DEBUG)
    respx.post(ROUTES_URL).mock(return_value=_ok(_route()))
    await fetch_routes(ORIGIN, DEST, DEPARTURE)
    assert KEY not in caplog.text


# ------------------------------------------------------------ demo mode


async def test_demo_mode_makes_no_request_and_is_simulated(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(ROUTES_URL)
        options = await fetch_routes(ORIGIN, DEST, DEPARTURE)
        assert not route.called
    assert options and all(o.summary.startswith("Simulated") for o in options)


# ------------------------------------------------------------ the sweep


def _slots(n=8):
    return [DEPARTURE + timedelta(minutes=15 * i) for i in range(n)]


async def test_sweep_never_runs_more_than_four_calls_at_once(monkeypatch):
    running = 0
    peak = 0

    async def fake_fetch(origin, destination, departure, *, client=None):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        return [routing.RouteOption(duration_seconds=1500)]

    monkeypatch.setattr(routing, "fetch_routes", fake_fetch)
    result = await sweep_departures(ORIGIN, DEST, _slots(8))
    assert len(result.routes) == 8
    assert result.failed_count == 0
    assert 1 < peak <= 4


async def test_sweep_refuses_more_than_the_hard_cap(monkeypatch):
    calls = 0

    async def fake_fetch(*args, **kwargs):
        nonlocal calls
        calls += 1
        return [routing.RouteOption(duration_seconds=1500)]

    monkeypatch.setattr(routing, "fetch_routes", fake_fetch)
    with pytest.raises(RoutingError) as info:
        await sweep_departures(ORIGIN, DEST, _slots(13))  # default cap is 12
    assert info.value.code == "too_many"
    assert calls == 0


async def test_sweep_cap_can_be_changed_in_settings(monkeypatch):
    monkeypatch.setenv("MAX_ROUTE_CALLS_PER_REQUEST", "3")
    get_settings.cache_clear()
    with pytest.raises(RoutingError):
        await sweep_departures(ORIGIN, DEST, _slots(4))


async def test_sweep_keeps_successes_when_some_slots_fail(monkeypatch):
    slots = _slots(6)
    bad = {slots[1], slots[4]}

    async def fake_fetch(origin, destination, departure, *, client=None):
        if departure in bad:
            raise RoutingError(
                "Google routing took too long to answer.", code="timeout"
            )
        return [routing.RouteOption(duration_seconds=1500)]

    monkeypatch.setattr(routing, "fetch_routes", fake_fetch)
    result = await sweep_departures(ORIGIN, DEST, slots)
    assert set(result.routes) == set(slots) - bad
    assert sorted(result.failed) == sorted(bad)
    assert result.failed_count == 2 and len(result.errors) == 2


async def test_sweep_raises_when_every_slot_fails(monkeypatch):
    async def fake_fetch(*args, **kwargs):
        raise RoutingError(
            "Google routing is receiving too many requests.", code="rate_limited"
        )

    monkeypatch.setattr(routing, "fetch_routes", fake_fetch)
    with pytest.raises(RoutingError) as info:
        await sweep_departures(ORIGIN, DEST, _slots(5))
    assert info.value.code == "rate_limited"


async def test_sweep_ignores_duplicate_times_and_rejects_an_empty_list(monkeypatch):
    seen = []

    async def fake_fetch(origin, destination, departure, *, client=None):
        seen.append(departure)
        return [routing.RouteOption(duration_seconds=1500)]

    monkeypatch.setattr(routing, "fetch_routes", fake_fetch)
    result = await sweep_departures(ORIGIN, DEST, [DEPARTURE, DEPARTURE, DEPARTURE])
    assert len(seen) == 1 and len(result.routes) == 1
    with pytest.raises(RoutingError):
        await sweep_departures(ORIGIN, DEST, [])


@respx.mock
async def test_sweep_end_to_end_with_mocked_google_keeps_partial_results():
    responses = iter(
        [_ok(_route()), httpx.Response(500), _ok(_route("1600s")), httpx.Response(429)]
    )
    respx.post(ROUTES_URL).mock(side_effect=lambda request: next(responses))
    result = await sweep_departures(ORIGIN, DEST, _slots(4))
    assert len(result.routes) == 2
    assert result.failed_count == 2
    assert {e.code for e in result.errors} == {"unavailable", "rate_limited"}


async def test_sweep_in_demo_mode_is_simulated_and_needs_no_network(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()
    with respx.mock(assert_all_called=False):
        result = await sweep_departures(ORIGIN, DEST, _slots(8))
    assert len(result.routes) == 8
    assert all(
        r.summary.startswith("Simulated")
        for opts in result.routes.values()
        for r in opts
    )
