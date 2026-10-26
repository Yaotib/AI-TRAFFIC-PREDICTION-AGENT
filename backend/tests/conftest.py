# backend/tests/conftest.py
import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _no_network_context(monkeypatch):
    """Keep planner tests offline: replace the weather/holiday lookup with a stub."""

    async def fake_context(lat, lng, when):
        return {
            "weather": {"available": False, "reason": "test"},
            "calendar": {"available": False, "reason": "test"},
            "note": "Context only. This is not traffic data.",
        }

    monkeypatch.setattr("app.services.planner.get_context", fake_context)