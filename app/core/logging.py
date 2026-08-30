"""
Structured logging configuration using structlog.

Usage
-----
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("observation.created", camera_id=str(camera_id), plate="AS01AB1234")

All log entries are JSON objects in production, human-readable in development.
"""

import logging
import sys

import structlog

from app.config import Settings


def configure_logging(settings: Settings) -> None:
    """
    Configure structlog and the standard library logging to work together.

    Call once at application startup (inside the lifespan context).
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Shared processors applied to every log record regardless of source.
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.LOG_FORMAT == "json":
        # Production: pure JSON output
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(sys.stdout),
            cache_logger_on_first_use=True,
        )
    else:
        # Development: coloured console output
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
            foreign_pre_chain=shared_processors,
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
        root_logger.setLevel(log_level)

    # Route stdlib loggers (uvicorn, sqlalchemy, etc.) through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named structlog logger bound to the calling module."""
    return structlog.get_logger(name)
