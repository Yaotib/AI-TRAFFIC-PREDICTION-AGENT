# backend/app/engine/decision.py
from datetime import datetime, timedelta

from ..schemas import Candidate, CandidateView, DataLabels, DecisionResult, RouteOption
from ..timeutil import fmt_date, fmt_time

LOW_VARIATION_MIN = 3  # tunable: below this spread, flag low variation
LOW_VARIATION = (
    "Traffic estimates barely vary across these times, so timing may matter little "
    "or the provider's data may not reflect traffic on this route."
)
SIMULATED = "This result uses simulated demo data, not real traffic."


def build_candidate(departure: datetime, options: list[RouteOption]) -> Candidate:
    best = min(options, key=lambda o: o.duration_s)
    duration_min = round(best.duration_s / 60)
    static_min = (
        round(best.static_duration_s / 60) if best.static_duration_s is not None else None
    )
    return Candidate(
        departure=departure,
        arrival=departure + timedelta(minutes=duration_min),
        duration_min=duration_min,
        static_duration_min=static_min,
        distance_km=round(best.distance_m / 1000, 1),
        route_description=best.description,
        alternatives_count=len(options),
    )


def _ceil_to_5(dt: datetime) -> datetime:
    dt = dt.replace(second=0, microsecond=0)
    return dt + timedelta(minutes=(-dt.minute) % 5)


def departure_slots(
    mode: str, target: datetime, now: datetime, step_min: int = 15, window_min: int = 120
) -> list[datetime]:
    earliest = _ceil_to_5(now + timedelta(minutes=2))
    if mode == "arrive_by":
        start = max(earliest, _ceil_to_5(target - timedelta(minutes=window_min)))
        end = target - timedelta(minutes=15)
    else:
        half = window_min // 2
        start = max(earliest, target - timedelta(minutes=half))
        end = target + timedelta(minutes=half)
    slots: list[datetime] = []
    t = start
    while t <= end:
        slots.append(t)
        t += timedelta(minutes=step_min)
    if mode == "depart_around" and target >= earliest and target not in slots:
        slots.append(target)
        slots.sort()
    return slots


def _view(c: Candidate) -> CandidateView:
    delay = None
    if c.static_duration_min is not None:
        delay = max(0, c.duration_min - c.static_duration_min)
    return CandidateView(
        departure_local=fmt_time(c.departure),
        arrival_local=fmt_time(c.arrival),
        duration_min=c.duration_min,
        static_duration_min=c.static_duration_min,
        traffic_delay_min=delay,
        distance_km=c.distance_km,
        route_description=c.route_description,
        alternatives_count=c.alternatives_count,
    )


def decide(
    *,
    mode: str,
    candidates: list[Candidate],
    target: datetime,
    origin_name: str,
    destination_name: str,
    labels: DataLabels,
    buffer_min: int = 10,
    gain_min: int = 5,
    failed_slots: int = 0,
    requested_slots: int = 0,
) -> DecisionResult:
    cs = sorted(candidates, key=lambda c: c.departure)
    warnings: list[str] = []
    if labels.simulated:
        warnings.append(SIMULATED)
    if failed_slots:
        warnings.append(
            f"{failed_slots} of {requested_slots} time slots could not be retrieved, "
            "so fewer options were compared."
        )

    def build(
        status: str,
        rule: str,
        rec: Candidate | None = None,
        baseline: Candidate | None = None,
        baseline_label: str | None = None,
        saved: int | None = None,
        margin: int | None = None,
        spread: int = 0,
        extra_warnings: tuple[str, ...] = (),
    ) -> DecisionResult:
        return DecisionResult(
            status=status,
            mode=mode,
            rule_applied=rule,
            origin_name=origin_name,
            destination_name=destination_name,
            date_local=fmt_date(target),
            deadline_local=fmt_time(target) if mode == "arrive_by" else None,
            desired_departure_local=fmt_time(target) if mode == "depart_around" else None,
            recommended=_view(rec) if rec else None,
            baseline=_view(baseline) if baseline else None,
            baseline_label=baseline_label,
            time_saved_min=saved,
            deadline_margin_min=margin,
            spread_min=spread,
            buffer_min=buffer_min if mode == "arrive_by" else None,
            gain_min=gain_min,
            candidates=[_view(c) for c in cs],
            warnings=warnings + list(extra_warnings),
            labels=labels,
        )

    if len(cs) < 2:
        return build(
            "insufficient_data",
            "fewer_than_two_time_slots",
            extra_warnings=("Not enough time slots could be retrieved to compare.",),
        )

    durations = [c.duration_min for c in cs]
    spread = max(durations) - min(durations)
    if spread < LOW_VARIATION_MIN:
        warnings.append(LOW_VARIATION)

    if mode == "arrive_by":
        feasible = [c for c in cs if c.arrival + timedelta(minutes=buffer_min) <= target]
        if not feasible:
            return build(
                "no_feasible_time",
                "no_departure_arrives_before_deadline_with_buffer",
                spread=spread,
            )
        fastest = min(c.duration_min for c in feasible)
        acceptable = [c for c in feasible if c.duration_min <= fastest + gain_min]
        rec = max(acceptable, key=lambda c: c.departure)
        baseline = max(feasible, key=lambda c: c.departure)
        margin = int((target - rec.arrival).total_seconds() // 60)
        return build(
            "recommended",
            "arrive_by_latest_departure_within_gain_of_fastest_feasible",
            rec=rec,
            baseline=baseline,
            baseline_label=f"leaving at {fmt_time(baseline.departure)}",
            saved=baseline.duration_min - rec.duration_min,
            margin=margin,
            spread=spread,
        )

    baseline = min(cs, key=lambda c: abs((c.departure - target).total_seconds()))
    best = min(
        cs,
        key=lambda c: (c.duration_min, abs((c.departure - target).total_seconds())),
    )
    gain = baseline.duration_min - best.duration_min
    label = f"leaving at {fmt_time(baseline.departure)}"
    if gain >= gain_min:
        return build(
            "recommended",
            "shift_departure_for_meaningful_gain",
            rec=best,
            baseline=baseline,
            baseline_label=label,
            saved=gain,
            spread=spread,
        )
    return build(
        "keep_desired_time",
        "no_meaningful_gain_keep_desired_time",
        rec=baseline,
        baseline=baseline,
        baseline_label=label,
        saved=0,
        spread=spread,
    )