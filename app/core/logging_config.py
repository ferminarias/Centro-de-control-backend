"""
Structured logging configuration using structlog.
"""
import logging
import sys

import structlog
from structlog.processors import (
    TimeStamper,
    JSONRenderer,
    CallsiteParameter,
    CallsiteParameterAdder,
)
from structlog.stdlib import (
    BoundLogger,
    LoggerFactory,
    add_log_level,
    add_logger_name,
    filter_by_level,
)

def configure_logging(environment: str = "development"):
    """
    Configure structured logging for the application.
    
    Args:
        environment: "development" or "production"
    """
    
    shared_processors = [
        # Add timestamp
        TimeStamper(fmt="iso"),
        # Add log level
        add_log_level,
        # Add logger name
        add_logger_name,
        # Add callsite info (file, line, function)
        CallsiteParameterAdder(
            [
                CallsiteParameter.FILENAME,
                CallsiteParameter.LINENO,
                CallsiteParameter.FUNC_NAME,
            ]
        ),
        # Format exceptions
        structlog.processors.format_exc_info,
    ]
    
    if environment == "development":
        # Pretty console output for development
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True)
            ],
            context_class=dict,
            logger_factory=LoggerFactory(),
            wrapper_class=BoundLogger,
            cache_logger_on_first_use=True,
        )
    else:
        # JSON output for production (easier to parse)
        structlog.configure(
            processors=shared_processors + [
                JSONRenderer()
            ],
            context_class=dict,
            logger_factory=LoggerFactory(),
            wrapper_class=BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    return structlog.get_logger()


def get_logger(name: str = None):
    """Get a structured logger."""
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()
