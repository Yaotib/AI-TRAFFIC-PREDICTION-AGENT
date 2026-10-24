from datetime import datetime, timedelta

import pytest
from app import schemas as s
from app.timeutil import ACCRA_TZ
from pydantic import ValidationError


def _cand(minutes=30):
    dep = datetime(2026, 10, 26, 7, 30, tzinfo=ACCRA_TZ)
    return s.CandidateDeparture(
        departure_time=dep,
        duration_minutes=minutes,
        arrival_time=dep + timedelta(minutes=minutes),
    )


def test_candidate_rejects_inconsistent_arrival():
    dep = datetime(2026, 10, 26, 7, 30, tzinfo=ACCRA_TZ)
    with pytest.raises(ValidationError):
        s.CandidateDeparture(
            departure_time=dep,
            duration_minutes=30,
            arrival_time=dep + timedelta(minutes=31),  # off by one minute
        )


def test_place_validates_coordinates():
    s.Place(place_id="p1", name="Accra Mall", lat=5.62, lng=-0.17)
    with pytest.raises(ValidationError):
        s.Place(place_id="p1", name="x", lat=95, lng=0)


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
            mode="leave_at",
            time=datetime(2026, 10, 26, 8, 0),
        )


def test_decision_result_simulated_flag():
    c = _cand()
    d = s.DecisionResult(
        mode=s.DecisionMode.PREFERRED,
        kind=s.DecisionKind.KEEP_PLAN,
        data_source=s.DataSource.SIMULATED,
        candidates=[c],
        recommended=c,
        baseline=c,
    )
    assert d.is_simulated is True
