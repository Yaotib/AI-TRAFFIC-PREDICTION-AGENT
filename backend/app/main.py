# backend/app/main.py
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .agent.loop import run_agent
from .config import get_settings
from .providers.geocoding import GeocodingError
from .providers.routing import RoutingError
from .schemas import AskRequest, AskResponse, DecisionResult, PlanRequest
from .services.planner import PlanError, plan_from_text

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