"""
Tests for the optional LangSmith tracing layer.

The property that matters most is that tracing is never load-bearing: the
pipeline must behave identically whether it is off, misconfigured, or
failing to reach LangSmith.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from config.settings import settings
from services.tracing_service import is_tracing_enabled, log_metadata, reset_cache, traced


@pytest.fixture(autouse=True)
def clean_tracing_state():
    """Each test decides its own tracing configuration."""
    reset_cache()
    original = (settings.langsmith_tracing, settings.langsmith_api_key)
    yield
    settings.langsmith_tracing, settings.langsmith_api_key = original
    reset_cache()


def test_tracing_is_off_without_an_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "langsmith_tracing", True)
    monkeypatch.setattr(settings, "langsmith_api_key", None)
    reset_cache()
    assert is_tracing_enabled() is False


def test_tracing_is_off_when_the_flag_is_false(monkeypatch) -> None:
    monkeypatch.setattr(settings, "langsmith_tracing", False)
    monkeypatch.setattr(settings, "langsmith_api_key", "ls__key")
    reset_cache()
    assert is_tracing_enabled() is False


def test_decorated_function_behaves_identically_when_tracing_is_off(monkeypatch) -> None:
    """With tracing off the decorator returns the function untouched, so
    there is no wrapper overhead in normal operation."""
    monkeypatch.setattr(settings, "langsmith_tracing", False)
    reset_cache()

    @traced(name="double")
    def double(x: int) -> int:
        return x * 2

    assert double(21) == 42


def test_decorated_function_preserves_exceptions(monkeypatch) -> None:
    monkeypatch.setattr(settings, "langsmith_tracing", False)
    reset_cache()

    @traced(name="boom")
    def boom() -> None:
        raise ValueError("expected")

    with pytest.raises(ValueError, match="expected"):
        boom()


def test_log_metadata_is_safe_without_an_active_run(monkeypatch) -> None:
    """Called from anywhere in the pipeline, including outside a traced
    call, so it must never raise."""
    monkeypatch.setattr(settings, "langsmith_tracing", False)
    reset_cache()
    log_metadata(crop="wheat", sources=30)  # must not raise


def test_tracing_state_is_cached(monkeypatch) -> None:
    """Resolved once rather than re-importing the SDK on every traced call."""
    monkeypatch.setattr(settings, "langsmith_tracing", False)
    reset_cache()
    assert is_tracing_enabled() is False

    # Flipping the setting without resetting must not change the answer
    monkeypatch.setattr(settings, "langsmith_tracing", True)
    monkeypatch.setattr(settings, "langsmith_api_key", "ls__key")
    assert is_tracing_enabled() is False

    reset_cache()  # now it re-evaluates
