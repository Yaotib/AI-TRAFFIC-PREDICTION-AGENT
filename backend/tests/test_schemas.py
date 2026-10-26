from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app import schemas as s
from app.timeutil import ACCRA_TZ


def _candidate(minutes=30):
    departure = datetime(2026, 10, 26, 7, 30, tzinfo=ACCRA_TZ)
    return s.Candidate(
        departure=departure,
        arrival=departure + timedelta(minutes=minutes),
        duration_min=minutes,
        static_duration_min=None,
        distance_km=10.0,
        route_description="Test route",
        alternatives_count=1,
    )


def test_candidate_accepts_current_schema():
    candidate = _candidate()

    assert candidate.duration_min == 30
    assert candidate.arrival - candidate.departure == timedelta(minutes=30)


def test_place_accepts_current_required_fields():
    place = s.Place(
        id="p1",
        name="Accra Mall",
        lat=5.62,
        lng=-0.17,
        source="demo_fixture",
    )

    assert place.id == "p1"
    assert place.name == "Accra Mall"


def test_place_rejects_invalid_source():
    with pytest.raises(ValidationError):
        s.Place(
            id="p1",
            name="Accra Mall",
            lat=5.62,
            lng=-0.17,
            source="unknown",
        )


def test_plan_request_accepts_current_fields():
    request = s.PlanRequest(
        origin="Accra Mall",
        destination="Legon",
        mode="arrive_by",
        time_local="2026-10-26T08:00",
    )

    assert request.origin == "Accra Mall"
    assert request.destination == "Legon"
    assert request.mode == "arrive_by"
    assert request.time_local == "2026-10-26T08:00"


def test_plan_request_rejects_invalid_mode():
    with pytest.raises(ValidationError):
        s.PlanRequest(
            origin="Accra Mall",
            destination="Legon",
            mode="leave_at",
            time_local="2026-10-26T08:00",
        )


def test_plan_request_rejects_short_location():
    with pytest.raises(ValidationError):
        s.PlanRequest(
            origin="A",
            destination="Legon",
            mode="arrive_by",
            time_local="2026-10-26T08:00",
        )


def test_data_labels_simulated_flag():
    labels = s.DataLabels(
        source="demo",
        duration_type="simulated",
        simulated=True,
        note="Demo data",
    )

    assert labels.simulated is True


def test_decision_result_accepts_current_schema():
    candidate = _candidate()
    candidate_view = s.CandidateView(
        departure_local="07:30",
        arrival_local="08:00",
        duration_min=30,
        static_duration_min=None,
        traffic_delay_min=None,
        distance_km=10.0,
        route_description="Test route",
        alternatives_count=1,
    )

    result = s.DecisionResult(
        status="recommended",
        mode="arrive_by",
        rule_applied="test_rule",
        origin_name="Accra Mall",
        destination_name="Legon",
        date_local="2026-10-26",
        deadline_local="08:30",
        desired_departure_local=None,
        recommended=candidate_view,
        baseline=candidate_view,
        baseline_label="test baseline",
        time_saved_min=0,
        deadline_margin_min=30,
        spread_min=0,
        buffer_min=10,
        gain_min=5,
        candidates=[candidate_view],
        warnings=[],
        labels=s.DataLabels(
            source="demo",
            duration_type="simulated",
            simulated=True,
            note="Demo data",
        ),
    )

    assert result.labels.simulated is True
    assert result.recommended.duration_min == candidate.duration_min
