"""Logging configuration for the application."""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

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


class WebSocketLogHandler(logging.Handler):
    """Logging handler that broadcasts logs to WebSocket clients."""
    
    def __init__(self, websocket_manager: Optional[Any] = None):
        """Initialize WebSocket log handler.
        
        Args:
            websocket_manager: WebSocket manager instance for broadcasting
        """
        super().__init__()
        self.websocket_manager = websocket_manager
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to WebSocket clients.
        
        Args:
            record: Log record to emit
        """
        if not self.websocket_manager:
            return
        
        try:
            # Determine log type based on logger name
            log_type = "debug_log"
            if "llm" in record.name.lower() or "ollama" in record.name.lower():
                log_type = "llm_log"
            
            # Extract agent_id if present in record
            agent_id = getattr(record, "agent_id", None)
            
            # Create log message
            log_message = {
                "type": log_type,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname.lower(),
                "message": record.getMessage(),
                "logger": record.name,
            }
            
            if agent_id:
                log_message["agent_id"] = agent_id
            
            # Broadcast asynchronously
            # We need to create a task since emit() is synchronous
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in current thread
                return
            
            if loop and loop.is_running():
                asyncio.create_task(self.websocket_manager.broadcast(log_message))
        
        except Exception:
            # Don't let logging errors break the application
            pass


def add_websocket_log_handler(websocket_manager: Any, log_level: str = "INFO") -> None:
    """Add WebSocket log handler to root logger.
    
    Args:
        websocket_manager: WebSocket manager instance
        log_level: Minimum log level to broadcast (default: INFO)
    """
    handler = WebSocketLogHandler(websocket_manager)
    handler.setLevel(getattr(logging, log_level))
    
    # Add to root logger
    logger = logging.getLogger()
    logger.addHandler(handler)
