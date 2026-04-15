"""
Logging configuration for GlitchHunter.

Sets up structured logging with:
- Colorful, human-readable console output
- JSON file logging for machine processing
"""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from pythonjsonlogger import jsonlogger

from core.config import LoggingConfig as LoggingConfigData

# Module logger
logger = logging.getLogger(__name__)

# ANSI color codes for console output
COLORS = {
    'DEBUG': '\033[36m',     # Cyan
    'INFO': '\033[32m',      # Green
    'WARNING': '\033[33m',   # Yellow
    'ERROR': '\033[31m',     # Red
    'CRITICAL': '\033[35m',  # Magenta
    'RESET': '\033[0m',      # Reset
}


class ColorConsoleFormatter(logging.Formatter):
    """
    Human-readable console formatter with colors.
    
    Format: [LEVEL] Module: Message (file:line)
    """
    
    # Short module name mapping for cleaner output
    SHORT_NAMES = {
        'agent.state_machine': 'StateMachine',
        'agent.hypothesis_agent': 'HypothesisAgent',
        'agent.analyzer_agent': 'Analyzer',
        'agent.observer_agent': 'Observer',
        'agent.patch_generator': 'PatchGen',
        'agent.evidence_gate': 'EvidenceGate',
        'prefilter.pipeline': 'Prefilter',
        'prefilter.semgrep_runner': 'Semgrep',
        'prefilter.complexity': 'Complexity',
        'prefilter.git_churn': 'GitChurn',
        'security.shield': 'Shield',
        'security.owasp_scanner': 'OWASP',
        'mapper.repo_mapper': 'Mapper',
        'core.reporting': 'Reporter',
        'inference.engine': 'LLM',
        'hardware.detector': 'Hardware',
        'mcp_gw.socratiCode_client': 'MCP',
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record for console output.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log string
        """
        # Get short module name
        module_name = record.name
        if module_name.startswith('glitchhunter.'):
            module_name = module_name[len('glitchhunter.'):]
        
        short_name = self.SHORT_NAMES.get(module_name, module_name.split('.')[-1])
        
        # Color level
        level = record.levelname
        color = COLORS.get(level, COLORS['RESET'])
        
        # Format message
        message = record.getMessage()
        
        # Truncate long messages for console
        if len(message) > 200:
            message = message[:197] + '...'
        
        # Build output
        timestamp = datetime.now().strftime('%H:%M:%S')
        output = (
            f"{color}[{level:8}]{COLORS['RESET']} "
            f"{short_name}: "
            f"{message}"
        )
        
        # Add file:line for DEBUG and ERROR
        if record.levelno in (logging.DEBUG, logging.ERROR):
            output += f" ({record.filename}:{record.lineno})"
        
        return output


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
    
    Console output is human-readable with colors.
    File output is JSON for machine processing.

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

    # Console handler with colorful human-readable formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level_int)
    console_formatter = ColorConsoleFormatter()
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with JSON formatter (if log file specified)
    if log_file_path:
        # Ensure log directory exists
        log_dir = Path(log_file_path).parent
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Failed to create log directory {log_dir}: {e}")

        # Rotating file handler with JSON format
        try:
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=config.max_size_mb * 1024 * 1024,  # Convert MB to bytes
                backupCount=config.backup_count,
            )
            file_handler.setLevel(log_level_int)
            file_formatter = CustomJsonFormatter(
                fmt="%(timestamp)s %(level)s %(module)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
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
    logging.getLogger("networkx").setLevel(logging.WARNING)


class ProgressFormatter(logging.Formatter):
    """
    Special formatter for progress messages.
    
    Shows progress in a single line with percentage.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format progress message.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted progress string
        """
        message = record.getMessage()
        
        # Extract percentage if present
        percentage = None
        if '%' in message:
            try:
                parts = message.split('%')
                for part in parts:
                    if part.strip().isdigit():
                        percentage = int(part.strip())
                        break
            except (ValueError, IndexError):
                pass
        
        # Build progress bar
        if percentage is not None:
            bar_width = 30
            filled = int(bar_width * percentage / 100)
            bar = '█' * filled + '░' * (bar_width - filled)
            return f"\r[{bar}] {percentage:3d}%"
        
        return message


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
