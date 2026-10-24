import math
from datetime import datetime, timedelta

from app.schemas import CandidateDeparture, RouteOption

SLOT_MINUTES = 15


def deadline_slots(deadline: datetime, now: datetime) -> list[datetime]:
    """Every 15 min in the 2 hours before the deadline, stopping 15 min before it."""
    start = deadline - timedelta(hours=2)
    stop = deadline - timedelta(minutes=SLOT_MINUTES)
    slots = []
    t = start
    while t <= stop:
        if t > now:
            slots.append(t)
        t += timedelta(minutes=SLOT_MINUTES)
    return slots


def build_candidate(departure: datetime, routes: list[RouteOption]) -> CandidateDeparture:
    """Pick the fastest route at this departure time and turn it into a candidate."""
    if not routes:
        raise ValueError("no routes to choose from")
    fastest = min(routes, key=lambda r: r.duration_seconds)
    minutes = math.ceil(fastest.duration_seconds / 60)
    km = round(fastest.distance_meters / 1000, 1) if fastest.distance_meters is not None else None
    return CandidateDeparture(
        departure_time=departure,
        duration_minutes=minutes,
        arrival_time=departure + timedelta(minutes=minutes),
        distance_km=km,
        route_summary=fastest.summary,
    )




ARRIVE_EARLY_MIN = 10
NEAR_FASTEST_MIN = 5


def recommend_for_deadline(
    candidates: list[CandidateDeparture], deadline: datetime
) -> CandidateDeparture | None:
    """Latest departure within 5 min of the fastest trip that arrives 10+ min early."""
    latest_ok = deadline - timedelta(minutes=ARRIVE_EARLY_MIN)
    acceptable = [c for c in candidates if c.arrival_time <= latest_ok]
    if not acceptable:
        return None
    fastest = min(c.duration_minutes for c in acceptable)
    near_fastest = [c for c in acceptable if c.duration_minutes <= fastest + NEAR_FASTEST_MIN]
    return max(near_fastest, key=lambda c: c.departure_time)