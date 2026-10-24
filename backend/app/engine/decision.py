import math
from datetime import datetime, timedelta
from typing import NamedTuple

from app.schemas import (
    CandidateDeparture,
    DecisionWarning,
    RouteOption,
    WarningCode,
)

SLOT_MINUTES = 15
MIN_SAVING_MIN = 5
LOW_VARIATION_MIN = 3

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




def preferred_slots(preferred: datetime, now: datetime) -> list[datetime]:
    """Every 15 min from 1 hour before to 1 hour after the preferred time."""
    start = preferred - timedelta(hours=1)
    stop = preferred + timedelta(hours=1)
    slots = []
    t = start
    while t <= stop:
        if t > now:
            slots.append(t)
        t += timedelta(minutes=SLOT_MINUTES)
    return slots


class PreferredChoice(NamedTuple):
    baseline: CandidateDeparture | None  # the user's own plan
    best: CandidateDeparture             # the fastest option checked
    minutes_saved: int
    shift: bool                          # True = suggest a different time


def recommend_for_preferred(
    candidates: list[CandidateDeparture], preferred: datetime
) -> PreferredChoice | None:
    """Suggest a different time only if it saves at least 5 minutes of driving."""
    if not candidates:
        return None
    baseline = next((c for c in candidates if c.departure_time == preferred), None)
    best = min(
        candidates,
        key=lambda c: (c.duration_minutes, abs(c.departure_time - preferred)),
    )
    if baseline is None:
        return PreferredChoice(None, best, 0, False)
    saved = baseline.duration_minutes - best.duration_minutes
    return PreferredChoice(baseline, best, saved, saved >= MIN_SAVING_MIN)

def build_warnings(
    candidates: list[CandidateDeparture],
    slots_requested: int,
    slots_failed: int,
    simulated: bool,
) -> list[DecisionWarning]:
    """Honest warnings about how far the recommendation can be trusted."""
    warnings = []
    if len(candidates) >= 2:
        durations = [c.duration_minutes for c in candidates]
        if max(durations) - min(durations) < LOW_VARIATION_MIN:
            warnings.append(DecisionWarning(
                code=WarningCode.LOW_VARIATION,
                message="Estimated trip times barely change across these departure "
                        "times, so leaving earlier or later makes little difference.",
            ))
    if slots_failed > 0:
        warnings.append(DecisionWarning(
            code=WarningCode.SLOTS_FAILED,
            message=f"{slots_failed} of {slots_requested} departure times could not "
                    "be checked, so this recommendation uses incomplete data.",
        ))
    if simulated:
        warnings.append(DecisionWarning(
            code=WarningCode.SIMULATED_DATA,
            message="These times are simulated demo data, not real traffic estimates.",
        ))
    return warnings