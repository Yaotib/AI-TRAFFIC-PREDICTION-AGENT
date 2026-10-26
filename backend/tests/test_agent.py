# backend/tests/test_agent.py
import json
from datetime import timedelta
from types import SimpleNamespace as NS

import httpx
import openai
from app.agent.loop import run_agent
from app.config import get_settings
from app.schemas import ChatMessage
from app.timeutil import now_local


def tc(call_id, name, args):
    return NS(id=call_id, function=NS(name=name, arguments=json.dumps(args)))


def reply(content=None, calls=None):
    return NS(choices=[NS(message=NS(content=content, tool_calls=calls))])


class FakeLLM:
    """Scripted stand-in for the AI. Items that are exceptions are raised."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.chat = NS(completions=NS(create=self._create))

    async def _create(self, **kwargs):
        item = self.replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def tomorrow_at(hour: int) -> str:
    d = (now_local() + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)
    return d.strftime("%Y-%m-%dT%H:%M")


def use_demo(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()


def user(text: str) -> list[ChatMessage]:
    return [ChatMessage(role="user", content=text)]


async def test_invented_numbers_fall_back_to_template(monkeypatch):
    use_demo(monkeypatch)
    llm = FakeLLM(
        [
            reply(
                calls=[
                    tc("c1", "geocode_place", {"query": "Madina"}),
                    tc("c2", "geocode_place", {"query": "Accra Central"}),
                ]
            ),
            reply(
                calls=[
                    tc(
                        "c3",
                        "compare_departure_times",
                        {
                            "origin_id": "p1",
                            "destination_id": "p2",
                            "mode": "arrive_by",
                            "time_local": tomorrow_at(9),
                        },
                    )
                ]
            ),
            reply(content="Leave at 07:41 and the trip takes 99 minutes."),
        ]
    )
    resp = await run_agent(user("Madina to Accra Central by 9 tomorrow"), client=llm)
    assert resp.result is not None
    assert resp.result.labels.simulated is True
    assert resp.explanation_source == "template"
    assert "99" not in resp.reply
    assert [t.ok for t in resp.trace] == [True, True, True]


async def test_clarifying_question_calls_no_tools(monkeypatch):
    use_demo(monkeypatch)
    llm = FakeLLM([reply(content="Which place are you leaving from, and what time must you arrive?")])
    resp = await run_agent(user("When should I leave?"), client=llm)
    assert resp.result is None
    assert resp.trace == []
    assert resp.explanation_source == "llm"


async def test_llm_outage_is_handled(monkeypatch):
    use_demo(monkeypatch)
    llm = FakeLLM([openai.APIConnectionError(request=httpx.Request("POST", "http://x"))])
    resp = await run_agent(user("Madina to Osu"), client=llm)
    assert resp.notice
    assert resp.result is None
    assert resp.explanation_source == "none"


async def test_malformed_tool_call_is_retried_once(monkeypatch):
    use_demo(monkeypatch)
    bad = openai.BadRequestError(
        "Failed to call a function",
        response=httpx.Response(400, request=httpx.Request("POST", "http://x")),
        body={"code": "tool_use_failed"},
    )
    llm = FakeLLM([bad, reply(content="Which place are you leaving from?")])
    resp = await run_agent(user("When should I leave?"), client=llm)
    assert resp.explanation_source == "llm"
    assert resp.notice is None


async def test_unknown_place_returns_error_and_no_crash(monkeypatch):
    use_demo(monkeypatch)
    llm = FakeLLM(
        [
            reply(calls=[tc("c1", "geocode_place", {"query": "Atlantis"})]),
            reply(content="I could not find that place in Ghana. Please try another name."),
        ]
    )
    resp = await run_agent(user("Atlantis to Osu by 9"), client=llm)
    assert resp.result is None
    assert resp.trace[0].summary == "no match"