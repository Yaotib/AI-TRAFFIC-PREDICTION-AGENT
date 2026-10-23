# backend/app/agent/llm.py
from openai import AsyncOpenAI

from ..config import get_settings


class LLMUnavailable(Exception):
    pass


def get_client() -> AsyncOpenAI:
    s = get_settings()
    if not s.groq_api_key:
        raise LLMUnavailable("The AI assistant is not configured (GROQ_API_KEY is missing).")
    # max_retries=1 caps automatic retries so a failing call cannot loop and burn quota.
    return AsyncOpenAI(
        base_url=s.groq_base_url,
        api_key=s.groq_api_key,
        timeout=s.llm_timeout_s,
        max_retries=1,
    )