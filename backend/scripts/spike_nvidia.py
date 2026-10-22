# backend/scripts/spike_nvidia.py
"""Run from backend/:  python scripts/spike_nvidia.py"""
import asyncio
import json
import os
import time

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
client = AsyncOpenAI(
    base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ["NVIDIA_API_KEY"],
    timeout=30,
    max_retries=0,
)
MODEL = os.environ["LLM_MODEL"]
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
    r = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You help with car journeys in Accra. Always use tools to look up places. Never guess."},
            {"role": "user", "content": prompt},
        ],
        tools=[TOOL],
        tool_choice="auto",
        temperature=0.2,
        max_tokens=300,
    )
    msg = r.choices[0].message
    ok = False
    if msg.tool_calls:
        try:
            ok = "query" in json.loads(msg.tool_calls[0].function.arguments)
        except json.JSONDecodeError:
            ok = False
    return ok, time.perf_counter() - start


async def main():
    results = []
    for prompt in PROMPTS * 2:  # 10 calls, sequential to respect rate limits
        ok, secs = await one(prompt)
        results.append((ok, secs))
        print(f"{'OK ' if ok else 'BAD'} {secs:5.1f}s  {prompt}")
    good = sum(1 for ok, _ in results if ok)
    avg = sum(s for _, s in results) / len(results)
    print(f"\nValid tool calls: {good}/{len(results)}   average latency: {avg:.1f}s")


asyncio.run(main())