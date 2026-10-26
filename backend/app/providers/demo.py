# backend/app/providers/demo.py
"""Simulated data for DEMO_MODE. Every result built from this is labelled simulated."""
import math
from datetime import datetime

from ..schemas import Place, RouteOption
from ..timeutil import tz

# Approximate coordinates, for demo only.
DEMO_PLACES = {
    "madina": ("Madina, Accra (demo coordinates)", 5.6683, -0.1668),
    "accra central": ("Accra Central, Accra (demo coordinates)", 5.5469, -0.2069),
    "osu": ("Osu, Accra (demo coordinates)", 5.5560, -0.1769),
    "achimota": ("Achimota, Accra (demo coordinates)", 5.6200, -0.2300),
    "circle": ("Kwame Nkrumah Circle, Accra (demo coordinates)", 5.5700, -0.2179),
    "airport": ("Kotoka International Airport, Accra (demo coordinates)", 5.6052, -0.1668),
}


def demo_geocode(query: str) -> list[Place]:
    q = query.strip().lower()
    out: list[Place] = []
    for key, (name, lat, lng) in DEMO_PLACES.items():
        if key in q or q in key:
            out.append(
                Place(id=f"place_{len(out) + 1}", name=name, lat=lat, lng=lng, source="demo_fixture")
            )
    return out


def _km(a: Place, b: Place) -> float:
    r = 6371.0
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp = p2 - p1
    dl = math.radians(b.lng - a.lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def demo_routes(origin: Place, dest: Place, departure: datetime) -> list[RouteOption]:
    road_km = _km(origin, dest) * 1.35
    free_flow_s = road_km / 40 * 3600
    local = departure.astimezone(tz())
    hour = local.hour + local.minute / 60
    mult = (
        1
        + 0.9 * math.exp(-(((hour - 7.75) / 1.1) ** 2))
        + 1.0 * math.exp(-(((hour - 17.5) / 1.4) ** 2))
    )
    route_a = RouteOption(
        duration_s=int(free_flow_s * mult),
        static_duration_s=int(free_flow_s),
        distance_m=int(road_km * 1000),
        description="Demo route A",
    )
    route_b = RouteOption(
        duration_s=int(free_flow_s * 1.15 * (1 + (mult - 1) * 0.7)),
        static_duration_s=int(free_flow_s * 1.15),
        distance_m=int(road_km * 1150),
        description="Demo route B",
    )
    return [route_a, route_b]