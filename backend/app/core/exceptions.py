"""Custom exceptions for the AI Agent Mixer application."""

from typing import Any, Dict, Optional


class AIAgentMixerException(Exception):
    """Base exception for all AI Agent Mixer errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        """
        Initialize exception.

        Args:
            message: Human-readable error message
            details: Additional context about the error
            status_code: HTTP status code for API responses
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.status_code = status_code


class ConfigurationError(AIAgentMixerException):
    """Exception raised for configuration-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, status_code=400)


class InvalidConfigError(ConfigurationError):
    """Exception raised when configuration validation fails."""

    pass


class ConfigFileNotFoundError(ConfigurationError):
    """Exception raised when configuration file is not found."""

    def __init__(self, filepath: str):
        super().__init__(
            f"Configuration file not found: {filepath}",
            details={"filepath": filepath},
        )


class OllamaConnectionError(AIAgentMixerException):
    """Exception raised when connection to Ollama fails."""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        model: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if url:
            error_details["url"] = url
        if model:
            error_details["model"] = model

        super().__init__(message, error_details, status_code=503)


class OllamaModelNotFoundError(OllamaConnectionError):
    """Exception raised when specified Ollama model is not available."""

    def __init__(self, model: str, url: str):
        super().__init__(
            f"Model '{model}' not found on Ollama server",
            url=url,
            model=model,
        )


class OllamaTimeoutError(OllamaConnectionError):
    """Exception raised when Ollama request times out."""

    def __init__(self, timeout: int, url: str):
        super().__init__(
            f"Ollama request timed out after {timeout} seconds",
            url=url,
            details={"timeout": timeout},
        )


class MCPServerError(AIAgentMixerException):
    """Base exception for MCP server-related errors."""

    def __init__(
        self,
        message: str,
        server_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if server_name:
            error_details["server_name"] = server_name

        super().__init__(message, error_details, status_code=500)


class MCPStartupError(MCPServerError):
    """Exception raised when MCP server fails to start."""

    def __init__(self, server_name: str, reason: str):
        super().__init__(
            f"Failed to start MCP server '{server_name}': {reason}",
            server_name=server_name,
            details={"reason": reason},
        )


class MCPConnectionError(MCPServerError):
    """Exception raised when connection to MCP server fails."""

    def __init__(self, server_name: str, reason: str):
        super().__init__(
            f"Failed to connect to MCP server '{server_name}': {reason}",
            server_name=server_name,
            details={"reason": reason},
        )


class MCPToolExecutionError(MCPServerError):
    """Exception raised when MCP tool execution fails."""

    def __init__(
        self,
        tool_name: str,
        server_name: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        error_details["tool_name"] = tool_name
        error_details["reason"] = reason

        super().__init__(
            f"Tool '{tool_name}' execution failed on server '{server_name}': {reason}",
            server_name=server_name,
            details=error_details,
        )


class AgentExecutionError(AIAgentMixerException):
    """Exception raised when agent execution fails."""

    def __init__(
        self,
        agent_id: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        error_details["agent_id"] = agent_id

        super().__init__(
            f"Agent '{agent_id}' execution failed: {message}",
            error_details,
            status_code=500,
        )


class AgentTimeoutError(AgentExecutionError):
    """Exception raised when agent execution times out."""

    def __init__(self, agent_id: str, timeout: int):
        super().__init__(
            agent_id,
            f"timed out after {timeout} seconds",
            details={"timeout": timeout},
        )


class ConversationStateError(AIAgentMixerException):
    """Exception raised for conversation state-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, status_code=500)


class WebSocketError(AIAgentMixerException):
    """Exception raised for WebSocket-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, status_code=500)


class ValidationError(AIAgentMixerException):
    """Exception raised for input validation errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, status_code=422)
