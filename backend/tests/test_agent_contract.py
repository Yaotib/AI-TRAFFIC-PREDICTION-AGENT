"""Guards the names the agent code (app/agent/tools.py, loop.py) reads.

compact_for_llm below is copied from app/agent/tools.py. If someone renames a
field in schemas.py, this test fails here instead of failing inside the agent.
"""

import json
from datetime import datetime, timedelta

from app import schemas as s
from app.timeutil import ACCRA_TZ


def compact_for_llm(r: s.DecisionResult) -> dict:
    rec = r.recommended
    return {
        "status": r.status,
        "mode": r.mode,
        "rule": r.rule_applied,
        "origin": r.origin_name,
        "destination": r.destination_name,
        "date": r.date_local,
        "deadline": r.deadline_local,
        "preferred_departure": r.desired_departure_local,
        "recommended_departure": rec.departure_local if rec else None,
        "recommended_arrival": rec.arrival_local if rec else None,
        "trip_minutes": rec.duration_min if rec else None,
        "minutes_saved": r.time_saved_min,
        "compared_with": r.baseline_label,
        "minutes_to_spare": r.deadline_margin_min,
        "safety_buffer_minutes": r.buffer_min,
        "meaningful_gain_minutes": r.gain_min,
        "options_checked": [
            f"{c.departure_local} -> {c.duration_min} min" for c in r.candidates
        ],
        "warnings": r.warnings,
        "data": {
            "source": r.labels.source,
            "simulated": r.labels.simulated,
            "note": r.labels.note,
        },
        "context": r.context,
    }


def _make_result() -> s.DecisionResult:
    dep = datetime(2026, 10, 26, 7, 30, tzinfo=ACCRA_TZ)
    cands = [
        s.CandidateDeparture(
            departure_time=dep + timedelta(minutes=15 * i),
            duration_min=40 - 3 * i,
            arrival_time=dep + timedelta(minutes=15 * i + 40 - 3 * i),
        )
        for i in range(3)
    ]
    return s.DecisionResult(
        status=s.DecisionStatus.RECOMMEND_DEPARTURE,
        mode="arrive_by",
        rule_applied="Arrive at least 10 minutes early.",
        origin_name="Madina",
        destination_name="Airport",
        date_local="2026-10-26",
        deadline_local="09:00",
        recommended=cands[2],
        deadline_margin_min=24,
        buffer_min=10,
        gain_min=5,
        candidates=cands,
        warnings=["Estimates barely vary."],
        warning_codes=[s.WarningCode.LOW_VARIATION],
        labels=s.DataLabels(source="simulated", simulated=True, note="Demo data"),
        context={"rain_chance": "20%"},
    )


def test_every_field_the_agent_reads_exists_and_json_serialises():
    payload = compact_for_llm(_make_result())
    text = json.dumps(payload, ensure_ascii=False)  # loop.py does exactly this
    data = json.loads(text)
    assert data["status"] == "recommend_departure"
    assert data["recommended_departure"] == "08:00"
    assert data["recommended_arrival"] == "08:34"
    assert data["trip_minutes"] == 34
    assert data["options_checked"][0] == "07:30 -> 40 min"
    assert data["data"] == {
        "source": "simulated",
        "simulated": True,
        "note": "Demo data",
    }


def test_result_without_a_recommendation_is_still_readable_by_the_agent():
    r = _make_result().model_copy(
        update={"recommended": None, "status": s.DecisionStatus.NO_FEASIBLE_TIME}
    )
    data = json.loads(json.dumps(compact_for_llm(r)))
    assert data["recommended_departure"] is None and data["trip_minutes"] is None
