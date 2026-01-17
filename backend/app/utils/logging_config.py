"""
Logging Configuration
"""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(log_level: str = "INFO"):
    """
    Setup logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # Main application log file (rotating)
    app_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    app_handler.setLevel(numeric_level)
    app_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(app_handler)

    # Trading-specific log file
    trading_logger = logging.getLogger("trading")
    trading_handler = RotatingFileHandler(
        log_dir / "trading.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    trading_handler.setLevel(logging.INFO)
    trading_handler.setFormatter(detailed_formatter)
    trading_logger.addHandler(trading_handler)

    # Error-only log file
    error_handler = RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    # Scheduler log file
    scheduler_logger = logging.getLogger("scheduler")
    scheduler_handler = RotatingFileHandler(
        log_dir / "scheduler.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    scheduler_handler.setLevel(logging.INFO)
    scheduler_handler.setFormatter(detailed_formatter)
    scheduler_logger.addHandler(scheduler_handler)

    # Gemini LLM log file
    gemini_logger = logging.getLogger("gemini")
    gemini_handler = RotatingFileHandler(
        log_dir / "gemini.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    gemini_handler.setLevel(logging.DEBUG)
    gemini_handler.setFormatter(detailed_formatter)
    gemini_logger.addHandler(gemini_handler)

    # Reduce verbosity of some third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.info(f"Logging configured with level: {log_level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
