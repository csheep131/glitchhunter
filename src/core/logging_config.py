"""
Logging configuration for GlitchHunter.

Sets up structured JSON logging with timestamps, levels, and module information.
"""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from pythonjsonlogger import jsonlogger

from .config import LoggingConfig as LoggingConfigData

# Module logger
logger = logging.getLogger(__name__)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for structured logging.

    Adds timestamp, level, and module information to all log records.
    """

    def add_fields(
        self,
        log_record: dict,
        record: logging.LogRecord,
        message_dict: dict,
    ) -> None:
        """
        Add custom fields to log record.

        Args:
            log_record: Dictionary to populate with log data
            record: Original logging record
            message_dict: Additional message dictionary
        """
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.utcnow().isoformat()

        # Add log level
        log_record["level"] = record.levelname

        # Add module name
        log_record["module"] = record.name

        # Add filename and line number for debugging
        log_record["file"] = record.filename
        log_record["line"] = record.lineno

        # Add function name
        log_record["function"] = record.funcName


def setup_logging(
    config: Optional[LoggingConfigData] = None,
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    Set up logging configuration for the application.

    Args:
        config: Logging configuration from config.yaml
        log_level: Override log level (optional)
        log_file: Override log file path (optional)
    """
    # Use provided config or defaults
    if config is None:
        config = LoggingConfigData(
            level="INFO",
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            file="logs/glitchhunter.log",
            max_size_mb=100,
            backup_count=5,
        )

    # Determine log level
    level_str = log_level or config.level
    log_level_int = getattr(logging, level_str.upper(), logging.INFO)

    # Determine log file path
    log_file_path = log_file or config.file

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_int)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = CustomJsonFormatter(
        fmt="%(timestamp)s %(level)s %(module)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level_int)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if log file specified)
    if log_file_path:
        # Ensure log directory exists
        log_dir = Path(log_file_path).parent
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Failed to create log directory {log_dir}: {e}")

        # Rotating file handler
        try:
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=config.max_size_mb * 1024 * 1024,  # Convert MB to bytes
                backupCount=config.backup_count,
            )
            file_handler.setLevel(log_level_int)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file_path}")
        except OSError as e:
            logger.warning(f"Failed to create log file handler: {e}")

    # Log startup message
    logger.info(
        "Logging initialized",
        extra={
            "level": level_str,
            "log_file": log_file_path,
            "max_size_mb": config.max_size_mb,
            "backup_count": config.backup_count,
        },
    )

    # Set third-party library log levels to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("semgrep").setLevel(logging.WARNING)
    logging.getLogger("tree_sitter").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class LoggingContext:
    """
    Context manager for temporary log level changes.

    Usage:
        with LoggingContext("DEBUG"):
            # Code that runs with DEBUG logging
            pass
    """

    def __init__(self, level: str) -> None:
        """
        Initialize logging context.

        Args:
            level: Log level string (e.g., "DEBUG", "INFO")
        """
        self.level = level
        self.original_level: Optional[int] = None

    def __enter__(self) -> "LoggingContext":
        """Enter context and set temporary log level."""
        root_logger = logging.getLogger()
        self.original_level = root_logger.level
        root_logger.setLevel(getattr(logging, self.level.upper(), logging.INFO))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and restore original log level."""
        if self.original_level is not None:
            logging.getLogger().setLevel(self.original_level)
