from datetime import datetime

from app.engine.decision import build_candidate, recommend_for_deadline
from app.schemas import RouteOption
from app.timeutil import ACCRA_TZ

DEADLINE = datetime(2026, 10, 25, 9, 0, tzinfo=ACCRA_TZ)


def make_candidates(table: dict[str, int]):
    out = []
    for leave, minutes in table.items():
        h, m = (int(x) for x in leave.split(":"))
        when = datetime(2026, 10, 25, h, m, tzinfo=ACCRA_TZ)
        out.append(build_candidate(when, [RouteOption(duration_seconds=minutes * 60)]))
    return out


PAPER_TABLE = {
    "7:00": 30, "7:15": 35, "7:30": 40, "7:45": 48,
    "8:00": 55, "8:15": 62, "8:30": 50, "8:45": 38,
}


def test_deadline_recommends_latest_within_five_minutes_of_fastest():
    rec = recommend_for_deadline(make_candidates(PAPER_TABLE), DEADLINE)
    assert rec.departure_time.strftime("%H:%M") == "07:15"


def test_deadline_drops_slot_that_is_too_slow():
    table = {**PAPER_TABLE, "7:15": 38}
    rec = recommend_for_deadline(make_candidates(table), DEADLINE)
    assert rec.departure_time.strftime("%H:%M") == "07:00"


def test_deadline_returns_none_when_nothing_is_feasible():
    early = datetime(2026, 10, 25, 7, 35, tzinfo=ACCRA_TZ)
    assert recommend_for_deadline(make_candidates(PAPER_TABLE), early) is None