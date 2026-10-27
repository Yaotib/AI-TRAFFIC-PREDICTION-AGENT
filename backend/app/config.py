# backend/app/config.py
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_maps_api_key: str = ""
    mapbox_access_token: str = ""
    mapbox_enabled: bool = True
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_timeout_s: float = 30.0
    llm_max_steps: int = 5

    demo_mode: bool = False

    http_timeout_s: float = 10.0
    max_route_calls: int = 14
    sweep_step_min: int = 15
    sweep_window_min: int = 120
    buffer_min: int = 10
    gain_min: int = 5

    cors_origins: str = "http://localhost:3000"
    timezone: str = "Africa/Accra"


@lru_cache
def get_settings() -> Settings:
    return Settings()