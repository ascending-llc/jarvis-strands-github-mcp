"""Logging configuration for the orchestrator."""

import logging
import logging.handlers
import os
from typing import Optional


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    name: str = "orchestrator",
) -> logging.Logger:
    """
    Set up structured logging with file and console handlers.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Defaults to INFO or ORCHESTRATOR_LOG_LEVEL env var.
        log_file: Optional path to log file. If provided, logs will be written to file with rotation.
        name: Logger name (default: "orchestrator")

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if logger.handlers:
        return logger

    # Determine log level
    if level is None:
        level = os.getenv("ORCHESTRATOR_LOG_LEVEL", "INFO").upper()

    logger.setLevel(level)

    # Formatter with structured information
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    if log_file is None:
        log_file = os.getenv("ORCHESTRATOR_LOG_FILE", "orchestrator.log")

    if log_file:
        # Create logs directory if needed
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Rotating file handler: 10MB per file, keep 5 files
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
