from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert set(body) == {
        "status",
        "demo_mode",
        "google_configured",
        "ai_key_configured",
        "zetaris_enabled",
    }


def test_health_reports_configuration_without_leaking_keys(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "super-secret-google")
    monkeypatch.setenv("GROQ_API_KEY", "super-secret-groq")
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()
    try:
        r = client.get("/health")
        body = r.json()
        assert body["google_configured"] is True
        assert body["ai_key_configured"] is True
        assert body["demo_mode"] is True
        assert "super-secret" not in r.text
    finally:
        get_settings.cache_clear()
