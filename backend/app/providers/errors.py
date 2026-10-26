"""Friendly provider errors.

Rule from the guide: timeouts, rate limits, rejected keys and unreadable
answers become clear errors, and an error message must never contain the
request address, because the address can contain the API key.

So messages here are fixed sentences. They never include the original
exception text or URL.
"""


class ProviderError(Exception):
    """Base class. `str(error)` is safe to show to a user or an AI model."""

    def __init__(self, message: str, *, code: str = "error", retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def describe_status(status: int, service: str) -> tuple[str, str, bool]:
    """Turn an HTTP status code into (code, message, retryable)."""
    if status == 429:
        return (
            "rate_limited",
            f"{service} is receiving too many requests right now. Try again in a minute.",
            True,
        )
    if status in (401, 403):
        return (
            "key_rejected",
            f"{service} rejected the API key. Check that the key is valid and the API is enabled.",
            False,
        )
    if status == 400:
        return ("bad_request", f"{service} could not understand the request.", False)
    if status >= 500:
        return (
            "unavailable",
            f"{service} is temporarily unavailable. Try again shortly.",
            True,
        )
    return (
        "bad_response",
        f"{service} sent an unexpected answer (status {status}).",
        False,
    )


def timeout_message(service: str) -> str:
    return f"{service} took too long to answer. Try again."


def network_message(service: str) -> str:
    return f"Could not reach {service}. Check the internet connection and try again."


def unreadable_message(service: str) -> str:
    return f"{service} sent an answer that could not be read."


def not_configured_message(service: str) -> str:
    return f"{service} is not configured (the Google Maps API key is missing)."
