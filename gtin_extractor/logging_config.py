"""Logging configuration for gtin_extractor."""

import logging
import sys
from pathlib import Path


def setup_logging(
    log_level: str = "INFO",
    log_file: str | None = None,
) -> logging.Logger:
    """Configure and return the root logger for gtin_extractor.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to a log file. If *None*, only console output is used.

    Returns:
        Configured logger instance for 'gtin_extractor'.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logger = logging.getLogger("gtin_extractor")
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers when called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(Path(log_file), encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "gtin_extractor") -> logging.Logger:
    """Return a child logger under the gtin_extractor namespace.

    Args:
        name: Dotted logger name (e.g. 'gtin_extractor.readers').

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)
