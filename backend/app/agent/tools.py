# backend/app/agent/tools.py
import json
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from ..providers.geocoding import GeocodingError, geocode
from ..providers.routing import RoutingError
from ..schemas import DecisionResult, Place, ToolTrace
from ..services.planner import PlanError, plan_between
from ..timeutil import parse_local

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "geocode_place",
            "description": "Look up a place in Ghana by name. Returns candidate places with ids. Call once for the origin and once for the destination, together.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Place name, e.g. 'Madina'"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_departure_times",
            "description": "Compare several departure times for a journey and return the system's recommendation. Use place ids from geocode_place.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_id": {"type": "string"},
                    "destination_id": {"type": "string"},
                    "mode": {
                        "type": "string",
                        "enum": ["arrive_by", "depart_around"],
                        "description": "arrive_by: user has a deadline. depart_around: user has a preferred departure time.",
                    },
                    "time_local": {
                        "type": "string",
                        "description": "Accra local time, format YYYY-MM-DDTHH:MM",
                    },
                },
                "required": ["origin_id", "destination_id", "mode", "time_local"],
            },
        },
    },
]


class GeocodeArgs(BaseModel):
    query: str = Field(min_length=2, max_length=120)


class CompareArgs(BaseModel):
    origin_id: str
    destination_id: str
    mode: Literal["arrive_by", "depart_around"]
    time_local: str


@dataclass
class ToolContext:
    places: dict[str, Place] = field(default_factory=dict)
    last_result: DecisionResult | None = None
    trace: list[ToolTrace] = field(default_factory=list)
    _counter: int = 0

    def next_id(self) -> str:
        self._counter += 1
        return f"p{self._counter}"


def compact_for_llm(r: DecisionResult) -> dict:
    """A small, readable view of the result. Keeps the model's token use low."""
    rec = r.recommended
    return {
        "status": r.status,
        "mode": r.mode,
        "rule": r.rule_applied,
        "origin": r.origin_name,
        "destination": r.destination_name,
        "date": r.date_local,
        "deadline": r.deadline_local,
        "preferred_departure": r.desired_departure_local,
        "recommended_departure": rec.departure_local if rec else None,
        "recommended_arrival": rec.arrival_local if rec else None,
        "trip_minutes": rec.duration_min if rec else None,
        "minutes_saved": r.time_saved_min,
        "compared_with": r.baseline_label,
        "minutes_to_spare": r.deadline_margin_min,
        "safety_buffer_minutes": r.buffer_min,
        "meaningful_gain_minutes": r.gain_min,
        "options_checked": [f"{c.departure_local} -> {c.duration_min} min" for c in r.candidates],
        "warnings": r.warnings,
        "data": {
            "source": r.labels.source,
            "simulated": r.labels.simulated,
            "note": r.labels.note,
        },
        "context": r.context,
    }


async def _geocode(args: GeocodeArgs, ctx: ToolContext) -> tuple[dict, str]:
    places = await geocode(args.query)
    stored = []
    for p in places:
        p2 = p.model_copy(update={"id": ctx.next_id()})
        ctx.places[p2.id] = p2
        stored.append({"id": p2.id, "name": p2.name})  # coordinates never reach the LLM
    if not stored:
        return {"query": args.query, "candidates": [], "message": "No match found in Ghana."}, "no match"
    return {"query": args.query, "candidates": stored}, f"{len(stored)} candidate(s)"


async def _compare(args: CompareArgs, ctx: ToolContext) -> tuple[dict, str]:
    origin = ctx.places.get(args.origin_id)
    dest = ctx.places.get(args.destination_id)
    if not origin or not dest:
        return {"error": "Unknown place id. Call geocode_place first."}, "unknown place id"
    try:
        target = parse_local(args.time_local)
    except ValueError:
        return {"error": "time_local must look like 2026-10-26T08:30"}, "bad time format"
    result = await plan_between(origin, dest, args.mode, target)
    ctx.last_result = result
    summary = result.status
    if result.recommended:
        summary += f", leave at {result.recommended.departure_local}"
    return compact_for_llm(result), summary


HANDLERS = {
    "geocode_place": (GeocodeArgs, _geocode),
    "compare_departure_times": (CompareArgs, _compare),
}


async def run_tool(name: str, raw_args: str, ctx: ToolContext) -> dict:
    """Validate arguments, run the tool, record a trace entry. Never raises."""
    entry = HANDLERS.get(name)
    if entry is None:
        ctx.trace.append(ToolTrace(tool=name, arguments={}, ok=False, summary="unknown tool"))
        return {"error": f"Unknown tool {name}."}
    model, handler = entry
    args_dict: object = {}
    try:
        args_dict = json.loads(raw_args or "{}")
        args = model.model_validate(args_dict)
        payload, summary = await handler(args, ctx)
        ok = "error" not in payload
    except (json.JSONDecodeError, ValidationError):
        payload, summary, ok = {"error": "Invalid tool arguments."}, "invalid arguments", False
    except (PlanError, RoutingError, GeocodingError) as e:
        payload, summary, ok = {"error": str(e)}, "error", False
    ctx.trace.append(
        ToolTrace(
            tool=name,
            arguments=args_dict if isinstance(args_dict, dict) else {},
            ok=ok,
            summary=summary,
        )
    )
    return payload