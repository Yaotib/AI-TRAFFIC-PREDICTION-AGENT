import httpx
import pytest
import respx

from app.config import get_settings
from app.providers import geocoding
from app.providers.geocoding import GEOCODE_URL, GeocodingError, geocode

KEY = "SECRET-KEY-123"


@pytest.fixture(autouse=True)
def google_env(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", KEY)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _result(name="Madina", lat=5.6683, lng=-0.1654, pid="pid-1"):
    return {
        "formatted_address": f"{name}, Accra, Ghana",
        "geometry": {"location": {"lat": lat, "lng": lng}},
        "place_id": pid,
    }


def _ok(*results):
    return httpx.Response(200, json={"status": "OK", "results": list(results)})


@respx.mock
async def test_valid_response_returns_places():
    respx.get(url__startswith=GEOCODE_URL).mock(return_value=_ok(_result()))
    places = await geocode("Madina")
    assert len(places) == 1
    assert places[0].name == "Madina"
    assert places[0].lat == pytest.approx(5.6683)
    assert places[0].provider_place_id == "pid-1"
    assert places[0].simulated is False


@respx.mock
async def test_request_is_restricted_to_ghana():
    route = respx.get(url__startswith=GEOCODE_URL).mock(return_value=_ok(_result()))
    await geocode("Madina")
    params = route.calls.last.request.url.params
    assert params["components"] == "country:GH"
    assert params["region"] == "gh"
    assert params["address"] == "Madina"


@respx.mock
async def test_returns_at_most_three_candidates():
    five = [_result(f"Place {i}", pid=f"p{i}") for i in range(5)]
    respx.get(url__startswith=GEOCODE_URL).mock(return_value=_ok(*five))
    assert len(await geocode("place")) == 3


@respx.mock
async def test_no_matches_returns_an_empty_list():
    respx.get(url__startswith=GEOCODE_URL).mock(
        return_value=httpx.Response(200, json={"status": "ZERO_RESULTS", "results": []})
    )
    assert await geocode("zzzz") == []


@respx.mock
async def test_malformed_results_are_skipped():
    bad = [
        {"formatted_address": "No geometry"},
        "nonsense",
        {"geometry": {"location": {"lat": "x"}}},
    ]
    respx.get(url__startswith=GEOCODE_URL).mock(return_value=_ok(*bad, _result()))
    places = await geocode("Madina")
    assert [p.name for p in places] == ["Madina"]


async def test_empty_query_makes_no_request():
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(url__startswith=GEOCODE_URL)
        assert await geocode("   ") == []
        assert not route.called


# ------------------------------------------------------------ errors


@pytest.mark.parametrize(
    ("response", "code"),
    [
        (httpx.Response(200, json={"status": "OVER_QUERY_LIMIT"}), "rate_limited"),
        (httpx.Response(200, json={"status": "REQUEST_DENIED"}), "key_rejected"),
        (httpx.Response(200, json={"status": "INVALID_REQUEST"}), "bad_request"),
        (httpx.Response(200, json={"status": "UNKNOWN_ERROR"}), "unavailable"),
        (httpx.Response(200, json={"status": "SURPRISE"}), "bad_response"),
        (httpx.Response(200, json=["not", "a", "dict"]), "bad_response"),
        (httpx.Response(200, json={"status": "OK", "results": "oops"}), "bad_response"),
        (httpx.Response(200, text="<html>not json</html>"), "bad_response"),
        (httpx.Response(429), "rate_limited"),
        (httpx.Response(403), "key_rejected"),
        (httpx.Response(500), "unavailable"),
    ],
)
@respx.mock
async def test_failures_become_friendly_errors(response, code):
    respx.get(url__startswith=GEOCODE_URL).mock(return_value=response)
    with pytest.raises(GeocodingError) as info:
        await geocode("Madina")
    assert info.value.code == code
    assert KEY not in str(info.value)
    assert "googleapis" not in str(info.value)


@respx.mock
async def test_timeout_becomes_a_friendly_error():
    respx.get(url__startswith=GEOCODE_URL).mock(
        side_effect=httpx.ConnectTimeout(f"timed out calling {GEOCODE_URL}?key={KEY}")
    )
    with pytest.raises(GeocodingError) as info:
        await geocode("Madina")
    assert info.value.code == "timeout" and info.value.retryable is True
    assert KEY not in str(info.value) and "googleapis" not in str(info.value)


@respx.mock
async def test_network_failure_never_leaks_the_request_address():
    respx.get(url__startswith=GEOCODE_URL).mock(
        side_effect=httpx.ConnectError(f"cannot connect to {GEOCODE_URL}?key={KEY}")
    )
    with pytest.raises(GeocodingError) as info:
        await geocode("Madina")
    assert KEY not in str(info.value) and "googleapis" not in str(info.value)
    assert info.value.__cause__ is None  # the original error text is not chained either


async def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY")
    get_settings.cache_clear()
    with pytest.raises(GeocodingError) as info:
        await geocode("Madina")
    assert info.value.code == "not_configured"


# ------------------------------------------------------------ demo mode and logging


async def test_demo_mode_makes_no_request_and_labels_places_simulated(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(url__startswith=GEOCODE_URL)
        places = await geocode("Madina")
        assert not route.called
    assert places and all(p.simulated for p in places)


@respx.mock
async def test_the_key_never_reaches_the_logs(caplog):
    import logging

    caplog.set_level(logging.DEBUG)
    respx.get(url__startswith=GEOCODE_URL).mock(return_value=_ok(_result()))
    await geocode("Madina")
    assert KEY not in caplog.text


def test_http_library_logging_is_turned_down():
    import logging

    assert geocoding  # importing the providers package sets this up
    for name in ("httpx", "httpcore"):
        assert logging.getLogger(name).getEffectiveLevel() >= logging.WARNING
