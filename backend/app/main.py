# backend/app/main.py
import logging
import sqlite3
import time
import uuid
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .agent.loop import run_agent
from .config import get_settings
from .providers.geocoding import GeocodingError
from .providers.routing import RoutingError
from .schemas import (
    ActualTripRequest,
    ActualTripResponse,
    AskRequest,
    AskResponse,
    DecisionResult,
    EvaluationResponse,
    PlanRequest,
)
from .services.planner import PlanError, plan_from_text
from .services.traffic_store import get_evaluation, record_actual_trip

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
# httpx logs full request URLs at INFO, which would put the Google key in the logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("api")

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="DepartWise API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    log.info("rid=%s %s %s -> %s %.0fms", rid, request.method, request.url.path, response.status_code, ms)
    return response


@app.get("/health")
def health():
    s = get_settings()
    return {
        "status": "ok",
        "demo_mode": s.demo_mode,
        "google_configured": bool(s.google_maps_api_key),
        "llm_configured": bool(s.groq_api_key),
        "llm_model": s.llm_model,
    }


@app.post("/api/plan", response_model=DecisionResult)
@limiter.limit("10/minute")
async def api_plan(request: Request, body: PlanRequest):
    try:
        return await plan_from_text(body.origin, body.destination, body.mode, body.time_local)
    except PlanError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except (RoutingError, GeocodingError) as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/api/agent/ask", response_model=AskResponse)
@limiter.limit("6/minute")
async def api_ask(request: Request, body: AskRequest):
    return await run_agent(body.messages)


@app.post(
    "/api/trips/actual",
    response_model=ActualTripResponse,
    status_code=201,
)
@limiter.limit("20/minute")
def api_record_actual_trip(
    request: Request,
    body: ActualTripRequest,
):
    """Record the observed duration of a previously predicted journey."""
    observation_source = body.observation_source.strip()

    if not observation_source:
        raise HTTPException(
            status_code=422,
            detail="Observation source cannot be empty.",
        )

    observed_at = datetime.now(UTC)

    try:
        trip_id = record_actual_trip(
            prediction_id=body.prediction_id,
            actual_duration_min=body.actual_duration_min,
            observation_source=observation_source,
            observed_at=observed_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except sqlite3.IntegrityError as exc:
        error_message = str(exc)

        if "UNIQUE constraint failed" in error_message:
            raise HTTPException(
                status_code=409,
                detail=(
                    "An actual journey has already been recorded "
                    "for this prediction."
                ),
            ) from exc

        if "FOREIGN KEY constraint failed" in error_message:
            raise HTTPException(
                status_code=404,
                detail="Prediction not found.",
            ) from exc

        log.exception("Database integrity error while recording actual trip.")
        raise HTTPException(
            status_code=500,
            detail="Could not record the actual journey.",
        ) from exc
    except sqlite3.Error as exc:
        log.exception("Database error while recording actual trip.")
        raise HTTPException(
            status_code=500,
            detail="Could not record the actual journey.",
        ) from exc
    except OSError as exc:
        log.exception("Storage error while recording actual trip.")
        raise HTTPException(
            status_code=500,
            detail="Could not access traffic history storage.",
        ) from exc

    return ActualTripResponse(
        id=trip_id,
        prediction_id=body.prediction_id,
        actual_duration_min=body.actual_duration_min,
        observed_at=observed_at.isoformat(),
        observation_source=observation_source,
    )


@app.get(
    "/api/evaluation",
    response_model=EvaluationResponse,
)
@limiter.limit("30/minute")
def api_evaluation(request: Request):
    """Return prediction accuracy metrics for observed journeys."""
    try:
        return get_evaluation()
    except (sqlite3.Error, OSError):
        log.exception("Could not evaluate traffic predictions.")
        raise HTTPException(
            status_code=500,
            detail="Could not evaluate traffic predictions.",
        ) from None
