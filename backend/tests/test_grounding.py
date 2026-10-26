# backend/tests/test_grounding.py
from app.agent.grounding import is_grounded, numbers_in


def test_time_normalisation():
    assert numbers_in("leave at 7:45") == numbers_in("leave at 07:45")


def test_accepts_numbers_from_sources():
    ok, bad = is_grounded(
        "Leave at 07:00, the trip takes 32 minutes.",
        ['{"departure_local": "07:00", "duration_min": 32}'],
    )
    assert ok and bad == []


def test_flags_invented_number():
    ok, bad = is_grounded("It will take 45 minutes.", ['{"duration_min": 32}'])
    assert not ok and bad == ["45"]