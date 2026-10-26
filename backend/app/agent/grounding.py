# backend/app/agent/grounding.py
import re

_NUM = re.compile(r"\d+(?::\d+)?(?:\.\d+)?")


def _norm(tok: str) -> str:
    if ":" in tok:
        h, m = tok.split(":", 1)
        return f"{int(h)}:{m}"
    if "." in tok:
        a, b = tok.split(".", 1)
        return f"{int(a)}.{b}"
    return str(int(tok))


def numbers_in(text: str) -> set[str]:
    return {_norm(t) for t in _NUM.findall(text)}


def is_grounded(reply: str, sources: list[str]) -> tuple[bool, list[str]]:
    """True only if every number or time in `reply` also appears in `sources`."""
    allowed: set[str] = set()
    for s in sources:
        allowed |= numbers_in(s)
    bad = sorted(numbers_in(reply) - allowed)
    return (not bad, bad)