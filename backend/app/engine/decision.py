import math
from datetime import datetime, timedelta
from typing import NamedTuple

from app.schemas import (
    CandidateDeparture,
    DataSource,
    DecisionKind,
    DecisionMode,
    DecisionResult,
    DecisionWarning,
    RouteOption,
    WarningCode,
)

SLOT_MINUTES = 15
MIN_SAVING_MIN = 5
LOW_VARIATION_MIN = 3
MIN_USABLE_SLOTS = 3
DEADLINE_RULE = (
    "Leave as late as possible, as long as the trip is within 5 minutes of the "
    "fastest option and you arrive at least 10 minutes before your deadline."
)
PREFERRED_RULE = (
    "Keep your planned time unless another departure time saves at least "
    "5 minutes of driving."
)

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


def decide_deadline(
    candidates: list[CandidateDeparture],
    deadline: datetime,
    slots_requested: int,
    simulated: bool,
) -> DecisionResult:
    """Full decision for 'I must arrive by...'."""
    failed = max(0, slots_requested - len(candidates))
    common = {
        "mode": DecisionMode.DEADLINE,
        "data_source": DataSource.SIMULATED if simulated else DataSource.PROVIDER,
        "candidates": sorted(candidates, key=lambda c: c.departure_time),
        "deadline": deadline,
        "slots_requested": slots_requested,
        "slots_failed": failed,
        "warnings": build_warnings(candidates, slots_requested, failed, simulated),
        "rule_summary": DEADLINE_RULE,
    }
    if len(candidates) < MIN_USABLE_SLOTS:
        return DecisionResult(kind=DecisionKind.INSUFFICIENT_DATA, **common)
    rec = recommend_for_deadline(candidates, deadline)
    if rec is None:
        return DecisionResult(kind=DecisionKind.NO_FEASIBLE_TIME, **common)
    spare = int((deadline - rec.arrival_time).total_seconds() // 60)
    return DecisionResult(
        kind=DecisionKind.RECOMMEND_DEPARTURE,
        recommended=rec,
        spare_minutes=spare,
        **common,
    )


def decide_preferred(
    candidates: list[CandidateDeparture],
    preferred: datetime,
    slots_requested: int,
    simulated: bool,
) -> DecisionResult:
    """Full decision for 'I plan to leave at...'."""
    failed = max(0, slots_requested - len(candidates))
    common = {
        "mode": DecisionMode.PREFERRED,
        "data_source": DataSource.SIMULATED if simulated else DataSource.PROVIDER,
        "candidates": sorted(candidates, key=lambda c: c.departure_time),
        "slots_requested": slots_requested,
        "slots_failed": failed,
        "warnings": build_warnings(candidates, slots_requested, failed, simulated),
        "rule_summary": PREFERRED_RULE,
    }
    choice = recommend_for_preferred(candidates, preferred)
    if len(candidates) < MIN_USABLE_SLOTS or choice is None or choice.baseline is None:
        return DecisionResult(kind=DecisionKind.INSUFFICIENT_DATA, **common)
    if choice.shift:
        return DecisionResult(
            kind=DecisionKind.SHIFT_DEPARTURE,
            recommended=choice.best,
            baseline=choice.baseline,
            minutes_saved=choice.minutes_saved,
            **common,
        )
    return DecisionResult(
        kind=DecisionKind.KEEP_PLAN,
        recommended=choice.baseline,
        baseline=choice.baseline,
        minutes_saved=choice.minutes_saved,
        **common,
    )