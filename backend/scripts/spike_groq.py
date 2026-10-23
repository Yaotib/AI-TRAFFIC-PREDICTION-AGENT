# backend/scripts/spike_groq.py
"""Run from backend/:  python scripts/spike_groq.py"""
import asyncio
import json
import os
import time

import openai
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
client = AsyncOpenAI(
    base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
    api_key=os.environ["GROQ_API_KEY"],
    timeout=30,
    max_retries=0,
)
MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
TOOL = {
    "type": "function",
    "function": {
        "name": "geocode_place",
        "description": "Look up a place in Ghana by name.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}
PROMPTS = [
    "How long from Madina to Accra Central if I leave at 8am tomorrow?",
    "Where exactly is Achimota?",
    "I want to go from Osu to the airport, check the airport first.",
    "Find Kwame Nkrumah Circle for me.",
    "Look up Tema Station.",
]


async def one(prompt: str):
    start = time.perf_counter()
    try:
        raw = await client.chat.completions.with_raw_response.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You help with car journeys in Accra. Always use tools to look up places. Never guess."},
                {"role": "user", "content": prompt},
            ],
            tools=[TOOL],
            tool_choice="auto",
            temperature=0.2,
            max_completion_tokens=300,
        )
    except openai.OpenAIError as e:
        return False, time.perf_counter() - start, 0, {}, type(e).__name__
    resp = raw.parse()
    msg = resp.choices[0].message
    ok = False
    if msg.tool_calls:
        try:
            ok = "query" in json.loads(msg.tool_calls[0].function.arguments)
        except json.JSONDecodeError:
            ok = False
    tokens = resp.usage.total_tokens if resp.usage else 0
    return ok, time.perf_counter() - start, tokens, raw.headers, ""


async def main():
    results = []
    headers = {}
    for prompt in PROMPTS * 2:  # 10 calls
        ok, secs, tokens, headers, err = await one(prompt)
        results.append((ok, secs, tokens))
        print(f"{'OK ' if ok else 'BAD'} {secs:5.1f}s {tokens:>5} tok  {err}  {prompt}")
    good = sum(1 for ok, _, _ in results if ok)
    avg_s = sum(s for _, s, _ in results) / len(results)
    avg_t = sum(t for _, _, t in results) / len(results)
    print(f"\nValid tool calls: {good}/{len(results)}  avg latency {avg_s:.1f}s  avg tokens/call {avg_t:.0f}")
    for name in (
        "x-ratelimit-limit-requests", "x-ratelimit-remaining-requests",
        "x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens",
    ):
        print(f"{name}: {headers.get(name, 'not returned')}")


asyncio.run(main())