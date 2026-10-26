# backend/app/services/planner.py
from datetime import datetime

from ..config import get_settings
from ..engine.decision import build_candidate, decide, departure_slots
from ..providers.context import get_context
from ..providers.geocoding import geocode
from ..providers.routing import sweep
from ..schemas import Candidate, DataLabels, DecisionResult, Place
from ..timeutil import fmt_time, now_local, parse_local


class PlanError(Exception):
    pass


def _labels() -> DataLabels:
    if get_settings().demo_mode:
        return DataLabels(
            source="demo_fixture",
            duration_type="simulated",
            simulated=True,
            note="Simulated demonstration data. Not real traffic.",
        )
    return DataLabels(
        source="google_routes",
        duration_type="traffic_aware_estimate",
        simulated=False,
        note="Provider estimates for each departure time. Not independently verified live traffic.",
    )


def _context_time(result: DecisionResult, candidates: list[Candidate], target: datetime) -> datetime:
    if result.recommended:
        for c in candidates:
            if fmt_time(c.departure) == result.recommended.departure_local:
                return c.departure
    return target


async def plan_between(origin: Place, dest: Place, mode: str, target: datetime) -> DecisionResult:
    s = get_settings()
    slots = departure_slots(mode, target, now_local(), s.sweep_step_min, s.sweep_window_min)
    if len(slots) < 2:
        raise PlanError(
            "That time is too close or has already passed, so departure times cannot be compared. "
            "Choose a later time."
        )
    results = await sweep(origin, dest, slots)
    candidates = [build_candidate(d, opts) for d, opts in sorted(results.items()) if opts]
    if not candidates:
        raise PlanError("No driving route was found between these two places.")
    result = decide(
        mode=mode,
        candidates=candidates,
        target=target,
        origin_name=origin.name,
        destination_name=dest.name,
        labels=_labels(),
        buffer_min=s.buffer_min,
        gain_min=s.gain_min,
        failed_slots=len(slots) - len(candidates),
        requested_slots=len(slots),
    )
    result.context = await get_context(dest.lat, dest.lng, _context_time(result, candidates, target))
    return result


async def plan_from_text(
    origin_text: str, destination_text: str, mode: str, time_local: str
) -> DecisionResult:
    try:
        target = parse_local(time_local)
    except ValueError as e:
        raise PlanError("Time must look like 2026-10-26T08:30.") from e
    origins = await geocode(origin_text)
    destinations = await geocode(destination_text)
    if not origins:
        raise PlanError(f"Could not find '{origin_text}' in Ghana.")
    if not destinations:
        raise PlanError(f"Could not find '{destination_text}' in Ghana.")
    return await plan_between(origins[0], destinations[0], mode, target)