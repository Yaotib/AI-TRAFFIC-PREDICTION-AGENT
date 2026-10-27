# backend/app/schemas.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Place(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    source: Literal[
    "google_geocoding",
    "openstreetmap_nominatim",
    "demo_fixture",
]


class RouteOption(BaseModel):
    duration_s: int
    static_duration_s: int | None = None
    distance_m: int
    description: str | None = None


class Candidate(BaseModel):
    departure: datetime
    arrival: datetime
    duration_min: int
    static_duration_min: int | None = None
    distance_km: float
    route_description: str | None = None
    alternatives_count: int = 1


class CandidateView(BaseModel):
    departure_local: str
    arrival_local: str
    duration_min: int
    static_duration_min: int | None
    traffic_delay_min: int | None
    distance_km: float
    route_description: str | None
    alternatives_count: int


class DataLabels(BaseModel):
    source: str
    duration_type: str
    simulated: bool
    note: str


class DecisionResult(BaseModel):
    status: Literal["recommended", "keep_desired_time", "no_feasible_time", "insufficient_data"]
    mode: Literal["arrive_by", "depart_around"]
    rule_applied: str
    origin_name: str
    destination_name: str
    date_local: str
    deadline_local: str | None
    desired_departure_local: str | None
    recommended: CandidateView | None
    baseline: CandidateView | None
    baseline_label: str | None
    time_saved_min: int | None
    deadline_margin_min: int | None
    spread_min: int
    buffer_min: int | None
    gain_min: int
    candidates: list[CandidateView]
    warnings: list[str]
    labels: DataLabels
    context: dict | None = None
    prediction_id: int | None = None


class PlanRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=120)
    destination: str = Field(min_length=2, max_length=120)
    mode: Literal["arrive_by", "depart_around"]
    time_local: str = Field(min_length=16, max_length=25)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class AskRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


class ToolTrace(BaseModel):
    tool: str
    arguments: dict
    ok: bool
    summary: str


class AskResponse(BaseModel):
    reply: str
    explanation_source: Literal["llm", "template", "none"]
    notice: str | None
    result: DecisionResult | None
    trace: list[ToolTrace]


class ActualTripRequest(BaseModel):
    """Request to record an observed journey duration."""

    prediction_id: int = Field(gt=0)
    actual_duration_min: int = Field(gt=0)
    observation_source: str = Field(min_length=1, max_length=100)


class ActualTripResponse(BaseModel):
    """Confirmation that an actual journey was recorded."""

    id: int
    prediction_id: int
    actual_duration_min: int
    observed_at: str
    observation_source: str


class EvaluationResponse(BaseModel):
    """Prediction accuracy metrics based on observed journeys."""

    matched_observations: int
    mae_minutes: float | None
    mean_signed_error_minutes: float | None
