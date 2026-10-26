"""Shared data formats. All datetimes are timezone-aware, in Accra time."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.timeutil import as_accra

MAX_TEXT_LEN = 200


# ---------------------------------------------------------------- places


class Place(BaseModel):
    """A geocoded place. The AI refers to places by place_id, never coordinates."""

    place_id: str
    name: str
    address: str | None = None
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    simulated: bool = False


# ---------------------------------------------------------------- routes


class RouteOption(BaseModel):
    """One route returned by the provider for a single departure time."""

    summary: str | None = None
    distance_meters: int | None = Field(default=None, ge=0)
    duration_seconds: int = Field(gt=0)  # parsed from text like "1500s"
    static_duration_seconds: int | None = Field(default=None, gt=0)


class CandidateDeparture(BaseModel):
    """One departure time with its fastest route, in whole minutes."""

    departure_time: datetime
    duration_minutes: int = Field(gt=0)
    arrival_time: datetime
    distance_km: float | None = Field(default=None, ge=0)
    route_summary: str | None = None

    @field_validator("departure_time", "arrival_time")
    @classmethod
    def _to_accra(cls, v: datetime) -> datetime:
        return as_accra(v)

    @model_validator(mode="after")
    def _numbers_add_up(self) -> "CandidateDeparture":
        expected = self.departure_time + timedelta(minutes=self.duration_minutes)
        if self.arrival_time != expected:
            raise ValueError(
                "arrival_time must equal departure_time + duration_minutes"
            )
        return self


# ---------------------------------------------------------------- decision


class DecisionMode(str, Enum):
    DEADLINE = "deadline"  # user must arrive by a time
    PREFERRED = "preferred"  # user wants to leave at a time


class DecisionKind(str, Enum):
    RECOMMEND_DEPARTURE = "recommend_departure"  # deadline mode, feasible
    NO_FEASIBLE_TIME = "no_feasible_time"  # deadline mode, nothing works
    KEEP_PLAN = "keep_plan"  # preferred mode, no meaningful gain
    SHIFT_DEPARTURE = "shift_departure"  # preferred mode, meaningful gain
    INSUFFICIENT_DATA = "insufficient_data"  # too few usable slots


class WarningCode(str, Enum):
    LOW_VARIATION = "low_variation"
    SLOTS_FAILED = "slots_failed"
    SIMULATED_DATA = "simulated_data"


class DecisionWarning(BaseModel):
    code: WarningCode
    message: str


class DataSource(str, Enum):
    PROVIDER = "provider"  # real Google estimates
    SIMULATED = "simulated"  # demo mode


class DecisionResult(BaseModel):
    """Output of the deterministic engine. The only place numbers are computed."""

    mode: DecisionMode
    kind: DecisionKind
    data_source: DataSource
    candidates: list[CandidateDeparture]
    recommended: CandidateDeparture | None = None
    baseline: CandidateDeparture | None = None  # the user's own plan (preferred mode)
    deadline: datetime | None = None
    spare_minutes: int | None = None  # deadline mode: arrival vs deadline
    minutes_saved: int | None = None  # preferred mode: vs the baseline
    slots_requested: int = 0
    slots_failed: int = 0
    warnings: list[DecisionWarning] = Field(default_factory=list)
    rule_summary: str = ""  # decision rule in plain English

    @property
    def is_simulated(self) -> bool:
        return self.data_source == DataSource.SIMULATED


# ---------------------------------------------------------------- requests


def _clean_text(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("must not be empty")
    return v


class PlanRequest(BaseModel):
    """Structured (form) endpoint input. No AI involved."""

    origin: str = Field(max_length=MAX_TEXT_LEN)
    destination: str = Field(max_length=MAX_TEXT_LEN)
    mode: Literal["arrive_by", "leave_at"]
    time: datetime  # naive values are read as Accra time

    _clean_origin = field_validator("origin")(_clean_text)
    _clean_destination = field_validator("destination")(_clean_text)

    @field_validator("time")
    @classmethod
    def _time_to_accra(cls, v: datetime) -> datetime:
        return as_accra(v)


class PlanResponse(BaseModel):
    request_id: str
    origin: Place
    destination: Place
    decision: DecisionResult
    explanation: str
    explanation_source: Literal["fallback"] = "fallback"


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class AgentRequest(BaseModel):
    """Natural-language endpoint input."""

    message: str = Field(max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)

    _clean_message = field_validator("message")(_clean_text)


class ToolTrace(BaseModel):
    """One tool call, shown in 'How the agent decided'."""

    name: str
    inputs: dict
    success: bool
    summary: str


class AgentResponse(BaseModel):
    request_id: str
    reply: str
    explanation_source: Literal["ai", "fallback"]  # who wrote the explanation
    needs_clarification: bool = False
    decision: DecisionResult | None = None
    origin: Place | None = None
    destination: Place | None = None
    trace: list[ToolTrace] = Field(default_factory=list)
    notice: str | None = None


# ---------------------------------------------------------------- errors / health


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    retryable: bool = False


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    demo_mode: bool
    google_configured: bool
    ai_key_configured: bool
    zetaris_enabled: bool
