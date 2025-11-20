"""Configuration schemas using Pydantic models for runtime validation."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator
import re


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ModelConfig(BaseModel):
    """Configuration for an LLM model."""
    provider: str = Field(default="ollama", description="LLM provider (e.g., ollama)")
    url: str = Field(..., description="Ollama API endpoint URL")
    model_name: str = Field(..., description="Model name (e.g., llama2, mistral)")
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Model-specific parameters (temperature, top_p, etc.)"
    )
    thinking: bool = Field(
        default=False,
        description="Enable thought suppression for internal reasoning"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name format."""
        if not re.match(r"^[a-zA-Z0-9_\-.:]+$", v):
            raise ValueError("Model name can only contain alphanumeric characters, _, -, ., and :")
        return v


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server."""
    name: str = Field(..., description="Unique name for the MCP server")
    command: str = Field(..., description="Command to start the server")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for the server"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate server name format."""
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError("Server name can only contain alphanumeric characters, _, and -")
        return v


class AgentConfig(BaseModel):
    """Configuration for an AI agent."""
    name: str = Field(..., description="Agent display name")
    persona: str = Field(..., description="System prompt defining agent personality")
    model: ModelConfig = Field(..., description="Model configuration for this agent")
    mcp_servers: List[str] = Field(
        default_factory=list,
        description="List of agent-specific MCP server names"
    )


class TerminationConditions(BaseModel):
    """Conditions that terminate a conversation."""
    keyword_triggers: List[str] = Field(
        default_factory=list,
        description="Keywords that trigger immediate termination"
    )
    silence_detection: Optional[int] = Field(
        default=None,
        description="Number of cycles with no substantive content before terminating"
    )


class ConversationConfig(BaseModel):
    """Configuration for conversation orchestration."""
    starting_agent: str = Field(..., description="ID of agent that starts the conversation")
    max_cycles: int = Field(
        default=10,
        ge=1,
        description="Maximum number of conversation cycles"
    )
    turn_timeout: int = Field(
        default=300,
        ge=1,
        description="Timeout in seconds for each agent turn"
    )
    termination_conditions: Optional[TerminationConditions] = Field(
        default_factory=TerminationConditions,
        description="Conditions for ending conversation"
    )


class InitializationConfig(BaseModel):
    """Configuration for conversation initialization."""
    system_prompt_template: Optional[str] = Field(
        default=None,
        description="Jinja2 template for system prompt"
    )
    first_message: str = Field(
        ...,
        description="Initial message to start the conversation"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    include_thoughts: bool = Field(
        default=True,
        description="Include thought streams in logs"
    )
    output_directory: Optional[str] = Field(
        default=None,
        description="Directory for log files"
    )


class MCPServersConfig(BaseModel):
    """Configuration for MCP servers."""
    global_servers: List[MCPServerConfig] = Field(
        default_factory=list,
        description="MCP servers available to all agents"
    )


class RootConfig(BaseModel):
    """Root configuration for the entire application."""
    version: str = Field(default="1.0", description="Configuration schema version")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Arbitrary metadata"
    )
    conversation: ConversationConfig = Field(..., description="Conversation settings")
    agents: Dict[str, AgentConfig] = Field(
        ...,
        description="Agent configurations keyed by agent ID"
    )
    mcp_servers: MCPServersConfig = Field(
        default_factory=MCPServersConfig,
        description="MCP server configurations"
    )
    initialization: InitializationConfig = Field(
        ...,
        description="Initialization settings"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )

    @field_validator("agents")
    @classmethod
    def validate_agents(cls, v: Dict[str, AgentConfig]) -> Dict[str, AgentConfig]:
        """Validate that at least two agents are configured."""
        if len(v) < 2:
            raise ValueError("At least two agents must be configured")
        return v

    def validate_starting_agent(self) -> None:
        """Validate that starting_agent exists in agents."""
        if self.conversation.starting_agent not in self.agents:
            raise ValueError(
                f"Starting agent '{self.conversation.starting_agent}' not found in agents"
            )
