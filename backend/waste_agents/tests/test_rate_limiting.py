"""
Unit tests for the shared LLM rate limiter (services/llm_service.py).

No network calls are made. The property that matters most: a 429 backs the
WHOLE pipeline off long enough for the quota window to actually reopen,
instead of burning retries in seconds the way production did before this
fix (three attempts, all failed, inside 6 seconds).
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.llm_service import RateLimiter, _is_rate_limit, _retry_after_seconds, _retry_delay


def test_rate_limiter_serializes_concurrent_threads() -> None:
    limiter = RateLimiter(0.05)
    timestamps: list[float] = []
    lock = threading.Lock()

    def worker() -> None:
        limiter.acquire()
        with lock:
            timestamps.append(time.monotonic())

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    timestamps.sort()
    gaps = [b - a for a, b in zip(timestamps, timestamps[1:])]
    assert all(gap >= 0.04 for gap in gaps)


def test_zero_interval_disables_the_limiter() -> None:
    limiter = RateLimiter(0.0)
    start = time.monotonic()
    for _ in range(20):
        limiter.acquire()
    assert time.monotonic() - start < 0.5


def test_penalize_delays_every_thread_not_just_the_failing_one() -> None:
    limiter = RateLimiter(0.01)
    limiter.acquire()
    limiter.penalize(0.2)

    start = time.monotonic()
    limiter.acquire()
    assert time.monotonic() - start >= 0.15


def test_is_rate_limit_detects_known_shapes() -> None:
    assert _is_rate_limit(Exception('Status 429 {"type":"rate_limited"}')) is True
    assert _is_rate_limit(Exception("Rate limit exceeded")) is True
    assert _is_rate_limit(Exception('"code":"rate_limited"')) is True


def test_is_rate_limit_ignores_unrelated_errors() -> None:
    assert _is_rate_limit(Exception("Connection timeout")) is False
    assert _is_rate_limit(Exception("Invalid API key")) is False


def test_rate_limit_backoff_exceeds_network_error_backoff() -> None:
    rate_limit_error = Exception("Status 429 rate_limited")
    network_error = Exception("Connection reset by peer")
    assert _retry_delay(rate_limit_error, 1) > _retry_delay(network_error, 1)


def test_rate_limit_backoff_matches_expected_schedule() -> None:
    """
    Non-regression: in production, 3 attempts burned inside 6 seconds all
    failed with 429. The schedule must give the quota window a real chance.
    """
    error = Exception("Status 429 rate_limited")
    assert _retry_delay(error, 1) >= 15
    assert _retry_delay(error, 2) >= 30
    assert _retry_delay(error, 3) >= 60


def test_retry_after_header_takes_priority_over_computed_backoff() -> None:
    class FakeResponse:
        headers = {"Retry-After": "5"}

    class FakeError(Exception):
        response = FakeResponse()

    hinted = _retry_after_seconds(FakeError("rate limited"))
    assert hinted == 5.0

    delay = _retry_delay(FakeError("rate limited"), 1)
    assert 5 <= delay <= 6.5


def test_jitter_makes_successive_calls_differ() -> None:
    error = Exception("Status 429 rate_limited")
    delays = {_retry_delay(error, 1) for _ in range(8)}
    assert len(delays) > 1
