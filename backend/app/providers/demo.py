"""Demo mode: simulated places and simulated route times.

Used when DEMO_MODE=true, so the whole system can be built and shown without
a Google key. Everything produced here is labelled simulated, and the
numbers follow a believable Accra rush-hour pattern (morning and evening
peaks, lighter weekends). The results are deterministic: the same inputs
always give the same answer, which keeps tests and demos repeatable.

The coordinates below are approximate and for demonstration only.
"""

import math
import re
from datetime import datetime

from ..schemas import Place, RouteOption
from ..timeutil import as_accra

DEMO_NOTE = "Simulated demo data. These are not real traffic estimates."

MAX_CANDIDATES = 3

# (name, aliases, latitude, longitude)
_GAZETTEER: list[tuple[str, tuple[str, ...], float, float]] = [
    ("Madina", ("madina market", "madina estate"), 5.6683, -0.1654),
    ("Accra Mall", ("tetteh quarshie", "tetteh quarshie interchange"), 5.6226, -0.1732),
    ("Kotoka International Airport", ("airport", "kia", "kotoka"), 5.6052, -0.1668),
    ("Osu", ("oxford street", "osu oxford street"), 5.5560, -0.1822),
    (
        "University of Ghana, Legon",
        ("legon", "ug", "university of ghana"),
        5.6502,
        -0.1870,
    ),
    ("Achimota", ("achimota school", "achimota mile 7"), 5.6181, -0.2290),
    (
        "Kwame Nkrumah Circle",
        ("circle", "nkrumah circle", "kwame nkrumah interchange"),
        5.5705,
        -0.2157,
    ),
    ("Tema Station", ("tema station accra",), 5.5493, -0.2093),
    ("Accra Central", ("central", "makola", "makola market"), 5.5502, -0.2174),
    ("Labadi", ("la", "labadi beach"), 5.5600, -0.1450),
    ("East Legon", ("east legon american house",), 5.6360, -0.1550),
    ("Spintex", ("spintex road", "baatsona"), 5.6370, -0.1000),
    ("Tema", ("tema community 1", "tema harbour"), 5.6698, -0.0166),
    ("Kaneshie", ("kaneshie market",), 5.5667, -0.2358),
    ("Dansoman", ("dansoman last stop",), 5.5500, -0.2650),
    ("Adenta", ("adenta housing down",), 5.7120, -0.1670),
    ("Dzorwulu", ("dzorwulu junction",), 5.6100, -0.1950),
    ("Teshie", ("teshie nungua",), 5.5800, -0.1050),
    ("Kasoa", ("kasoa market",), 5.5340, -0.4170),
]

# Straight-line distance is shorter than the road distance. The factor and
# free-flow speed below are rough, chosen only so demo trips look plausible.
_ROAD_FACTOR = 1.35
_FREE_FLOW_KMH = 45.0
_MIN_TRIP_SECONDS = 300


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower()).strip()


def _slug(text: str) -> str:
    return re.sub(r"\s+", "-", _norm(text))


def _score(query: str, name: str, aliases: tuple[str, ...]) -> int:
    q = _norm(query)
    names = [_norm(name), *(_norm(a) for a in aliases)]
    if q in names:
        return 3
    if any(len(q) >= 3 and (q in n or n in q) for n in names):
        return 2
    q_words = {w for w in q.split() if len(w) >= 4}
    if any(q_words & {w for w in n.split() if len(w) >= 4} for n in names):
        return 1
    return 0


def demo_geocode(query: str) -> list[Place]:
    """Return up to three simulated places that match the query."""
    scored = []
    for name, aliases, lat, lng in _GAZETTEER:
        score = _score(query, name, aliases)
        if score:
            scored.append((score, name, lat, lng))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        Place(
            name=name,
            address="Accra, Ghana (simulated place)",
            lat=lat,
            lng=lng,
            provider_place_id=f"demo-{_slug(name)}",
            simulated=True,
        )
        for _, name, lat, lng in scored[:MAX_CANDIDATES]
    ]


def _bump(hour: float, centre: float, width: float) -> float:
    return math.exp(-0.5 * ((hour - centre) / width) ** 2)


def congestion_factor(departure: datetime) -> float:
    """How many times slower than free flow a trip is at this departure time.

    Morning peak around 07:45, evening peak around 17:30, a mild midday bump,
    and lighter weekends. 1.0 means free flow.
    """
    dt = as_accra(departure)
    hour = dt.hour + dt.minute / 60
    weekend = dt.weekday() >= 5
    rush = 0.45 if weekend else 1.0
    return (
        1.0
        + rush * 0.85 * _bump(hour, 7.75, 1.0)
        + rush * 0.95 * _bump(hour, 17.5, 1.3)
        + 0.15 * _bump(hour, 12.5, 2.0)
    )


def _haversine_km(a: Place, b: Place) -> float:
    r = 6371.0
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp = p2 - p1
    dl = math.radians(b.lng - a.lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def demo_routes(
    origin: Place, destination: Place, departure: datetime
) -> list[RouteOption]:
    """Two simulated routes for one departure time.

    The alternative is slower when roads are clear but copes better with
    heavy traffic, so it wins at the peak, as a real alternative sometimes does.
    """
    road_km = max(_haversine_km(origin, destination) * _ROAD_FACTOR, 0.5)
    static = max(road_km / _FREE_FLOW_KMH * 3600, _MIN_TRIP_SECONDS)
    factor = congestion_factor(departure)

    main = round(static * factor)
    alternative = round(static * 1.18 * (1 + 0.45 * (factor - 1)))
    return [
        RouteOption(
            summary="Simulated main route",
            distance_meters=round(road_km * 1000),
            duration_seconds=main,
            static_duration_seconds=round(static),
        ),
        RouteOption(
            summary="Simulated alternative route",
            distance_meters=round(road_km * 1100),
            duration_seconds=alternative,
            static_duration_seconds=round(static * 1.18),
        ),
    ]
