"""FastAPI entry point. Phase 1 has health only; the real endpoints arrive in Phase 4."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .schemas import HealthResponse


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AI Traffic & Routing Agent", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        s = get_settings()
        return HealthResponse(
            demo_mode=s.demo_mode,
            google_configured=s.google_configured,
            ai_key_configured=s.ai_key_configured,
            zetaris_enabled=s.zetaris_enabled,
        )

    return app


app = create_app()
