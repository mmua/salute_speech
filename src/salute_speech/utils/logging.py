"""
Logging configuration for the Sber Speech Recognition service.
"""
from __future__ import annotations

import logging


def setup_logger(name: str, level: int | None = None) -> logging.Logger:
    """
    Set up a logger with consistent formatting.

    Args:
        name: Logger name
        level: Logging level (defaults to DEBUG)

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    if level is not None:
        logger.setLevel(level)
    elif logger.level == logging.NOTSET:
        logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)

    return logger
