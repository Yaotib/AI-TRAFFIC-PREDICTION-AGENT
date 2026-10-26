from datetime import datetime

import pytest

from app.providers import demo
from app.schemas import Place
from app.timeutil import ACCRA_TZ

# 2026-10-26 is a Monday; 2026-10-24 is a Saturday.
MON_MORNING_PEAK = datetime(2026, 10, 26, 7, 45, tzinfo=ACCRA_TZ)
MON_EVENING_PEAK = datetime(2026, 10, 26, 17, 30, tzinfo=ACCRA_TZ)
MON_NIGHT = datetime(2026, 10, 26, 3, 0, tzinfo=ACCRA_TZ)
SAT_MORNING = datetime(2026, 10, 24, 7, 45, tzinfo=ACCRA_TZ)


def _pair():
    madina = demo.demo_geocode("Madina")[0]
    airport = demo.demo_geocode("airport")[0]
    return madina, airport


# ------------------------------------------------------------ places


def test_geocode_finds_a_known_place_and_labels_it_simulated():
    places = demo.demo_geocode("Madina")
    assert places and places[0].name == "Madina"
    assert all(p.simulated for p in places)


def test_geocode_understands_aliases():
    assert demo.demo_geocode("airport")[0].name == "Kotoka International Airport"
    assert demo.demo_geocode("Legon")[0].name == "University of Ghana, Legon"


def test_geocode_returns_at_most_three_and_empty_when_nothing_matches():
    assert len(demo.demo_geocode("accra")) <= 3
    assert demo.demo_geocode("zzzz nowhere") == []


def test_demo_places_have_valid_coordinates_in_accra_area():
    for name in ("Madina", "Osu", "Tema", "Kasoa"):
        p = demo.demo_geocode(name)[0]
        assert 5.0 < p.lat < 6.0 and -0.6 < p.lng < 0.1


# ------------------------------------------------------------ rush-hour pattern


def test_traffic_peaks_in_the_morning_and_evening_and_is_clear_at_night():
    night = demo.congestion_factor(MON_NIGHT)
    assert night < 1.05
    assert demo.congestion_factor(MON_MORNING_PEAK) > 1.6
    assert demo.congestion_factor(MON_EVENING_PEAK) > 1.7
    assert demo.congestion_factor(datetime(2026, 10, 26, 12, 30, tzinfo=ACCRA_TZ)) < 1.3


def test_weekends_are_lighter_than_weekdays():
    assert demo.congestion_factor(SAT_MORNING) < demo.congestion_factor(
        MON_MORNING_PEAK
    )


def test_demo_routes_are_deterministic():
    a, b = _pair()
    assert demo.demo_routes(a, b, MON_MORNING_PEAK) == demo.demo_routes(
        a, b, MON_MORNING_PEAK
    )


# ------------------------------------------------------------ routes


def test_demo_routes_return_valid_labelled_options():
    a, b = _pair()
    routes = demo.demo_routes(a, b, MON_MORNING_PEAK)
    assert len(routes) == 2
    for r in routes:
        assert r.duration_seconds >= 300
        assert r.summary and r.summary.startswith("Simulated")


def test_rush_hour_trip_is_slower_than_a_night_trip():
    a, b = _pair()
    peak = min(r.duration_seconds for r in demo.demo_routes(a, b, MON_MORNING_PEAK))
    night = min(r.duration_seconds for r in demo.demo_routes(a, b, MON_NIGHT))
    assert peak > night * 1.3


def test_alternative_route_wins_at_the_peak_and_loses_at_night():
    a, b = _pair()
    peak_main, peak_alt = demo.demo_routes(a, b, MON_MORNING_PEAK)
    night_main, night_alt = demo.demo_routes(a, b, MON_NIGHT)
    assert peak_alt.duration_seconds < peak_main.duration_seconds
    assert night_alt.duration_seconds > night_main.duration_seconds


def test_very_short_trips_have_a_minimum_duration():
    p = Place(name="A", lat=5.6, lng=-0.17, simulated=True)
    q = Place(name="B", lat=5.6001, lng=-0.17, simulated=True)
    assert min(r.duration_seconds for r in demo.demo_routes(p, q, MON_NIGHT)) >= 300


@pytest.mark.parametrize("hour", range(24))
def test_every_hour_gives_a_sensible_factor(hour):
    f = demo.congestion_factor(datetime(2026, 10, 26, hour, 0, tzinfo=ACCRA_TZ))
    assert 1.0 <= f < 2.2
