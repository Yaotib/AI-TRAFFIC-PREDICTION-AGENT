from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app import schemas as s
from app.timeutil import ACCRA_TZ


def _cand(minutes=30, hour=7, minute=30):
    dep = datetime(2026, 10, 26, hour, minute, tzinfo=ACCRA_TZ)
    return s.CandidateDeparture(
        departure_time=dep,
        duration_min=minutes,
        arrival_time=dep + timedelta(minutes=minutes),
    )


def _result(**overrides):
    c = _cand()
    base = {
        "status": s.DecisionStatus.KEEP_PLAN,
        "mode": "depart_around",
        "rule_applied": "Keep your plan unless another time saves at least 5 minutes.",
        "origin_name": "Madina",
        "destination_name": "Airport",
        "date_local": "2026-10-26",
        "desired_departure_local": "07:30",
        "recommended": c,
        "baseline": c,
        "baseline_label": "your preferred time",
        "buffer_min": 10,
        "gain_min": 5,
        "candidates": [c],
        "labels": s.DataLabels(
            source="google", simulated=False, note="Provider estimate"
        ),
    }
    base.update(overrides)
    return s.DecisionResult(**base)


# ------------------------------------------------------------ candidates


def test_candidate_numbers_add_up():
    c = _cand(30)
    assert c.arrival_time - c.departure_time == timedelta(minutes=30)


def test_candidate_rejects_inconsistent_arrival():
    dep = datetime(2026, 10, 26, 7, 30, tzinfo=ACCRA_TZ)
    with pytest.raises(ValidationError):
        s.CandidateDeparture(
            departure_time=dep,
            duration_min=30,
            arrival_time=dep + timedelta(minutes=31),  # off by one minute
        )


def test_candidate_local_strings_are_computed_from_the_datetimes():
    c = _cand(45, hour=7, minute=30)
    assert c.departure_local == "07:30"
    assert c.arrival_local == "08:15"
    dumped = c.model_dump(mode="json")
    assert dumped["departure_local"] == "07:30" and dumped["arrival_local"] == "08:15"


def test_candidate_arrival_can_cross_midnight():
    assert _cand(30, hour=23, minute=50).arrival_local == "00:20"


# ------------------------------------------------------------ places and tools


def test_place_id_is_assigned_later_by_the_agent():
    p = s.Place(name="Accra Mall", lat=5.62, lng=-0.17)
    assert p.id == ""
    p2 = p.model_copy(update={"id": "p1"})  # exactly what tools.py does
    assert p2.id == "p1" and p.id == ""


def test_place_validates_coordinates():
    with pytest.raises(ValidationError):
        s.Place(name="x", lat=95, lng=0)


def test_tool_trace_uses_the_agents_field_names():
    t = s.ToolTrace(
        tool="geocode_place",
        arguments={"query": "Madina"},
        ok=True,
        summary="2 candidate(s)",
    )
    assert t.model_dump()["tool"] == "geocode_place"


# ------------------------------------------------------------ labels and decision


def test_labels_must_agree_with_source():
    with pytest.raises(ValidationError):
        s.DataLabels(source="simulated", simulated=False)
    with pytest.raises(ValidationError):
        s.DataLabels(source="google", simulated=True)


def test_decision_result_simulated_flag():
    d = _result(
        labels=s.DataLabels(source="simulated", simulated=True, note="Demo data")
    )
    assert d.is_simulated is True
    assert d.model_dump(mode="json")["labels"]["simulated"] is True


def test_decision_result_rejects_unknown_mode():
    with pytest.raises(ValidationError):
        _result(mode="leave_at")


# ------------------------------------------------------------ requests and responses


def test_plan_request_cleans_text_and_reads_time_as_accra():
    r = s.PlanRequest(
        origin="  Accra Mall ",
        destination="Legon",
        mode="arrive_by",
        time=datetime(2026, 10, 26, 8, 0),
    )
    assert r.origin == "Accra Mall"
    assert r.time.tzinfo == ACCRA_TZ


@pytest.mark.parametrize("bad", ["", "   ", "x" * 201])
def test_plan_request_rejects_bad_text(bad):
    with pytest.raises(ValidationError):
        s.PlanRequest(
            origin=bad,
            destination="Legon",
            mode="depart_around",
            time=datetime(2026, 10, 26, 8, 0),
        )


def test_ask_request_needs_at_least_one_message():
    with pytest.raises(ValidationError):
        s.AskRequest(messages=[])
    r = s.AskRequest(messages=[{"role": "user", "content": "Madina to Airport at 8"}])
    assert r.messages[0].content.startswith("Madina")


def test_ask_response_can_be_built_the_way_loop_py_builds_it():
    r = s.AskResponse(
        reply="Leave at 07:30.",
        explanation_source="template",
        notice=None,
        result=_result(),
        trace=[s.ToolTrace(tool="geocode_place", arguments={}, ok=True, summary="ok")],
    )
    assert r.request_id is None
    for source in ("llm", "template", "none"):
        s.AskResponse(reply="x", explanation_source=source)
    with pytest.raises(ValidationError):
        s.AskResponse(reply="x", explanation_source="ai")
