from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.providers.routing import RoutingError
from app.schemas import Place, RouteOption
from app.services.planner import PlanError, plan_between
from app.timeutil import now_local

LEGON = Place(id="a", name="Legon", lat=5.65, lng=-0.18, source="demo_fixture")
OSU = Place(id="b", name="Osu", lat=5.55, lng=-0.18, source="demo_fixture")


def local_str(delta: timedelta) -> str:
    return (now_local() + delta).strftime("%Y-%m-%dT%H:%M")


@pytest.fixture(autouse=True)
def stub_io(monkeypatch):
    """No network, no database: fake the sweep, geocoding, context and saving."""

    async def fake_sweep(origin, dest, departures):
        return {
            d: [RouteOption(duration_s=(10 + 6 * (i % 2)) * 60, distance_m=12000,
                            description="OSRM route 1")]
            for i, d in enumerate(departures)
        }

    async def fake_geocode(text):
        return [Place(id=text, name=text, lat=5.6, lng=-0.18, source="demo_fixture")]

    async def fake_context(lat, lng, when):
        return None

    monkeypatch.setattr("app.services.planner.sweep", fake_sweep)
    monkeypatch.setattr("app.services.planner.geocode", fake_geocode)
    monkeypatch.setattr("app.services.planner.get_context", fake_context)
    monkeypatch.setattr("app.services.planner.record_prediction", lambda **kw: 1)


async def test_arrive_by_returns_a_recommendation():
    r = await plan_between(LEGON, OSU, "arrive_by", now_local() + timedelta(hours=3))
    assert r.status == "recommended"
    assert len(r.candidates) >= 2
    assert r.labels.simulated is True


async def test_depart_around_returns_a_decision():
    r = await plan_between(LEGON, OSU, "depart_around", now_local() + timedelta(hours=3))
    assert r.status in {"recommended", "keep_desired_time"}


async def test_past_deadline_is_rejected():
    with pytest.raises(PlanError):
        await plan_between(LEGON, OSU, "arrive_by", now_local() - timedelta(minutes=20))


async def test_past_preferred_time_is_rejected():
    with pytest.raises(PlanError):
        await plan_between(LEGON, OSU, "depart_around", now_local() - timedelta(minutes=20))


async def test_preferred_time_too_close_is_rejected():
    with pytest.raises(PlanError):
        await plan_between(LEGON, OSU, "depart_around", now_local() + timedelta(minutes=5))


async def test_no_routes_gives_plan_error(monkeypatch):
    async def empty(origin, dest, departures):
        return {d: [] for d in departures}

    monkeypatch.setattr("app.services.planner.sweep", empty)
    with pytest.raises(PlanError):
        await plan_between(LEGON, OSU, "arrive_by", now_local() + timedelta(hours=3))


async def test_routing_failure_propagates_for_the_endpoint_to_map(monkeypatch):
    async def boom(origin, dest, departures):
        raise RoutingError("provider down")

    monkeypatch.setattr("app.services.planner.sweep", boom)
    with pytest.raises(RoutingError):
        await plan_between(LEGON, OSU, "arrive_by", now_local() + timedelta(hours=3))


def test_api_plan_returns_complete_result():
    client = TestClient(app)
    res = client.post("/api/plan", json={
        "origin": "Legon", "destination": "Osu",
        "mode": "arrive_by", "time_local": local_str(timedelta(hours=3)),
    })
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "recommended"
    assert body["labels"]["simulated"] is True


def test_api_plan_past_time_is_422():
    client = TestClient(app)
    res = client.post("/api/plan", json={
        "origin": "Legon", "destination": "Osu",
        "mode": "arrive_by", "time_local": local_str(timedelta(hours=-2)),
    })
    assert res.status_code == 422


def test_api_plan_routing_failure_is_502(monkeypatch):
    async def boom(origin, dest, departures):
        raise RoutingError("provider down")

    monkeypatch.setattr("app.services.planner.sweep", boom)
    client = TestClient(app)
    res = client.post("/api/plan", json={
        "origin": "Legon", "destination": "Osu",
        "mode": "arrive_by", "time_local": local_str(timedelta(hours=3)),
    })
    assert res.status_code == 502