"""Shared data formats.

Field names follow what the agent code (app/agent/loop.py, tools.py) already
reads. Datetimes are timezone-aware and in Accra time. The *_local strings
are computed from them, so the numbers always add up.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from .timeutil import as_accra, format_clock

MAX_TEXT_LEN = 200

# One vocabulary for both endpoints and the agent tool.
Mode = Literal["arrive_by", "depart_around"]


# ---------------------------------------------------------------- places


class Place(BaseModel):
    """A geocoded place. The AI works with `id`, never with coordinates.

    `id` is assigned per conversation turn (p1, p2, ...) by the agent.
    """

    id: str = ""
    name: str
    address: str | None = None
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    provider_place_id: str | None = None
    simulated: bool = False


# ---------------------------------------------------------------- routes


class RouteOption(BaseModel):
    """One route returned by the provider for a single departure time."""

    summary: str | None = None
    distance_meters: int | None = Field(default=None, ge=0)
    # Parsed from provider text such as "1500s".
    duration_seconds: int = Field(gt=0)
    # Traffic-unaware duration, when the provider returns it.
    static_duration_seconds: int | None = Field(default=None, gt=0)


class CandidateDeparture(BaseModel):
    """One departure time with its fastest route, in whole minutes."""

    departure_time: datetime
    duration_min: int = Field(gt=0)
    arrival_time: datetime
    distance_km: float | None = Field(default=None, ge=0)
    route_summary: str | None = None

    @field_validator("departure_time", "arrival_time")
    @classmethod
    def _to_accra(cls, v: datetime) -> datetime:
        return as_accra(v)

    @model_validator(mode="after")
    def _numbers_add_up(self) -> "CandidateDeparture":
        expected = self.departure_time + timedelta(minutes=self.duration_min)
        if self.arrival_time != expected:
            raise ValueError("arrival_time must equal departure_time + duration_min")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def departure_local(self) -> str:
        return format_clock(self.departure_time)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def arrival_local(self) -> str:
        return format_clock(self.arrival_time)


# ---------------------------------------------------------------- decision


class DecisionStatus(str, Enum):
    RECOMMEND_DEPARTURE = "recommend_departure"  # arrive_by, feasible
    NO_FEASIBLE_TIME = "no_feasible_time"  # arrive_by, nothing works
    KEEP_PLAN = "keep_plan"  # depart_around, no meaningful gain
    SHIFT_DEPARTURE = "shift_departure"  # depart_around, meaningful gain
    INSUFFICIENT_DATA = "insufficient_data"  # too few usable slots


class WarningCode(str, Enum):
    LOW_VARIATION = "low_variation"  # estimates barely vary across the day
    SLOTS_FAILED = "slots_failed"  # some time slots could not be fetched
    SIMULATED_DATA = "simulated_data"  # demo mode


class DataLabels(BaseModel):
    """Where the numbers came from. Simulated data must always say so."""

    source: Literal["google", "simulated"]
    simulated: bool
    note: str = ""

    @model_validator(mode="after")
    def _consistent(self) -> "DataLabels":
        if self.simulated != (self.source == "simulated"):
            raise ValueError(
                "simulated must be True exactly when source is 'simulated'"
            )
        return self


class DecisionResult(BaseModel):
    """Output of the deterministic engine. The only place numbers are computed."""

    status: DecisionStatus
    mode: Mode
    # The decision rule in plain English ("How the agent decided").
    rule_applied: str
    origin_name: str
    destination_name: str
    date_local: str  # YYYY-MM-DD, Accra time
    deadline_local: str | None = None  # HH:MM
    desired_departure_local: str | None = None  # HH:MM
    recommended: CandidateDeparture | None = None
    # The user's own plan, for comparison (depart_around mode).
    baseline: CandidateDeparture | None = None
    baseline_label: str | None = None
    time_saved_min: int | None = None
    # arrive_by mode: minutes between arrival and the deadline.
    deadline_margin_min: int | None = None
    buffer_min: int
    gain_min: int
    candidates: list[CandidateDeparture]
    slots_requested: int = 0
    slots_failed: int = 0
    warnings: list[str] = Field(default_factory=list)
    warning_codes: list[WarningCode] = Field(default_factory=list)
    labels: DataLabels
    # Optional extra information (e.g. weather). Never traffic data.
    context: dict[str, Any] | None = None

    @property
    def is_simulated(self) -> bool:
        return self.labels.simulated


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
    mode: Mode
    # Naive values are read as Accra local time.
    time: datetime

    _clean_origin = field_validator("origin")(_clean_text)
    _clean_destination = field_validator("destination")(_clean_text)

    @field_validator("time")
    @classmethod
    def _time_to_accra(cls, v: datetime) -> datetime:
        return as_accra(v)


class PlanResponse(BaseModel):
    request_id: str
    result: DecisionResult
    explanation: str
    # The form endpoint never uses the AI, so code writes the explanation.
    explanation_source: Literal["template"] = "template"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class AskRequest(BaseModel):
    """Natural-language endpoint input."""

    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


class ToolTrace(BaseModel):
    """One tool call, shown in 'How the agent decided'."""

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    ok: bool
    summary: str


class AskResponse(BaseModel):
    request_id: str | None = None
    reply: str
    # "llm": the AI wrote it. "template": code wrote it. "none": nothing to explain.
    explanation_source: Literal["llm", "template", "none"]
    notice: str | None = None
    result: DecisionResult | None = None
    trace: list[ToolTrace] = Field(default_factory=list)


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
