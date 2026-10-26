# backend/app/providers/geocoding.py
import httpx

from ..config import get_settings
from ..schemas import Place
from .demo import demo_geocode

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class GeocodingError(Exception):
    pass


async def geocode(query: str, limit: int = 3) -> list[Place]:
    s = get_settings()
    if s.demo_mode:
        return demo_geocode(query)[:limit]
    if not s.google_maps_api_key:
        raise GeocodingError("GOOGLE_MAPS_API_KEY is not set.")
    params = {
        "address": query,
        "components": "country:GH",
        "region": "gh",
        "key": s.google_maps_api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=s.http_timeout_s) as client:
            r = await client.get(GEOCODE_URL, params=params)
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        # Never include the exception text: it can contain the URL and API key.
        raise GeocodingError(f"Geocoding request failed ({type(e).__name__}).") from e
    status = data.get("status")
    if status == "ZERO_RESULTS":
        return []
    if status != "OK":
        raise GeocodingError(f"Geocoding provider returned status {status}.")
    places: list[Place] = []
    for i, item in enumerate(data["results"][:limit], start=1):
        loc = item["geometry"]["location"]
        places.append(
            Place(
                id=f"place_{i}",
                name=item["formatted_address"],
                lat=loc["lat"],
                lng=loc["lng"],
                source="google_geocoding",
            )
        )
    return places