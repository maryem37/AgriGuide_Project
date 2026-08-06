"""
LLM service abstraction.

Any LLM provider can be plugged in by implementing `LLMService`. The rest
of the codebase (agents/*) only depends on this interface, never on a
concrete provider, so swapping Mistral for another provider means writing
one new class here and flipping `settings.llm_provider`.
"""
from __future__ import annotations

import json
import random
import re
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from config.logging_config import get_logger
from config.settings import settings
from services.tracing_service import log_metadata, traced

logger = get_logger(__name__)


class LLMServiceError(Exception):
    """Raised when the LLM call fails after all retries, or returns unparseable output."""


class LLMService(ABC):
    """Abstract interface every LLM provider must implement."""

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 4000,
    ) -> str:
        """Return the raw text completion for a system+user prompt pair."""
        raise NotImplementedError

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 4000,
    ) -> dict[str, Any] | list[Any]:
        """
        Call `complete` and parse the result as JSON, stripping common
        LLM artifacts (markdown code fences, stray prose) defensively.
        Raises LLMServiceError if parsing fails after cleanup.
        """
        raw = self.complete(system_prompt, user_prompt, temperature=temperature, max_tokens=max_tokens)
        cleaned = _strip_json_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Last-resort recovery: try to isolate the outermost {...} or [...]
            extracted = _extract_json_block(cleaned)
            if extracted is None:
                logger.error("Failed to parse LLM output as JSON. Raw output: %.500s", raw)
                raise LLMServiceError(f"LLM did not return valid JSON: {raw[:200]}")
            try:
                return json.loads(extracted)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse extracted JSON block. Block: %.500s", extracted)
                raise LLMServiceError(f"LLM returned unparseable JSON: {e}")


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_block(text: str) -> Optional[str]:
    """Find the outermost balanced {...} or [...] block in text."""
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == open_ch:
                depth += 1
            elif text[i] == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None


class RateLimiter:
    """
    Process-wide minimum interval between LLM requests.

    Extraction runs several sources in parallel, so without this the
    threads fire simultaneously and trip the provider's per-second limit --
    which is exactly what the retries then have to recover from. Spacing
    requests at the source is cheaper than retrying after a 429.
    """

    def __init__(self, min_interval_seconds: float) -> None:
        self.min_interval = min_interval_seconds
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def acquire(self) -> None:
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            wait = self._next_allowed - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self._next_allowed = now + self.min_interval

    def penalize(self, seconds: float) -> None:
        """
        Hold back *every* thread after a rate limit, not just the one that
        hit it.

        Threads share one quota, so when one gets a 429 the others are
        moments away from the same fate. Backing the whole pipeline off at
        once is what actually lets the window reopen.
        """
        with self._lock:
            self._next_allowed = max(self._next_allowed, time.monotonic() + seconds)


_rate_limiter: Optional[RateLimiter] = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        with _rate_limiter_lock:
            if _rate_limiter is None:
                _rate_limiter = RateLimiter(settings.llm_min_request_interval)
    return _rate_limiter


def _is_rate_limit(error: Exception) -> bool:
    """Detect a 429 across SDK versions, which vary in how they surface it."""
    text = str(error).lower()
    return "429" in text or "rate limit" in text or "rate_limited" in text


def _retry_after_seconds(error: Exception) -> Optional[float]:
    """
    Read the provider's own Retry-After hint, when it gives one.

    The API knows when its window reopens far better than any guess we can
    make, so this takes precedence over computed backoff.
    """
    for attr in ("response", "http_response", "raw_response"):
        response = getattr(error, attr, None)
        headers = getattr(response, "headers", None)
        if not headers:
            continue
        for key in ("Retry-After", "retry-after", "x-ratelimit-reset"):
            value = headers.get(key) if hasattr(headers, "get") else None
            if value:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
    return None


def _retry_delay(error: Exception, attempt: int) -> float:
    """
    Backoff for a failed attempt.

    Rate limits are treated very differently from network errors. A 429
    means a quota window must elapse before anything can succeed, so
    retrying seconds later simply burns another request and guarantees
    another 429 -- which is exactly what happened in production, where
    three attempts failed inside 6 seconds. Network blips, by contrast,
    often clear immediately.

    Jitter spreads the retries of concurrently-failing threads, which
    otherwise all wake at the same instant and re-trigger the limit.
    """
    hinted = _retry_after_seconds(error)
    if hinted is not None:
        return min(hinted, 120) + random.uniform(0, 1.5)

    if _is_rate_limit(error):
        # 15s, 30s, 60s, 120s: give the quota window a real chance to reopen.
        base = min(15 * (2 ** (attempt - 1)), 120)
    else:
        base = min(2 ** attempt, 30)

    return base + random.uniform(0, 1.5)


class MistralLLMService(LLMService):
    """Mistral API implementation of LLMService."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or settings.mistral_api_key
        self.model = model or settings.mistral_model
        if not self.api_key:
            logger.warning(
                "MISTRAL_API_KEY is not set. MistralLLMService calls will fail until it is configured "
                "in the environment or .env file."
            )
        self._client = None  # lazy-initialized

    def _get_client(self):
        if self._client is None:
            try:
                from mistralai import Mistral
            except ImportError as e:
                raise LLMServiceError(
                    "The 'mistralai' package is required. Install it with: pip install mistralai"
                ) from e
            self._client = Mistral(api_key=self.api_key)
        return self._client

    @traced(name="mistral_chat_complete", run_type="llm")
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 4000,
    ) -> str:
        if not self.api_key:
            raise LLMServiceError(
                "MISTRAL_API_KEY is not configured. Set it in your environment or .env file."
            )

        log_metadata(
            model=self.model,
            system_prompt_chars=len(system_prompt),
            user_prompt_chars=len(user_prompt),
        )

        client = self._get_client()
        temp = settings.llm_temperature if temperature is None else temperature

        last_error: Optional[Exception] = None
        for attempt in range(1, settings.llm_max_retries + 1):
            try:
                get_rate_limiter().acquire()
                response = client.chat.complete(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temp,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content
                if isinstance(content, list):
                    # Some SDK versions return a list of content blocks
                    content = "".join(getattr(c, "text", str(c)) for c in content)
                return content or ""
            except Exception as e:  # noqa: BLE001 - broad on purpose, network/SDK errors vary
                last_error = e
                # Sleeping after the final attempt just delays the failure.
                if attempt >= settings.llm_max_retries:
                    break
                wait = _retry_delay(e, attempt)
                # A 429 means the shared quota is exhausted, so hold every
                # thread back -- not just this one -- until it recovers.
                if _is_rate_limit(e):
                    get_rate_limiter().penalize(wait)
                logger.warning(
                    "Mistral API call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt,
                    settings.llm_max_retries,
                    e,
                    wait,
                )
                log_metadata(
                    retry_attempt=attempt,
                    retry_reason="rate_limit" if _is_rate_limit(e) else "error",
                )
                time.sleep(wait)

        raise LLMServiceError(f"Mistral API call failed after {settings.llm_max_retries} attempts: {last_error}")


def get_llm_service() -> LLMService:
    """Factory returning the configured LLM provider."""
    if settings.llm_provider == "mistral":
        return MistralLLMService()
    raise ValueError(
        f"Unknown llm_provider '{settings.llm_provider}'. "
        f"Implement a new LLMService subclass and register it in get_llm_service()."
    )
