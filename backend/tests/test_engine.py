# backend/tests/test_engine.py
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.engine.decision import LOW_VARIATION, SIMULATED, decide, departure_slots
from app.schemas import Candidate, DataLabels

TZ = ZoneInfo("Africa/Accra")
LABELS = DataLabels(
    source="test", duration_type="traffic_aware_estimate", simulated=False, note="t"
)


def cand(hhmm: str, minutes: int) -> Candidate:
    h, m = map(int, hhmm.split(":"))
    dep = datetime(2026, 10, 26, h, m, tzinfo=TZ)
    return Candidate(
        departure=dep,
        arrival=dep + timedelta(minutes=minutes),
        duration_min=minutes,
        static_duration_min=20,
        distance_km=12.0,
        route_description="Test",
        alternatives_count=2,
    )


def at(h: int, m: int = 0) -> datetime:
    return datetime(2026, 10, 26, h, m, tzinfo=TZ)


def run(mode, cands, target, labels=LABELS):
    return decide(
        mode=mode, candidates=cands, target=target,
        origin_name="A", destination_name="B", labels=labels,
    )


def test_arrive_by_latest_departure_within_gain():
    cands = [cand("06:30", 30), cand("07:00", 32), cand("07:30", 45), cand("08:00", 55)]
    r = run("arrive_by", cands, at(9))
    assert r.status == "recommended"
    assert r.recommended.departure_local == "07:00"
    assert r.baseline_label == "leaving at 07:30"
    assert r.time_saved_min == 13
    assert r.deadline_margin_min == 88


def test_arrive_by_no_feasible_time():
    r = run("arrive_by", [cand("06:30", 30), cand("06:45", 35)], at(7))
    assert r.status == "no_feasible_time"
    assert r.recommended is None


def test_depart_around_keeps_time_when_gain_small():
    cands = [cand("07:00", 40), cand("07:15", 36), cand("07:30", 38), cand("07:45", 41)]
    r = run("depart_around", cands, at(7, 30))
    assert r.status == "keep_desired_time"
    assert r.recommended.departure_local == "07:30"
    assert r.time_saved_min == 0


def test_depart_around_shifts_for_meaningful_gain():
    cands = [
        cand("07:00", 52), cand("07:15", 50), cand("07:30", 50),
        cand("07:45", 42), cand("08:00", 35),
    ]
    r = run("depart_around", cands, at(7, 30))
    assert r.status == "recommended"
    assert r.recommended.departure_local == "08:00"
    assert r.time_saved_min == 15


def test_low_variation_warning():
    r = run("arrive_by", [cand("06:30", 30), cand("06:45", 31), cand("07:00", 30)], at(9))
    assert LOW_VARIATION in r.warnings


def test_simulated_data_is_flagged():
    sim = DataLabels(source="demo_fixture", duration_type="simulated", simulated=True, note="s")
    r = run("arrive_by", [cand("06:30", 30), cand("07:00", 40)], at(9), labels=sim)
    assert SIMULATED in r.warnings


def test_insufficient_data():
    r = run("arrive_by", [cand("07:00", 30)], at(9))
    assert r.status == "insufficient_data"


def test_slots_include_target_and_handle_tight_deadline():
    slots = departure_slots("depart_around", at(7, 30), at(5), 15, 120)
    assert len(slots) == 9 and at(7, 30) in slots
    clipped = departure_slots("depart_around", at(7, 30), at(7, 20), 15, 120)
    assert at(7, 30) in clipped
    tight = departure_slots("arrive_by", at(8, 20), at(8, 0), 15, 120)
    assert len(tight) < 2