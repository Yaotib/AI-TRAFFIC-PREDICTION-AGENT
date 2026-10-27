# backend/app/engine/explain.py
from ..schemas import DecisionResult


def template_explanation(r: DecisionResult) -> str:
    """Deterministic fallback explanation, built only from the decision result."""
    tail = " These are provider estimates for each departure time, not verified live traffic."
    if r.labels.simulated:
        tail = " This uses simulated demo data, not real traffic."
    rec = r.recommended
    if r.status == "recommended" and r.mode == "arrive_by" and rec:
        text = (
            f"To reach {r.destination_name} by {r.deadline_local}, leave {r.origin_name} "
            f"at {rec.departure_local}. The trip is estimated at {rec.duration_min} minutes, "
            f"arriving at {rec.arrival_local}, which leaves {r.deadline_margin_min} minutes to spare."
        )
        if r.time_saved_min:
            text += f" That is {r.time_saved_min} minutes shorter than {r.baseline_label}."
        return text + tail
    if r.status == "recommended" and rec:
        return (
            f"Leaving at {rec.departure_local} instead of {r.desired_departure_local} is "
            f"estimated to save {r.time_saved_min} minutes. The trip would take "
            f"{rec.duration_min} minutes, arriving at {rec.arrival_local}." + tail
        )
    if r.status == "keep_desired_time" and rec:
        return (
            f"Leaving at {rec.departure_local} is fine. No nearby departure time saves at "
            f"least {r.gain_min} minutes. The trip is estimated at {rec.duration_min} minutes." + tail
        )
    if r.status == "no_feasible_time":
        return (
            f"None of the departure times checked would reach {r.destination_name} by "
            f"{r.deadline_local} with a {r.buffer_min}-minute buffer. Try a later deadline "
            "or an earlier departure." + tail
        )
    return "There was not enough data to compare departure times." + tail