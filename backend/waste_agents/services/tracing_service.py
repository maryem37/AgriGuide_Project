"""
Optional LangSmith tracing.

The project doesn't use LangChain, so this wraps the `langsmith` SDK
directly. Everything here degrades to a no-op when the package isn't
installed or no API key is configured, which keeps tracing a debugging
aid rather than a runtime dependency.

Why a wrapper instead of importing @traceable everywhere: the agents
should not care whether tracing exists. If LangSmith is later swapped for
something else, only this file changes.
"""
from __future__ import annotations

import functools
from typing import Any, Callable, Optional, TypeVar

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_tracing_enabled: Optional[bool] = None


def is_tracing_enabled() -> bool:
    """
    True when tracing is switched on, keyed, and the SDK is importable.

    Resolved once and cached: this is checked on every traced call, and a
    failed import shouldn't be retried on each one.
    """
    global _tracing_enabled
    if _tracing_enabled is not None:
        return _tracing_enabled

    if not settings.langsmith_tracing or not settings.langsmith_api_key:
        _tracing_enabled = False
        return False

    try:
        import langsmith  # noqa: F401
    except ImportError:
        logger.warning(
            "LANGSMITH_TRACING is on but the 'langsmith' package is missing. "
            "Install it with: pip install langsmith. Continuing without tracing."
        )
        _tracing_enabled = False
        return False

    # The SDK reads these from the environment, so mirror our settings into
    # it rather than making callers configure the same thing twice.
    import os

    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_TRACING"] = "true"
    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint

    logger.info("LangSmith tracing enabled (project: %s).", settings.langsmith_project)
    _tracing_enabled = True
    return True


def traced(name: Optional[str] = None, run_type: str = "chain") -> Callable[[F], F]:
    """
    Decorator recording a function call as a LangSmith run.

    `run_type` should be "llm" for model calls, "retriever" for search and
    vector lookups, and "chain" for everything else -- LangSmith renders
    each differently, so getting it right makes traces far easier to read.

    When tracing is off the function is returned untouched, so there is no
    wrapper overhead in normal operation.
    """

    def decorator(func: F) -> F:
        if not is_tracing_enabled():
            return func

        try:
            from langsmith import traceable

            return traceable(name=name or func.__name__, run_type=run_type)(func)
        except Exception as e:  # noqa: BLE001
            logger.debug("Could not wrap '%s' with LangSmith tracing: %s", func.__name__, e)
            return func

    return decorator


def log_metadata(**kwargs: Any) -> None:
    """
    Attach key/value metadata to the currently active run.

    Used to record things worth filtering traces by later -- which crop was
    researched, how many sources survived validation, why an extraction was
    rejected. Silently does nothing when there is no active run.
    """
    if not is_tracing_enabled():
        return
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        if run is not None:
            run.extra.setdefault("metadata", {}).update(kwargs)
    except Exception as e:  # noqa: BLE001
        logger.debug("Could not attach LangSmith metadata: %s", e)


def reset_cache() -> None:
    """Re-evaluate whether tracing is enabled. Intended for tests."""
    global _tracing_enabled
    _tracing_enabled = None
