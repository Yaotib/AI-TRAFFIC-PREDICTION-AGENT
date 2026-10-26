"""Application settings.

All configuration comes from environment variables (or a local .env file).
Empty values in .env are treated as "not set", so the template file
.env.example can list every variable with no value.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    # --- Keys (never logged, never returned by any endpoint) ---
    google_maps_api_key: SecretStr | None = None
    nvidia_api_key: SecretStr | None = None

    # --- Model ---
    llm_model: str = ""

    # --- Switches ---
    demo_mode: bool = False
    zetaris_enabled: bool = False

    # --- Limits ---
    sweep_concurrency: int = 4  # guide: at most four at a time
    max_route_calls_per_request: int = 12  # guide wants a cap but gives no number
    min_lead_minutes: int = 5  # "too close" is undefined in the guide
    rate_limit_form_per_minute: int = 10  # guide: about 10 per minute
    rate_limit_agent_per_minute: int = 6  # guide: 6 per minute
    request_timeout_seconds: float = 10.0

    # --- Decision thresholds, in minutes (Phase 3) ---
    slot_step_minutes: int = 15
    deadline_lookback_minutes: int = 120
    deadline_stop_before_minutes: int = 15
    preferred_window_minutes: int = 60
    deadline_margin_minutes: int = 10
    within_fastest_minutes: int = 5
    shift_min_saving_minutes: int = 5
    low_variation_minutes: int = 3

    # --- Web ---
    allowed_origins: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def google_configured(self) -> bool:
        return self.google_maps_api_key is not None

    @property
    def ai_key_configured(self) -> bool:
        return self.nvidia_api_key is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
