"""LangGraph state definitions and message types for conversation management."""

import json
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict
from uuid import uuid4

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    """Extended message with agent metadata."""
    
    content: str = Field(..., description="Message content")
    agent_id: str = Field(..., description="ID of the agent that generated this message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When message was created")
    is_thought: bool = Field(default=False, description="Whether this is internal reasoning")
    message_type: Literal["human", "ai", "system", "tool", "cycle_marker"] = Field(
        default="ai",
        description="Type of message"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_langchain_message(self) -> BaseMessage:
        """
        Convert to LangChain message.
        
        Returns:
            Appropriate LangChain message type
        """
        kwargs = {
            "content": self.content,
            "additional_kwargs": {
                "agent_id": self.agent_id,
                "timestamp": self.timestamp.isoformat(),
                "is_thought": self.is_thought,
                **self.metadata
            }
        }
        
        if self.message_type == "human":
            return HumanMessage(**kwargs)
        elif self.message_type == "system":
            return SystemMessage(**kwargs)
        else:
            return AIMessage(**kwargs)
    
    @classmethod
    def from_langchain_message(cls, msg: BaseMessage, agent_id: str) -> "AgentMessage":
        """
        Create from LangChain message.
        
        Args:
            msg: LangChain message
            agent_id: Agent ID to associate with message
            
        Returns:
            AgentMessage instance
        """
        # Determine message type
        if isinstance(msg, HumanMessage):
            msg_type = "human"
        elif isinstance(msg, SystemMessage):
            msg_type = "system"
        else:
            msg_type = "ai"
        
        # Extract metadata
        additional_kwargs = getattr(msg, "additional_kwargs", {})
        is_thought = additional_kwargs.get("is_thought", False)
        timestamp_str = additional_kwargs.get("timestamp")
        
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str)
        else:
            timestamp = datetime.utcnow()
        
        return cls(
            content=msg.content,
            agent_id=agent_id,
            timestamp=timestamp,
            is_thought=is_thought,
            message_type=msg_type,
            metadata=additional_kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "is_thought": self.is_thought,
            "message_type": self.message_type,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Create from dictionary."""
        data = data.copy()
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class ConversationState(TypedDict):
    """
    State structure for LangGraph conversation management.
    
    This defines the state that flows through the conversation graph.
    """
    
    messages: List[Dict[str, Any]]  # List of message dictionaries
    current_cycle: int  # Current conversation cycle number
    next_agent: str  # ID of agent who should respond next
    metadata: Dict[str, Any]  # Additional state metadata
    should_terminate: bool  # Whether conversation should end
    termination_reason: Optional[str]  # Why conversation ended


class CycleMarker(BaseModel):
    """Marker for conversation cycle boundaries."""
    
    cycle_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agents_completed: List[str] = Field(default_factory=list)
    
    def to_message(self) -> AgentMessage:
        """Convert to AgentMessage for storage."""
        return AgentMessage(
            content=f"--- Cycle {self.cycle_number} Complete ---",
            agent_id="system",
            timestamp=self.timestamp,
            message_type="cycle_marker",
            metadata={
                "cycle_number": self.cycle_number,
                "agents_completed": self.agents_completed
            }
        )


class ConversationStateManager:
    """Helper class for managing conversation state."""
    
    @staticmethod
    def create_initial_state(
        starting_agent: str,
        system_messages: Optional[List[AgentMessage]] = None,
        first_message: Optional[AgentMessage] = None
    ) -> ConversationState:
        """
        Create initial conversation state.
        
        Args:
            starting_agent: ID of agent that starts conversation
            system_messages: Optional system messages to include
            first_message: Optional first message to seed conversation
            
        Returns:
            Initial conversation state
        """
        messages = []
        
        # Add system messages if provided
        if system_messages:
            messages.extend([msg.to_dict() for msg in system_messages])
        
        # Add first message if provided
        if first_message:
            messages.append(first_message.to_dict())
        
        return ConversationState(
            messages=messages,
            current_cycle=0,
            next_agent=starting_agent,
            metadata={
                "conversation_id": str(uuid4()),
                "started_at": datetime.utcnow().isoformat()
            },
            should_terminate=False,
            termination_reason=None
        )
    
    @staticmethod
    def add_message(state: ConversationState, message: AgentMessage) -> ConversationState:
        """
        Add a message to the conversation state.
        
        Args:
            state: Current conversation state
            message: Message to add
            
        Returns:
            Updated state
        """
        state["messages"].append(message.to_dict())
        return state
    
    @staticmethod
    def get_messages(state: ConversationState, exclude_thoughts: bool = False) -> List[AgentMessage]:
        """
        Get messages from state.
        
        Args:
            state: Conversation state
            exclude_thoughts: Whether to exclude thought messages
            
        Returns:
            List of AgentMessage objects
        """
        messages = [AgentMessage.from_dict(msg) for msg in state["messages"]]
        
        if exclude_thoughts:
            messages = [msg for msg in messages if not msg.is_thought]
        
        return messages
    
    @staticmethod
    def get_langchain_messages(state: ConversationState) -> List[BaseMessage]:
        """
        Convert state messages to LangChain format.
        
        Args:
            state: Conversation state
            
        Returns:
            List of LangChain messages
        """
        agent_messages = ConversationStateManager.get_messages(state, exclude_thoughts=True)
        return [msg.to_langchain_message() for msg in agent_messages]
    
    @staticmethod
    def increment_cycle(state: ConversationState) -> ConversationState:
        """
        Increment the cycle counter.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        state["current_cycle"] += 1
        return state
    
    @staticmethod
    def mark_cycle_complete(
        state: ConversationState,
        agents_completed: List[str]
    ) -> ConversationState:
        """
        Mark a cycle as complete.
        
        Args:
            state: Current state
            agents_completed: List of agent IDs that completed this cycle
            
        Returns:
            Updated state
        """
        marker = CycleMarker(
            cycle_number=state["current_cycle"],
            agents_completed=agents_completed
        )
        state["messages"].append(marker.to_message().to_dict())
        return state
    
    @staticmethod
    def set_termination(
        state: ConversationState,
        reason: str
    ) -> ConversationState:
        """
        Mark conversation for termination.
        
        Args:
            state: Current state
            reason: Reason for termination
            
        Returns:
            Updated state
        """
        state["should_terminate"] = True
        state["termination_reason"] = reason
        return state
    
    @staticmethod
    def serialize_state(state: ConversationState) -> str:
        """
        Serialize state to JSON.
        
        Args:
            state: Conversation state
            
        Returns:
            JSON string
        """
        return json.dumps(dict(state), default=str)
    
    @staticmethod
    def deserialize_state(json_str: str) -> ConversationState:
        """
        Deserialize state from JSON.
        
        Args:
            json_str: JSON string
            
        Returns:
            Conversation state
        """
        data = json.loads(json_str)
        return ConversationState(**data)
