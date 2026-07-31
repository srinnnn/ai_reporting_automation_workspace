from __future__ import annotations

import logging as std_logging
from pathlib import Path

from .config import CoreConfig, load_core_config


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
SUPPORTED_LEVELS = frozenset({"INFO", "WARNING", "ERROR"})


def configure_logging(
    config: CoreConfig | None = None,
    level: str = "INFO",
) -> Path:
    actual_config = config if config is not None else load_core_config()
    if not isinstance(actual_config, CoreConfig):
        raise TypeError("config must be CoreConfig")
    normalized_level = _normalize_level(level)
    log_dir = actual_config.files.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = std_logging.getLogger("ai_reporting_automation")
    logger.setLevel(getattr(std_logging, normalized_level))
    logger.propagate = False
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()

    formatter = std_logging.Formatter(LOG_FORMAT)
    file_handler = std_logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(std_logging, normalized_level))
    logger.addHandler(file_handler)

    stream_handler = std_logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(getattr(std_logging, normalized_level))
    logger.addHandler(stream_handler)

    assert log_dir.exists()
    return log_dir


def get_logger(module_name: str) -> std_logging.Logger:
    if not isinstance(module_name, str) or not module_name.strip():
        raise ValueError("module_name must not be empty")
    logger = std_logging.getLogger(f"ai_reporting_automation.{module_name.strip()}")
    assert isinstance(logger, std_logging.Logger)
    return logger


def _normalize_level(level: str) -> str:
    if not isinstance(level, str):
        raise TypeError("level must be text")
    normalized = level.strip().upper()
    if normalized not in SUPPORTED_LEVELS:
        raise ValueError("level must be INFO, WARNING, or ERROR")
    return normalized
