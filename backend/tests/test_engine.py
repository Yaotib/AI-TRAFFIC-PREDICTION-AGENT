from datetime import datetime

from app.engine.decision import (
    build_candidate,
    build_warnings,
    decide_deadline,
    decide_preferred,
    preferred_slots,
    recommend_for_deadline,
    recommend_for_preferred,
)
from app.schemas import DataSource, DecisionKind, RouteOption, WarningCode
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






PREFERRED = datetime(2026, 10, 25, 8, 0, tzinfo=ACCRA_TZ)


def test_preferred_slots_cover_hour_either_side_and_skip_past():
    early = datetime(2026, 10, 25, 6, 0, tzinfo=ACCRA_TZ)
    assert len(preferred_slots(PREFERRED, early)) == 9
    late = datetime(2026, 10, 25, 7, 50, tzinfo=ACCRA_TZ)
    times = [t.strftime("%H:%M") for t in preferred_slots(PREFERRED, late)]
    assert times == ["08:00", "08:15", "08:30", "08:45", "09:00"]


def test_preferred_keeps_plan_when_saving_is_small():
    table = {"7:45": 47, "8:00": 50, "8:15": 46}
    choice = recommend_for_preferred(make_candidates(table), PREFERRED)
    assert choice.minutes_saved == 4
    assert choice.shift is False


def test_preferred_shifts_when_saving_is_meaningful():
    table = {"7:30": 44, "7:45": 46, "8:00": 50, "8:15": 41}
    choice = recommend_for_preferred(make_candidates(table), PREFERRED)
    assert choice.best.departure_time.strftime("%H:%M") == "08:15"
    assert choice.minutes_saved == 9
    assert choice.shift is True


def test_preferred_saving_of_exactly_five_counts():
    table = {"8:00": 50, "8:15": 45}
    choice = recommend_for_preferred(make_candidates(table), PREFERRED)
    assert choice.minutes_saved == 5
    assert choice.shift is True




def test_warns_when_times_barely_vary():
    cands = make_candidates({"7:00": 30, "7:15": 31, "7:30": 32})
    codes = [w.code for w in build_warnings(cands, 3, 0, False)]
    assert codes == [WarningCode.LOW_VARIATION]


def test_no_variation_warning_at_exactly_three_minutes():
    cands = make_candidates({"7:00": 30, "7:15": 33})
    assert build_warnings(cands, 2, 0, False) == []


def test_warns_on_failed_slots_and_simulated_data():
    cands = make_candidates({"7:00": 30, "7:15": 45})
    codes = [w.code for w in build_warnings(cands, 4, 2, True)]
    assert codes == [WarningCode.SLOTS_FAILED, WarningCode.SIMULATED_DATA]


def test_clean_data_has_no_warnings():
    cands = make_candidates({"7:00": 30, "7:15": 45})
    assert build_warnings(cands, 2, 0, False) == []


def test_decide_deadline_recommends_and_reports_spare_time():
    result = decide_deadline(make_candidates(PAPER_TABLE), DEADLINE, 8, False)
    assert result.kind == DecisionKind.RECOMMEND_DEPARTURE
    assert result.recommended.departure_time.strftime("%H:%M") == "07:15"
    assert result.spare_minutes == 70
    assert result.data_source == DataSource.PROVIDER


def test_decide_deadline_no_feasible_time():
    early = datetime(2026, 10, 25, 7, 35, tzinfo=ACCRA_TZ)
    result = decide_deadline(make_candidates(PAPER_TABLE), early, 8, False)
    assert result.kind == DecisionKind.NO_FEASIBLE_TIME
    assert result.recommended is None


def test_decide_deadline_too_few_slots():
    cands = make_candidates({"7:00": 30, "7:15": 35})
    result = decide_deadline(cands, DEADLINE, 8, False)
    assert result.kind == DecisionKind.INSUFFICIENT_DATA


def test_decide_flags_simulated_data():
    result = decide_deadline(make_candidates(PAPER_TABLE), DEADLINE, 8, True)
    assert result.is_simulated is True
    assert WarningCode.SIMULATED_DATA in [w.code for w in result.warnings]


def test_decide_counts_failed_slots():
    result = decide_deadline(make_candidates(PAPER_TABLE), DEADLINE, 10, False)
    assert result.slots_failed == 2
    assert WarningCode.SLOTS_FAILED in [w.code for w in result.warnings]


def test_decide_preferred_keeps_plan():
    table = {"7:45": 47, "8:00": 50, "8:15": 46}
    result = decide_preferred(make_candidates(table), PREFERRED, 3, False)
    assert result.kind == DecisionKind.KEEP_PLAN
    assert result.recommended.departure_time.strftime("%H:%M") == "08:00"


def test_decide_preferred_shifts():
    table = {"7:30": 44, "7:45": 46, "8:00": 50, "8:15": 41}
    result = decide_preferred(make_candidates(table), PREFERRED, 4, False)
    assert result.kind == DecisionKind.SHIFT_DEPARTURE
    assert result.minutes_saved == 9


def test_decide_preferred_without_own_slot_is_insufficient():
    table = {"7:30": 44, "7:45": 46, "8:15": 41}
    result = decide_preferred(make_candidates(table), PREFERRED, 4, False)
    assert result.kind == DecisionKind.INSUFFICIENT_DATA