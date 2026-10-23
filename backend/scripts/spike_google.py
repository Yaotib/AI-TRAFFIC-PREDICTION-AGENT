# backend/scripts/spike_google.py
"""Feasibility spike. Run from backend/:  python scripts/spike_google.py"""
import os
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ["GOOGLE_MAPS_API_KEY"]
TZ = ZoneInfo("Africa/Accra")
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
TRIPS = [
    ("Madina", "Accra Central"),
    ("Achimota", "Osu"),
    ("Kotoka International Airport", "Kwame Nkrumah Circle"),
]
HOURS = [(6, 0), (7, 0), (8, 0), (10, 0), (13, 0), (17, 0), (18, 30), (21, 0)]
FIELDS = "routes.duration,routes.staticDuration,routes.distanceMeters"


def geocode(client: httpx.Client, query: str):
    r = client.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={"address": query, "components": "country:GH", "key": KEY},
    )
    data = r.json()
    if data.get("status") != "OK":
        raise SystemExit(f"Geocoding failed for {query}: {data.get('status')}")
    best = data["results"][0]
    return best["formatted_address"], best["geometry"]["location"]


def minutes(value):
    return round(float(value.rstrip("s")) / 60) if value else None


def main():
    day = datetime.now(TZ).date() + timedelta(days=1)
    while day.weekday() >= 5:  # skip weekend
        day += timedelta(days=1)
    with httpx.Client(timeout=15) as client:
        for origin, dest in TRIPS:
            o_name, o = geocode(client, origin)
            d_name, d = geocode(client, dest)
            print(f"\n{o_name} -> {d_name}  ({day})")
            print("depart  traffic  static  extra  routes")
            for h, m in HOURS:
                dep = datetime(day.year, day.month, day.day, h, m, tzinfo=TZ)
                body = {
                    "origin": {"location": {"latLng": {"latitude": o["lat"], "longitude": o["lng"]}}},
                    "destination": {"location": {"latLng": {"latitude": d["lat"], "longitude": d["lng"]}}},
                    "travelMode": "DRIVE",
                    "routingPreference": "TRAFFIC_AWARE",
                    "departureTime": dep.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "computeAlternativeRoutes": True,
                }
                r = client.post(
                    ROUTES_URL,
                    json=body,
                    headers={"X-Goog-Api-Key": KEY, "X-Goog-FieldMask": FIELDS},
                )
                if r.status_code != 200:
                    print(f"{h:02d}:{m:02d}  ERROR {r.status_code} {r.text[:120]}")
                    continue
                routes = r.json().get("routes", [])
                if not routes:
                    print(f"{h:02d}:{m:02d}  no routes")
                    continue
                best = min(routes, key=lambda x: float(x["duration"].rstrip("s")))
                t, s = minutes(best["duration"]), minutes(best.get("staticDuration"))
                extra = (t - s) if s is not None else "?"
                print(f"{h:02d}:{m:02d}   {t:>4}     {s}    {extra:>4}    {len(routes)}")


if __name__ == "__main__":
    main()