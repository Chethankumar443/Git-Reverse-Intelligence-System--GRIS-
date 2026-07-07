"""
Structured logging setup using structlog.

Produces machine-readable JSON in production and colourised, human-friendly
output in development / TUI contexts. Integrated with Python's stdlib
`logging` so that third-party library logs (gitpython, httpx) flow through
the same pipeline.

Usage:
    from git_reverse.core.logging import get_logger
    log = get_logger(__name__)
    log.info("cloning_started", url=url, destination=str(dest))
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger


# ── Custom Processors ─────────────────────────────────────────────────────────
def _add_app_context(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Inject the application name and log level into every event."""
    event_dict.setdefault("app", "git-reverse")
    return event_dict


def _drop_color_message_key(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Remove the `color_message` key injected by uvicorn and other libraries.
    It's redundant when structlog handles formatting.
    """
    event_dict.pop("color_message", None)
    return event_dict


# ── Configuration ─────────────────────────────────────────────────────────────
def configure_logging(level: str = "INFO", *, dev_mode: bool = False) -> None:
    """
    Configure structlog and stdlib logging for the application.

    Args:
        level: Log level string (DEBUG | INFO | WARNING | ERROR).
        dev_mode: If True, use colourised console output instead of JSON.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Shared processors applied to every log record
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _add_app_context,
        _drop_color_message_key,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if dev_mode:
        # Pretty, colourised output for terminals
        renderer: Any = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    else:
        # JSON lines for log aggregators / file sinks
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Silence overly verbose third-party loggers
    for noisy in ("git", "urllib3", "httpx", "httpcore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Return a bound structlog logger.

    Args:
        name: Typically `__name__` of the calling module.

    Returns:
        A structlog BoundLogger with the module name bound as context.
    """
    return structlog.get_logger(name)
