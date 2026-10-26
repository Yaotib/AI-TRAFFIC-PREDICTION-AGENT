from pathlib import Path

from app.config import Settings


def _env_names() -> set[str]:
    names = set()
    for name, field in Settings.model_fields.items():
        alias = field.validation_alias
        names.add(alias if isinstance(alias, str) else name.upper())
    return names


def test_defaults_match_guide():
    s = Settings(_env_file=None)
    assert s.sweep_concurrency == 4
    assert s.rate_limit_form_per_minute == 10
    assert s.rate_limit_agent_per_minute == 6
    assert (s.deadline_margin_minutes, s.within_fastest_minutes) == (10, 5)
    assert (s.shift_min_saving_minutes, s.low_variation_minutes) == (5, 3)
    assert s.slot_step_minutes == 15
    assert s.deadline_lookback_minutes == 120
    assert s.deadline_stop_before_minutes == 15
    assert s.preferred_window_minutes == 60
    assert s.demo_mode is False and s.zetaris_enabled is False


def test_groq_defaults_come_from_the_spike_script():
    s = Settings(_env_file=None)
    assert s.groq_base_url == "https://api.groq.com/openai/v1"
    assert s.llm_model == "llama-3.3-70b-versatile"
    assert s.llm_timeout_s == 30.0
    assert s.llm_max_steps >= 1


def test_empty_env_values_use_defaults(monkeypatch):
    monkeypatch.setenv("SWEEP_CONCURRENCY", "")
    monkeypatch.setenv("DEMO_MODE", "")
    s = Settings(_env_file=None)
    assert s.sweep_concurrency == 4
    assert s.demo_mode is False


def test_allowed_origins_parsing(monkeypatch):
    monkeypatch.setenv(
        "ALLOWED_ORIGINS", "http://localhost:3000, https://app.example.com ,"
    )
    s = Settings(_env_file=None)
    assert s.allowed_origins_list == [
        "http://localhost:3000",
        "https://app.example.com",
    ]


def test_groq_key_is_a_plain_string_for_llm_py_but_hidden_from_repr(monkeypatch):
    # llm.py passes settings.groq_api_key straight to the OpenAI client, which
    # needs the real string (a SecretStr would send 'Bearer **********').
    monkeypatch.setenv("GROQ_API_KEY", "gsk_secret123")
    s = Settings(_env_file=None)
    assert s.groq_api_key == "gsk_secret123"
    assert isinstance(s.groq_api_key, str)
    assert s.ai_key_configured is True
    assert "gsk_secret123" not in repr(s)


def test_missing_groq_key_is_falsy(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    s = Settings(_env_file=None)
    assert not s.groq_api_key  # llm.py checks `if not s.groq_api_key`
    assert s.ai_key_configured is False


def test_google_key_not_in_repr(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "abc123secret")
    s = Settings(_env_file=None)
    assert "abc123secret" not in repr(s)


def test_env_example_lists_every_setting_with_no_values():
    example = Path(__file__).resolve().parent.parent / ".env.example"
    keys = {}
    for line in example.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            k, _, v = line.partition("=")
            keys[k] = v
    assert all(v == "" for v in keys.values())
    assert _env_names() <= set(keys), f"missing: {_env_names() - set(keys)}"


def test_real_env_is_gitignored():
    gi = (
        (Path(__file__).resolve().parent.parent / ".gitignore").read_text().splitlines()
    )
    assert ".env" in gi
