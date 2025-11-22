"""Conversation initialization service."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..core.state import AgentMessage, ConversationState, ConversationStateManager
from ..schemas.config import AgentConfig, InitializationConfig, RootConfig
from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class ConversationInitializer:
    """Service for initializing conversation state."""
    
    def __init__(self, config: RootConfig, scenario_name: Optional[str] = None):
        """
        Initialize conversation initializer.
        
        Args:
            config: Root configuration
            scenario_name: Optional scenario name to use (None = first/default)
        """
        self.config = config
        self.scenario_name = scenario_name
        self.conversation_config = config.get_conversation_config(scenario_name)
        self.prompt_builder = PromptBuilder()
    
    def create_initial_state(self) -> ConversationState:
        """
        Create initial conversation state with system prompts and first message.
        
        Returns:
            Initial conversation state ready for execution
        """
        logger.info("Creating initial conversation state")
        
        # Build system messages for each agent
        system_messages = self._build_system_messages()
        
        # Create first user message
        first_message = self._build_first_message()
        
        # Create initial state
        state = ConversationStateManager.create_initial_state(
            starting_agent=self.conversation_config.starting_agent,
            system_messages=system_messages,
            first_message=first_message
        )
        
        # Add configuration metadata
        state["metadata"]["config_version"] = self.config.version
        state["metadata"]["scenario_name"] = self.scenario_name
        state["metadata"]["max_cycles"] = self.conversation_config.max_cycles
        state["metadata"]["agents"] = list(self.config.agents.keys())
        
        logger.info(
            f"Initial state created with {len(system_messages)} system messages, "
            f"starting with agent '{self.conversation_config.starting_agent}'"
            f"{f' (scenario: {self.scenario_name})' if self.scenario_name else ''}"
        )
        
        return state
    
    def _build_system_messages(self) -> List[AgentMessage]:
        """
        Build system messages for all agents.
        
        Returns:
            List of system messages
        """
        system_messages = []
        
        # Get template from initialization config
        template = None
        if self.config.initialization.system_prompt_template:
            template = self.config.initialization.system_prompt_template
        
        # Build system message for each agent
        for agent_id, agent_config in self.config.agents.items():
            # Build system prompt
            system_prompt = self.prompt_builder.build_system_prompt(
                agent_config=agent_config,
                template=template,
                global_context={
                    "conversation": {
                        "max_cycles": self.conversation_config.max_cycles,
                        "starting_agent": self.conversation_config.starting_agent,
                        "goal": self.conversation_config.goal,
                        "brevity": self.conversation_config.brevity,
                        "scenario_name": self.scenario_name
                    }
                },
                available_tools=[]  # TODO: Add MCP tools when Phase 3 is implemented
            )
            
            # Create system message
            system_message = AgentMessage(
                content=system_prompt,
                agent_id=agent_id,
                timestamp=datetime.utcnow(),
                is_thought=False,
                message_type="system",
                metadata={
                    "agent_name": agent_config.name,
                    "purpose": "system_prompt"
                }
            )
            
            system_messages.append(system_message)
            
            # Log token count
            token_count = self.prompt_builder.count_tokens(system_prompt)
            logger.debug(
                f"System prompt for {agent_config.name}: "
                f"~{token_count} tokens"
            )
        
        return system_messages
    
    def _build_first_message(self) -> AgentMessage:
        """
        Build the first message to start the conversation.
        
        Returns:
            First message
        """
        first_message_content = self.config.initialization.first_message
        
        # Create message attributed to a virtual "user"
        first_message = AgentMessage(
            content=first_message_content,
            agent_id="user",
            timestamp=datetime.utcnow(),
            is_thought=False,
            message_type="human",
            metadata={
                "purpose": "conversation_starter"
            }
        )
        
        logger.debug(f"First message: {first_message_content[:100]}...")
        
        return first_message
    
    def validate_configuration(self) -> bool:
        """
        Validate that configuration is suitable for initialization.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Check that starting agent exists
        if self.conversation_config.starting_agent not in self.config.agents:
            raise ValueError(
                f"Starting agent '{self.conversation_config.starting_agent}' "
                f"not found in configured agents"
            )
        
        # Check that we have at least 2 agents
        if len(self.config.agents) < 2:
            raise ValueError("At least 2 agents required for conversation")
        
        # Check that first message exists
        if not self.config.initialization.first_message:
            raise ValueError("First message is required")
        
        # Validate agent configurations
        for agent_id, agent_config in self.config.agents.items():
            if not agent_config.name:
                raise ValueError(f"Agent {agent_id} must have a name")
            
            if not agent_config.persona:
                raise ValueError(f"Agent {agent_id} must have a persona")
            
            if not agent_config.model.url:
                raise ValueError(f"Agent {agent_id} must have a model URL")
            
            if not agent_config.model.model_name:
                raise ValueError(f"Agent {agent_id} must have a model name")
        
        logger.info("Configuration validation passed")
        return True
