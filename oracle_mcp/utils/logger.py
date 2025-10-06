# Relative Path: oracle_mcp/utils/logger.py
"""
Common logging utility for the Oracle MCP server.

Provides a single place to configure logging (file and optional console),
using centralized configuration from `oracle_mcp.config`.

Usage:
    from oracle_mcp.utils.logger import setup_logging, get_logger
    setup_logging(enable_console=False)
    logger = get_logger()
    logger.info("Server starting...")
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from oracle_mcp.config import LOG_DIRECTORY, LOG_FILENAME, LOG_LEVEL

# Map log level string to logging level
_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_DEFAULT_LOGGER_NAME = "oracle_mcp"


def _ensure_log_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def setup_logging(enable_console: bool = False,
                  logger_name: str = _DEFAULT_LOGGER_NAME,
                  log_directory: Optional[str] = None,
                  log_filename: Optional[str] = None,
                  log_level_name: Optional[str] = None) -> logging.Logger:
    """
    Configure the application logger in a single place.

    Parameters:
    - enable_console: If True, also log to console (stderr)
    - logger_name: Named logger to configure (default: 'oracle_mcp')
    - log_directory: Override log directory (defaults to config.LOG_DIRECTORY)
    - log_filename: Override log filename (defaults to config.LOG_FILENAME)
    - log_level_name: Override level name (defaults to config.LOG_LEVEL)

    Returns:
    - Configured logger instance
    """
    directory = Path(log_directory or LOG_DIRECTORY)
    filename = log_filename or LOG_FILENAME
    level_name = (log_level_name or LOG_LEVEL or "INFO").upper()
    level = _LEVEL_MAP.get(level_name, logging.INFO)

    _ensure_log_dir(directory)
    log_file_path = directory / filename

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    existing_targets = set()
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler):
            existing_targets.add(getattr(h, "baseFilename", None))
        elif isinstance(h, logging.StreamHandler):
            existing_targets.add("__console__")

    # File handler
    if str(log_file_path) not in existing_targets:
        file_handler = logging.FileHandler(str(log_file_path))
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logger.addHandler(file_handler)

    # Optional console handler
    if enable_console and "__console__" not in existing_targets:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logger.addHandler(console_handler)

    # Prevent double logging to root if other basicConfig is set elsewhere
    logger.propagate = False

    return logger


def get_logger(name: str = _DEFAULT_LOGGER_NAME) -> logging.Logger:
    """Return the named logger (configure it first with setup_logging)."""
    return logging.getLogger(name)
