"""
Logging configuration for the application.
Provides structured logging with file rotation and different log levels.
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
import json
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Format the message
        message = super().format(record)

        # Add color to level name
        colored_level = f"{log_color}{record.levelname}{reset}"
        message = message.replace(record.levelname, colored_level)

        return message


def setup_logger(
    name: str = "backend-ai",
    log_level: str = "INFO",
    log_dir: str = "logs",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_json_logs: bool = True,
    enable_console: bool = True
) -> logging.Logger:
    """
    Setup and configure application logger.

    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
        enable_json_logs: Enable JSON formatted file logging
        enable_console: Enable console logging

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Console Handler (colored, human-readable)
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # File Handler - JSON format (for parsing/analysis)
    if enable_json_logs:
        json_file = log_path / f"{name}_json.log"
        json_handler = RotatingFileHandler(
            json_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONFormatter())
        logger.addHandler(json_handler)

    # File Handler - Plain text (human-readable)
    text_file = log_path / f"{name}.log"
    text_handler = RotatingFileHandler(
        text_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    text_handler.setLevel(logging.DEBUG)
    text_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    text_handler.setFormatter(text_formatter)
    logger.addHandler(text_handler)

    # File Handler - Error logs only
    error_file = log_path / f"{name}_errors.log"
    error_handler = RotatingFileHandler(
        error_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(text_formatter)
    logger.addHandler(error_handler)

    logger.info(f"Logger '{name}' initialized with level {log_level}")

    return logger


# Create default application logger
app_logger = setup_logger(
    name="backend-ai",
    log_level="DEBUG",
    enable_console=True,
    enable_json_logs=True
)


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (uses module name if None)

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"backend-ai.{name}")
    return app_logger


def log_function_call(logger: logging.Logger, func_name: str, **kwargs):
    """Log a function call with its parameters"""
    logger.debug(f"Calling {func_name}", extra={"extra_data": kwargs})


def log_database_query(logger: logging.Logger, query: str, params: Dict[str, Any] = None):
    """Log a database query"""
    logger.debug(
        f"Database query: {query}",
        extra={"extra_data": {"params": params}}
    )


def log_api_call(logger: logging.Logger, method: str, endpoint: str, status_code: int, duration: float):
    """Log an API call"""
    logger.info(
        f"{method} {endpoint} - {status_code} ({duration:.3f}s)",
        extra={"extra_data": {
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration": duration
        }}
    )


def log_error_with_context(logger: logging.Logger, error: Exception, context: Dict[str, Any] = None):
    """Log an error with additional context"""
    logger.error(
        f"Error occurred: {str(error)}",
        exc_info=True,
        extra={"extra_data": context or {}}
    )
