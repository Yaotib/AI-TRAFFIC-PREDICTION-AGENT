# backend/app/agent/loop.py
import json
import logging

import openai

from ..config import get_settings
from ..engine.explain import template_explanation
from ..schemas import AskResponse, ChatMessage
from ..timeutil import now_local
from .grounding import is_grounded
from .llm import LLMUnavailable, get_client
from .prompts import build_system_prompt
from .tools import TOOLS, ToolContext, run_tool

log = logging.getLogger("agent")


def _is_tool_format_error(e: openai.BadRequestError) -> bool:
    """Groq returns 400 'tool_use_failed' when the model writes a malformed tool call."""
    return getattr(e, "code", None) == "tool_use_failed" or "tool_use_failed" in str(e)


def _notice_for(e: Exception) -> str:
    if isinstance(e, openai.AuthenticationError):
        return "The AI service rejected the API key."
    if isinstance(e, openai.RateLimitError):
        return "The AI service rate limit was reached. Try again in a minute."
    if isinstance(e, openai.APITimeoutError):
        return "The AI service timed out."
    if isinstance(e, openai.BadRequestError):
        return "The AI model could not format a tool call. Please try again or use the form."
    return "The AI service is unavailable right now."


async def run_agent(messages: list[ChatMessage], client=None) -> AskResponse:
    s = get_settings()
    ctx = ToolContext()
    sources = [m.content for m in messages if m.role == "user"]
    convo: list[dict] = [{"role": "system", "content": build_system_prompt(now_local())}]
    convo += [{"role": m.role, "content": m.content} for m in messages]
    notice: str | None = None
    final_text = ""
    format_retries = 1

    try:
        client = client or get_client()
        for _ in range(s.llm_max_steps):
            try:
                resp = await client.chat.completions.create(
                    model=s.llm_model,
                    messages=convo,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.2,
                    max_completion_tokens=500,
                )
            except openai.BadRequestError as e:
                if _is_tool_format_error(e) and format_retries > 0:
                    format_retries -= 1
                    log.warning("tool_use_failed: retrying once")
                    continue
                raise
            msg = resp.choices[0].message
            calls = msg.tool_calls or []
            if not calls:
                final_text = (msg.content or "").strip()
                break
            convo.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": c.id,
                            "type": "function",
                            "function": {"name": c.function.name, "arguments": c.function.arguments},
                        }
                        for c in calls
                    ],
                }
            )
            for call in calls:
                payload = await run_tool(call.function.name, call.function.arguments, ctx)
                text = json.dumps(payload, ensure_ascii=False)
                sources.append(text)
                convo.append({"role": "tool", "tool_call_id": call.id, "content": text})
                log.info("tool=%s ok=%s", call.function.name, "error" not in payload)
        else:
            notice = "The assistant took too many steps and was stopped."
    except LLMUnavailable as e:
        notice = str(e)
    except openai.OpenAIError as e:
        log.warning("llm_error type=%s", type(e).__name__)
        notice = _notice_for(e)

    source = "llm"
    if ctx.last_result is not None:
        ok = True
        if final_text:
            ok, bad = is_grounded(final_text, sources)
            if not ok:
                log.warning("ungrounded numbers=%s", bad)
        if not final_text or not ok:
            final_text = template_explanation(ctx.last_result)
            source = "template"
    elif not final_text:
        final_text = (
            f"{notice} You can still get a recommendation with the form."
            if notice
            else "I could not complete that request. Please give me an origin, a destination, "
            "and either an arrival deadline or a preferred departure time."
        )
        source = "none"

    return AskResponse(
        reply=final_text,
        explanation_source=source,
        notice=notice,
        result=ctx.last_result,
        trace=ctx.trace,
    )