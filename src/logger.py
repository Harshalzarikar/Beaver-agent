"""
Structured logging configuration with JSON support and correlation IDs.
"""
import logging
import sys
from typing import Any
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar

from src.config import settings


# Context variable for correlation ID (trace_id)
correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id.get() or "N/A"
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""
    
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        
        # Add correlation ID if present
        if hasattr(record, "correlation_id"):
            log_record["correlation_id"] = record.correlation_id
        
        # Add environment
        log_record["environment"] = settings.environment


def setup_logging() -> logging.Logger:
    """
    Configure application logging based on settings.
    
    Returns:
        Configured root logger
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter based on configuration
    if settings.log_format == "json":
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    handler.setFormatter(formatter)
    
    # Add correlation ID filter
    handler.addFilter(CorrelationIdFilter())
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def set_correlation_id(trace_id: str | None):
    """
    Set correlation ID for current context.
    
    Args:
        trace_id: Trace/correlation ID to set
    """
    correlation_id.set(trace_id)


def get_correlation_id() -> str | None:
    """
    Get current correlation ID.
    
    Returns:
        Current correlation ID or None
    """
    return correlation_id.get()


# Initialize logging on module import
setup_logging()
