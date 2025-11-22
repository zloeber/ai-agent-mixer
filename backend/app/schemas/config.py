"""Configuration schemas using Pydantic models for runtime validation."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
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
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata attributes for use in templates and prompts"
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


class ConversationScenario(BaseModel):
    """Configuration for a single conversation scenario."""
    name: str = Field(..., description="Name of the conversation scenario")
    goal: Optional[str] = Field(None, description="Goal or description of the conversation")
    brevity: str = Field(
        default="low",
        description="Response brevity level: low, medium, or high"
    )
    agents_involved: Optional[List[str]] = Field(
        default=None,
        description="List of agent IDs involved in this conversation (None = all agents)"
    )
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

    @field_validator("brevity")
    @classmethod
    def validate_brevity(cls, v: str) -> str:
        """Validate brevity level."""
        if v.lower() not in ["low", "medium", "high"]:
            raise ValueError("Brevity must be 'low', 'medium', or 'high'")
        return v.lower()


class ConversationConfig(BaseModel):
    """Configuration for conversation orchestration (legacy single conversation)."""
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
    goal: Optional[str] = Field(
        default=None,
        description="Goal or description of the conversation"
    )
    brevity: str = Field(
        default="low",
        description="Response brevity level: low, medium, or high"
    )
    agents_involved: Optional[List[str]] = Field(
        default=None,
        description="List of agent IDs involved in this conversation (None = all agents)"
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
    conversation: Optional[ConversationConfig] = Field(
        None,
        description="Legacy single conversation settings (deprecated, use conversations instead)"
    )
    conversations: Optional[List[ConversationScenario]] = Field(
        None,
        description="List of conversation scenarios to choose from"
    )
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
    
    @model_validator(mode='after')
    def validate_conversation_config(self) -> 'RootConfig':
        """Validate that at least one of conversation or conversations is provided."""
        if not self.conversation and not self.conversations:
            raise ValueError("Either 'conversation' or 'conversations' must be provided")
        return self
    
    def get_conversation_config(self, scenario_name: Optional[str] = None) -> ConversationConfig:
        """Get conversation config, either from scenarios or legacy single conversation.
        
        Args:
            scenario_name: Name of scenario to use, or None for first/default
            
        Returns:
            ConversationConfig instance
        """
        if self.conversations:
            if scenario_name:
                # Find specific scenario
                for scenario in self.conversations:
                    if scenario.name == scenario_name:
                        return self._scenario_to_config(scenario)
                raise ValueError(f"Scenario '{scenario_name}' not found")
            else:
                # Use first scenario
                return self._scenario_to_config(self.conversations[0])
        elif self.conversation:
            # Use legacy conversation
            return self.conversation
        else:
            raise ValueError("No conversation or conversations configured")
    
    def _scenario_to_config(self, scenario: ConversationScenario) -> ConversationConfig:
        """Convert a scenario to a ConversationConfig."""
        return ConversationConfig(
            starting_agent=scenario.starting_agent,
            max_cycles=scenario.max_cycles,
            turn_timeout=scenario.turn_timeout,
            termination_conditions=scenario.termination_conditions or TerminationConditions(),
            goal=scenario.goal,
            brevity=scenario.brevity,
            agents_involved=scenario.agents_involved
        )
    
    def list_scenarios(self) -> List[str]:
        """Get list of available scenario names."""
        if self.conversations:
            return [s.name for s in self.conversations]
        return []

    @field_validator("agents")
    @classmethod
    def validate_agents(cls, v: Dict[str, AgentConfig]) -> Dict[str, AgentConfig]:
        """Validate that at least two agents are configured."""
        if len(v) < 2:
            raise ValueError("At least two agents must be configured")
        return v

    def validate_starting_agent(self, scenario_name: Optional[str] = None) -> None:
        """Validate that starting_agent exists in agents for given scenario or default conversation.
        
        Args:
            scenario_name: Name of scenario to validate, or None for first/default
        """
        if self.conversations:
            scenarios_to_check = self.conversations if not scenario_name else [
                s for s in self.conversations if s.name == scenario_name
            ]
            for scenario in scenarios_to_check:
                if scenario.starting_agent not in self.agents:
                    raise ValueError(
                        f"Starting agent '{scenario.starting_agent}' in scenario '{scenario.name}' not found in agents"
                    )
                # Validate agents_involved if specified
                if scenario.agents_involved:
                    for agent_id in scenario.agents_involved:
                        if agent_id not in self.agents:
                            raise ValueError(
                                f"Agent '{agent_id}' in scenario '{scenario.name}' not found in agents"
                            )
        elif self.conversation:
            if self.conversation.starting_agent not in self.agents:
                raise ValueError(
                    f"Starting agent '{self.conversation.starting_agent}' not found in agents"
                )
        else:
            # This should have been caught by model validator, but be defensive
            raise ValueError("No conversation or conversations configured")
