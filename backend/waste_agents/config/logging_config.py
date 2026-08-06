"""
Centralized logging configuration.

Every module obtains its logger via `get_logger(__name__)` so log output
is consistent and can be redirected (e.g. to the Streamlit "Extraction Logs"
page) from a single place.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import settings, ensure_directories

_CONFIGURED = False


def configure_logging() -> None:
    """Idempotently configure the root logger. Safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    ensure_directories()
    log_path = Path(settings.logs_dir) / "agent.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger, configuring logging on first use."""
    configure_logging()
    return logging.getLogger(name)


class InMemoryLogCapture(logging.Handler):
    """
    A logging handler that keeps the last N log records in memory.

    Used by the Streamlit 'Extraction Logs' page to display live logs
    without tailing the log file from disk.
    """

    def __init__(self, capacity: int = 500) -> None:
        super().__init__()
        self.capacity = capacity
        self.records: list[str] = []
        self.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.records.append(msg)
        if len(self.records) > self.capacity:
            self.records.pop(0)

    def get_logs(self) -> list[str]:
        return list(self.records)
