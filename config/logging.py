"""
Centralized logging configuration for seo-flow.

Provides consistent logging format across all modules.
"""

import logging
import sys
from pathlib import Path


def setup_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
) -> logging.Logger:
    """
    Configure application-wide logging.

    Args:
        level: Logging level (default: INFO).
        log_file: Optional path to log file.

    Returns:
        Root logger instance.

    Example:
        >>> logger = setup_logging(level=logging.DEBUG)
        >>> logger.info("Application started")
    """
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
    ]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)

    return logging.getLogger("seo-flow")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (typically __name__).

    Returns:
        Logger instance for the module.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Processing data...")
    """
    return logging.getLogger(f"seo-flow.{name}")
