"""Place name -> coordinates, using Google, restricted to Ghana.

Returns at most three candidates and an empty list when nothing matches.
Error messages never contain the request address, because it contains the
API key.
"""

import httpx

from ..config import get_settings
from ..schemas import Place
from . import demo
from .errors import (
    ProviderError,
    describe_status,
    network_message,
    not_configured_message,
    timeout_message,
    unreadable_message,
)

SERVICE = "Google geocoding"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
MAX_CANDIDATES = 3


class GeocodingError(ProviderError):
    """A place lookup failed. The message is safe to show to users."""


def _error(code_msg: tuple[str, str, bool]) -> GeocodingError:
    code, message, retryable = code_msg
    return GeocodingError(message, code=code, retryable=retryable)


def _place_name(result: dict) -> str:
    address = str(result.get("formatted_address") or "").strip()
    return address.split(",")[0].strip() or "Unnamed place"


def _parse_place(result: object) -> Place | None:
    """Turn one Google result into a Place, or None if it is malformed."""
    if not isinstance(result, dict):
        return None
    try:
        loc = result["geometry"]["location"]
        return Place(
            name=_place_name(result),
            address=result.get("formatted_address"),
            lat=float(loc["lat"]),
            lng=float(loc["lng"]),
            provider_place_id=result.get("place_id"),
        )
    except (KeyError, TypeError, ValueError):
        return None


def parse_geocode_response(payload: object) -> list[Place]:
    """Read Google's answer. Raises GeocodingError for failure statuses."""
    if not isinstance(payload, dict):
        raise GeocodingError(
            unreadable_message(SERVICE), code="bad_response", retryable=True
        )

    status = payload.get("status")
    if status == "ZERO_RESULTS":
        return []
    if status in ("OVER_QUERY_LIMIT", "OVER_DAILY_LIMIT"):
        raise _error(describe_status(429, SERVICE))
    if status == "REQUEST_DENIED":
        raise _error(describe_status(403, SERVICE))
    if status == "INVALID_REQUEST":
        raise _error(describe_status(400, SERVICE))
    if status == "UNKNOWN_ERROR":
        raise _error(describe_status(503, SERVICE))
    if status != "OK":
        raise GeocodingError(
            unreadable_message(SERVICE), code="bad_response", retryable=True
        )

    results = payload.get("results")
    if not isinstance(results, list):
        raise GeocodingError(
            unreadable_message(SERVICE), code="bad_response", retryable=True
        )

    places = [p for p in (_parse_place(r) for r in results) if p is not None]
    return places[:MAX_CANDIDATES]


async def geocode(
    query: str, *, client: httpx.AsyncClient | None = None
) -> list[Place]:
    """Look up a place in Ghana. Returns up to three candidates, or []."""
    query = query.strip()
    if not query:
        return []

    settings = get_settings()
    if settings.demo_mode:
        return demo.demo_geocode(query)

    if settings.google_maps_api_key is None:
        raise GeocodingError(not_configured_message(SERVICE), code="not_configured")

    params = {
        "address": query,
        "components": "country:GH",  # Ghana only
        "region": "gh",
        "key": settings.google_maps_api_key.get_secret_value(),
    }

    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=settings.request_timeout_seconds)
    try:
        response = await http.get(GEOCODE_URL, params=params)
    except httpx.TimeoutException:
        raise GeocodingError(
            timeout_message(SERVICE), code="timeout", retryable=True
        ) from None
    except httpx.HTTPError:
        # str() of these errors can include the request address (and the key).
        raise GeocodingError(
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
        raise GeocodingError(
            unreadable_message(SERVICE), code="bad_response", retryable=True
        ) from None

    return parse_geocode_response(payload)
