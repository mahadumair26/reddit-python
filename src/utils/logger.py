"""Centralized logging configuration."""

import logging
import sys
from pathlib import Path

from pythonjsonlogger import jsonlogger

from src.config.settings import settings


def setup_logger(name: str = __name__) -> logging.Logger:
    """Return a configured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    json_formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    plain_formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if settings.ENVIRONMENT == "production":
        console_handler.setFormatter(json_formatter)
    else:
        console_handler.setFormatter(plain_formatter)
    logger.addHandler(console_handler)

    if settings.LOG_FILE:
        log_path = Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(json_formatter if settings.ENVIRONMENT == "production" else plain_formatter)
        logger.addHandler(file_handler)

    return logger


logger = setup_logger("reddit_scraper")
