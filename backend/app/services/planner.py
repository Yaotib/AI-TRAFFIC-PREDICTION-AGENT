
# backend/app/services/planner.py
import logging
import sqlite3
from datetime import datetime, timedelta

from ..config import get_settings
from ..engine.decision import build_candidate, decide, departure_slots
from ..providers.context import get_context
from ..providers.geocoding import geocode
from ..providers.routing import sweep
from ..schemas import Candidate, DataLabels, DecisionResult, Place
from ..timeutil import fmt_time, now_local, parse_local
from .traffic_store import record_prediction

log = logging.getLogger(__name__)
MIN_PREFERRED_LEAD_MIN = 10  # chosen by us; the guide gives no number


class PlanError(Exception):
    """Raised when a trip-planning request cannot be completed."""


def _labels(source: str = "osrm") -> DataLabels:
    """Describe the source and reliability of the route estimates."""
    if get_settings().demo_mode:
        return DataLabels(
            source="demo_fixture",
            duration_type="simulated",
            simulated=True,
            note="Simulated demonstration data. Not real traffic.",
        )

    if source == "mapbox":
        return DataLabels(
            source="mapbox_driving_traffic",
            duration_type="traffic_aware_estimate",
            simulated=False,
            note=(
                "Traffic-aware estimates from Mapbox Directions. "
                "Typical-condition durations are used as the baseline. "
                "Traffic coverage varies by location and road."
            ),
        )

    return DataLabels(
        source="osrm_plus_simulated_traffic",
        duration_type="simulated_traffic_estimate",
        simulated=True,
        note=(
            "Road routes and baseline durations from OSRM. "
            "Rush-hour adjustments are simulated, not live traffic."
        ),
    )


def _context_time(
    result: DecisionResult,
    candidates: list[Candidate],
    target: datetime,
) -> datetime:
    """Find the selected departure time for contextual information."""
    if result.recommended:
        for candidate in candidates:
            if (
                fmt_time(candidate.departure)
                == result.recommended.departure_local
            ):
                return candidate.departure

    return target


def _save_prediction(
    origin: Place,
    dest: Place,
    result: DecisionResult,
    candidates: list[Candidate],
) -> None:
    """Save the recommended prediction without failing trip planning."""
    if not result.recommended:
        return

    selected = next(
        (
            candidate
            for candidate in candidates
            if fmt_time(candidate.departure)
            == result.recommended.departure_local
        ),
        None,
    )

    if selected is None:
        log.warning(
            "Could not match the recommended departure to a candidate; "
            "prediction was not saved."
        )
        return

    try:
        result.prediction_id = record_prediction(
            origin_name=origin.name,
            destination_name=dest.name,
            origin_lat=origin.lat,
            origin_lng=origin.lng,
            destination_lat=dest.lat,
            destination_lng=dest.lng,
            departure_at=selected.departure,
            predicted_duration_min=selected.duration_min,
            baseline_duration_min=selected.static_duration_min,
            source=result.labels.source,
            simulated=result.labels.simulated,
        )
    except (sqlite3.Error, OSError, ValueError):
        log.exception(
            "Could not save the traffic prediction; "
            "continuing without a prediction ID."
        )


async def plan_between(
    origin: Place,
    dest: Place,
    mode: str,
    target: datetime,
) -> DecisionResult:
    """Plan a journey, evaluate departure options, and save its prediction."""
    settings = get_settings()
    now = now_local()

    if target <= now:
        raise PlanError("That time has already passed. Choose a later time.")
    if mode == "depart_around" and target - now < timedelta(minutes=MIN_PREFERRED_LEAD_MIN):
        raise PlanError(
            f"That departure time is too close. Choose a time at least "
            f"{MIN_PREFERRED_LEAD_MIN} minutes from now."
        )

    slots = departure_slots(
        mode,
        target,
        now,
        settings.sweep_step_min,
        settings.sweep_window_min,
    )

    if len(slots) < 2:
        raise PlanError(
            "That time is too close or has already passed, so departure "
            "times cannot be compared. Choose a later time."
        )

    results = await sweep(origin, dest, slots)

    used_mapbox = any(
        route.description
        and route.description.startswith("Mapbox traffic-aware")
        for options in results.values()
        for route in options
    )

    candidates = [
        build_candidate(departure, options)
        for departure, options in sorted(results.items())
        if options
    ]

    if not candidates:
        raise PlanError(
            "No driving route was found between these two places."
        )

    result = decide(
        mode=mode,
        candidates=candidates,
        target=target,
        origin_name=origin.name,
        destination_name=dest.name,
        labels=_labels("mapbox" if used_mapbox else "osrm"),
        buffer_min=settings.buffer_min,
        gain_min=settings.gain_min,
        failed_slots=len(slots) - len(candidates),
        requested_slots=len(slots),
    )

    _save_prediction(origin, dest, result, candidates)

    result.context = await get_context(
        dest.lat,
        dest.lng,
        _context_time(result, candidates, target),
    )

    return result


async def plan_from_text(
    origin_text: str,
    destination_text: str,
    mode: str,
    time_local: str,
) -> DecisionResult:
    """Geocode the requested places and plan the journey."""
    try:
        target = parse_local(time_local)
    except ValueError as exc:
        raise PlanError(
            "Time must look like 2026-10-26T08:30."
        ) from exc

    origins = await geocode(origin_text)
    destinations = await geocode(destination_text)

    if not origins:
        raise PlanError(f"Could not find '{origin_text}' in Ghana.")

    if not destinations:
        raise PlanError(
            f"Could not find '{destination_text}' in Ghana."
        )

    return await plan_between(
        origins[0],
        destinations[0],
        mode,
        target,
    )
