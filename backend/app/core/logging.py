"""Logging configuration for the application."""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict

from app.schemas.config import LogLevel


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data)


def setup_logging(level: LogLevel = LogLevel.INFO, output_directory: str = None) -> None:
    """Configure application logging.
    
    Args:
        level: Logging level
        output_directory: Optional directory for log files
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(level.value)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # File handler if output directory is specified
    if output_directory:
        from pathlib import Path
        log_dir = Path(output_directory)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"app_{datetime.utcnow().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    
    # Silence some noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
