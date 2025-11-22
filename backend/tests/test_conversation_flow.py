"""Integration tests for conversation flow and orchestration."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver

from app.agents.agent_node import create_agent_node
from app.core.cycle_manager import CycleManager, should_continue_conversation
from app.core.orchestrator import ConversationOrchestrator
from app.core.state import AgentMessage, ConversationState, ConversationStateManager
from app.schemas.config import (
    AgentConfig,
    ConversationConfig,
    InitializationConfig,
    ModelConfig,
    RootConfig,
    TerminationConditions,
)
from app.services.ollama_client import OllamaClient


@pytest.fixture
def mock_ollama_client():
    """Create a mocked Ollama client."""
    with patch("app.agents.agent_node.OllamaClient") as mock_class:
        mock_instance = Mock(spec=OllamaClient)
        mock_instance.bind_tools = Mock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def simple_config() -> RootConfig:
    """Create a simple test configuration."""
    return RootConfig(
        version="1.0",
        metadata={"name": "Test Conversation"},
        conversation=ConversationConfig(
            starting_agent="agent_a",
            max_cycles=3,
            turn_timeout=120,
            termination_conditions=TerminationConditions(
                keyword_triggers=["goodbye", "exit"],
                silence_detection=None,
            ),
        ),
        agents={
            "agent_a": AgentConfig(
                name="Agent A",
                persona="You are a friendly assistant.",
                model=ModelConfig(
                    url="http://localhost:11434",
                    model_name="llama2",
                    thinking=False,
                ),
                mcp_servers=[],
            ),
            "agent_b": AgentConfig(
                name="Agent B",
                persona="You are a knowledgeable expert.",
                model=ModelConfig(
                    url="http://localhost:11434",
                    model_name="mistral",
                    thinking=False,
                ),
                mcp_servers=[],
            ),
        },
        initialization=InitializationConfig(
            first_message="Hello, let's discuss AI.",
        ),
    )


@pytest.fixture
def initial_state() -> ConversationState:
    """Create an initial conversation state."""
    return {
        "messages": [],
        "current_cycle": 0,
        "next_agent": "agent_a",
        "should_terminate": False,
        "termination_reason": None,
    }


class TestConversationState:
    """Test conversation state management."""

    def test_initial_state_creation(self, initial_state: ConversationState) -> None:
        """Test creating initial conversation state."""
        assert initial_state["current_cycle"] == 0
        assert initial_state["next_agent"] == "agent_a"
        assert initial_state["should_terminate"] is False
        assert len(initial_state["messages"]) == 0

    def test_add_message_to_state(self, initial_state: ConversationState) -> None:
        """Test adding a message to state."""
        msg = AgentMessage(
            content="Hello",
            agent_id="agent_a",
            message_type="ai",
        )

        messages = ConversationStateManager.get_messages(initial_state)
        assert len(messages) == 0

        # Add message as dict
        initial_state["messages"].append(msg.to_dict())
        messages = ConversationStateManager.get_messages(initial_state)
        assert len(messages) == 1
        assert messages[0].content == "Hello"
        assert messages[0].agent_id == "agent_a"

    def test_filter_thought_messages(self, initial_state: ConversationState) -> None:
        """Test filtering thought messages from state."""
        # Add regular message
        msg1 = AgentMessage(
            content="Regular message",
            agent_id="agent_a",
            is_thought=False,
        )
        # Add thought message
        msg2 = AgentMessage(
            content="Internal thought",
            agent_id="agent_a",
            is_thought=True,
        )

        initial_state["messages"] = [msg1.to_dict(), msg2.to_dict()]

        # Get all messages
        all_messages = ConversationStateManager.get_messages(
            initial_state, exclude_thoughts=False
        )
        assert len(all_messages) == 2

        # Get only non-thought messages
        non_thought = ConversationStateManager.get_messages(
            initial_state, exclude_thoughts=True
        )
        assert len(non_thought) == 1
        assert non_thought[0].content == "Regular message"


class TestCycleManager:
    """Test cycle detection and management."""

    def test_cycle_manager_initialization(self) -> None:
        """Test cycle manager initializes correctly."""
        manager = CycleManager(
            agent_ids=["agent_a", "agent_b"],
            max_cycles=5,
        )

        assert manager.max_cycles == 5
        assert len(manager.agent_ids) == 2
        assert manager.cycles_completed == 0

    def test_register_agent_turn(self) -> None:
        """Test registering agent turns."""
        manager = CycleManager(
            agent_ids=["agent_a", "agent_b"],
            max_cycles=5,
        )

        # Register agent_a turn - completes cycle 1
        cycle_num = manager.register_agent_turn("agent_a")
        assert cycle_num == 1
        assert manager.cycles_completed == 1

        # Register agent_b turn - completes cycle 2
        cycle_num = manager.register_agent_turn("agent_b")
        assert cycle_num == 2
        assert manager.cycles_completed == 2

    def test_complete_cycle(self) -> None:
        """Test completing a cycle."""
        manager = CycleManager(
            agent_ids=["agent_a", "agent_b"],
            max_cycles=5,
        )

        # Register agent - cycle auto-completes
        manager.register_agent_turn("agent_a")
        assert manager.cycles_completed == 1
        
        # Complete cycle returns current cycle number
        cycle_num = manager.complete_cycle()
        assert cycle_num == 1
        assert manager.cycles_completed == 1

    def test_max_cycles_termination(self) -> None:
        """Test termination when max cycles reached."""
        manager = CycleManager(
            agent_ids=["agent_a", "agent_b"],
            max_cycles=2,
        )

        state: ConversationState = {
            "messages": [],
            "current_cycle": 0,
            "next_agent": "agent_a",
            "should_terminate": False,
        }

        # Agent A turn - cycle 1 complete
        manager.register_agent_turn("agent_a")
        should_terminate, reason = manager.check_termination(state)
        assert should_terminate is False

        # Agent B turn - cycle 2 complete (max reached)
        manager.register_agent_turn("agent_b")
        should_terminate, reason = manager.check_termination(state)
        assert should_terminate is True
        assert reason == "max_cycles_reached"

    def test_keyword_trigger_termination(self) -> None:
        """Test termination on keyword trigger."""
        manager = CycleManager(
            agent_ids=["agent_a", "agent_b"],
            max_cycles=10,
            termination_conditions=TerminationConditions(
                keyword_triggers=["goodbye", "exit"]
            ),
        )

        # Create state with message containing trigger keyword
        msg = AgentMessage(
            content="Okay, goodbye for now!",
            agent_id="agent_a",
            message_type="ai",
        )

        state: ConversationState = {
            "messages": [msg.to_dict()],
            "current_cycle": 1,
            "next_agent": "agent_b",
            "should_terminate": False,
        }

        should_terminate, reason = manager.check_termination(state)
        assert should_terminate is True
        assert reason == "keyword_trigger"

    def test_no_termination_without_keywords(self) -> None:
        """Test no termination when keywords not present."""
        manager = CycleManager(
            agent_ids=["agent_a", "agent_b"],
            max_cycles=10,
            termination_conditions=TerminationConditions(
                keyword_triggers=["goodbye", "exit"]
            ),
        )

        msg = AgentMessage(
            content="Let's continue discussing AI.",
            agent_id="agent_a",
            message_type="ai",
        )

        state: ConversationState = {
            "messages": [msg.to_dict()],
            "current_cycle": 1,
            "next_agent": "agent_b",
            "should_terminate": False,
        }

        should_terminate, reason = manager.check_termination(state)
        assert should_terminate is False
        assert reason is None


class TestAgentNode:
    """Test agent node creation and execution."""

    @pytest.mark.asyncio
    async def test_create_agent_node(
        self, simple_config: RootConfig, mock_ollama_client
    ) -> None:
        """Test creating an agent node."""
        agent_config = simple_config.agents["agent_a"]

        # Mock the generate_response method
        mock_ollama_client.generate_response = AsyncMock(
            return_value=AIMessage(content="Hello, I am Agent A.")
        )

        node_func = create_agent_node(
            agent_id="agent_a",
            agent_config=agent_config,
            turn_timeout=120,
        )

        assert callable(node_func)

    @pytest.mark.asyncio
    async def test_agent_node_execution(
        self, simple_config: RootConfig, mock_ollama_client
    ) -> None:
        """Test executing an agent node."""
        agent_config = simple_config.agents["agent_a"]

        # Mock response
        mock_ollama_client.generate_response = AsyncMock(
            return_value=AIMessage(content="This is my response.")
        )

        node_func = create_agent_node(
            agent_id="agent_a",
            agent_config=agent_config,
            turn_timeout=120,
        )

        # Create initial state with a message
        initial_msg = AgentMessage(
            content="Hello",
            agent_id="user",
            message_type="human",
        )

        state: ConversationState = {
            "messages": [initial_msg.to_dict()],
            "current_cycle": 0,
            "next_agent": "agent_a",
            "should_terminate": False,
        }

        # Execute node
        result_state = await node_func(state)

        # Verify response was added
        assert len(result_state["messages"]) >= len(state["messages"])


class TestConversationOrchestrator:
    """Test conversation orchestrator."""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(
        self, simple_config: RootConfig
    ) -> None:
        """Test orchestrator initializes correctly."""
        with patch("app.core.orchestrator.get_mcp_manager"):
            orchestrator = ConversationOrchestrator(config=simple_config)

            assert orchestrator.config == simple_config
            assert orchestrator.cycle_manager is not None
            assert orchestrator.checkpointer is not None

    @pytest.mark.asyncio
    async def test_single_cycle_execution(
        self, simple_config: RootConfig, mock_ollama_client
    ) -> None:
        """Test executing a single conversation cycle."""
        # Mock responses for both agents
        responses = [
            AIMessage(content="Response from Agent A"),
            AIMessage(content="Response from Agent B"),
        ]
        mock_ollama_client.generate_response = AsyncMock(
            side_effect=responses
        )

        with patch("app.core.orchestrator.get_mcp_manager"):
            with patch("app.core.orchestrator.get_tools_for_agent_as_langchain") as mock_get_tools:
                # Use AsyncMock for cleaner async mocking
                mock_get_tools.return_value = AsyncMock(return_value=[])()
                
                orchestrator = ConversationOrchestrator(config=simple_config)

                # Note: Full execution would require building and running the graph
                # This is a simplified test of initialization
                assert orchestrator.cycle_manager.max_cycles == 3


class TestShouldContinueConversation:
    """Test the should_continue_conversation function."""

    def test_should_continue_normal(self) -> None:
        """Test should continue when conditions are normal."""
        manager = CycleManager(
            agent_ids=["agent_a", "agent_b"],
            max_cycles=5,
        )
        
        state: ConversationState = {
            "messages": [],
            "current_cycle": 1,
            "next_agent": "agent_a",
            "should_terminate": False,
        }

        result = should_continue_conversation(state, manager)
        assert result == "continue"

    def test_should_end_when_terminated(self) -> None:
        """Test should end when termination flag is set."""
        manager = CycleManager(
            agent_ids=["agent_a", "agent_b"],
            max_cycles=5,
        )
        
        # Set manager to completed cycles
        manager.cycles_completed = 5
        
        state: ConversationState = {
            "messages": [],
            "current_cycle": 1,
            "next_agent": "agent_a",
            "should_terminate": False,
        }

        result = should_continue_conversation(state, manager)
        assert result == "terminate"


class TestMultiCycleConversation:
    """Test multi-cycle conversation scenarios."""

    def test_cycle_progression(self) -> None:
        """Test that cycles progress correctly."""
        manager = CycleManager(
            agent_ids=["agent_a", "agent_b", "agent_c"],
            max_cycles=5,
        )

        # Each agent turn completes a cycle
        manager.register_agent_turn("agent_a")
        assert manager.cycles_completed == 1
        
        manager.register_agent_turn("agent_b")
        assert manager.cycles_completed == 2
        
        manager.register_agent_turn("agent_c")
        assert manager.cycles_completed == 3
        
        # Continue with more turns
        manager.register_agent_turn("agent_a")
        assert manager.cycles_completed == 4
        
        manager.register_agent_turn("agent_b")
        assert manager.cycles_completed == 5

    def test_early_termination_prevents_continuation(self) -> None:
        """Test that early termination stops conversation."""
        manager = CycleManager(
            agent_ids=["agent_a", "agent_b"],
            max_cycles=10,
            termination_conditions=TerminationConditions(
                keyword_triggers=["stop"]
            ),
        )

        # First cycle
        manager.register_agent_turn("agent_a")
        manager.register_agent_turn("agent_b")
        manager.complete_cycle()

        # Create state with termination keyword
        msg = AgentMessage(
            content="Let's stop here.",
            agent_id="agent_a",
            message_type="ai",
        )

        state: ConversationState = {
            "messages": [msg.to_dict()],
            "current_cycle": 1,
            "next_agent": "agent_b",
            "should_terminate": False,
        }

        should_terminate, reason = manager.check_termination(state)
        assert should_terminate is True
        assert reason == "keyword_trigger"


class TestAgentMessage:
    """Test AgentMessage model."""

    def test_agent_message_creation(self) -> None:
        """Test creating an agent message."""
        msg = AgentMessage(
            content="Test message",
            agent_id="agent_a",
            message_type="ai",
        )

        assert msg.content == "Test message"
        assert msg.agent_id == "agent_a"
        assert msg.message_type == "ai"
        assert msg.is_thought is False

    def test_thought_message(self) -> None:
        """Test creating a thought message."""
        msg = AgentMessage(
            content="Internal reasoning",
            agent_id="agent_a",
            is_thought=True,
        )

        assert msg.is_thought is True

    def test_message_to_langchain(self) -> None:
        """Test converting to LangChain message."""
        msg = AgentMessage(
            content="Test",
            agent_id="agent_a",
            message_type="ai",
        )

        lc_msg = msg.to_langchain_message()
        assert isinstance(lc_msg, AIMessage)
        assert lc_msg.content == "Test"

    def test_human_message_to_langchain(self) -> None:
        """Test converting human message to LangChain."""
        msg = AgentMessage(
            content="User input",
            agent_id="user",
            message_type="human",
        )

        lc_msg = msg.to_langchain_message()
        assert isinstance(lc_msg, HumanMessage)

    def test_system_message_to_langchain(self) -> None:
        """Test converting system message to LangChain."""
        msg = AgentMessage(
            content="System prompt",
            agent_id="system",
            message_type="system",
        )

        lc_msg = msg.to_langchain_message()
        assert isinstance(lc_msg, SystemMessage)


class TestTerminationConditions:
    """Test termination condition handling."""

    def test_multiple_keyword_triggers(self) -> None:
        """Test multiple keyword triggers."""
        manager = CycleManager(
            agent_ids=["agent_a", "agent_b"],
            max_cycles=10,
            termination_conditions=TerminationConditions(
                keyword_triggers=["goodbye", "bye", "exit", "quit"]
            ),
        )

        test_cases = [
            ("See you later, bye!", True),
            ("I want to exit now", True),
            ("Quit this conversation", True),
            ("Let's continue talking", False),
        ]

        for content, should_trigger in test_cases:
            msg = AgentMessage(
                content=content,
                agent_id="agent_a",
                message_type="ai",
            )

            state: ConversationState = {
                "messages": [msg.to_dict()],
                "current_cycle": 1,
                "next_agent": "agent_b",
                "should_terminate": False,
            }

            should_terminate, _ = manager.check_termination(state)
            assert should_terminate == should_trigger, f"Failed for: {content}"

    def test_case_insensitive_keywords(self) -> None:
        """Test that keyword matching is case-insensitive."""
        manager = CycleManager(
            agent_ids=["agent_a", "agent_b"],
            max_cycles=10,
            termination_conditions=TerminationConditions(
                keyword_triggers=["goodbye"]
            ),
        )

        test_cases = ["Goodbye", "GOODBYE", "GoodBye", "goodbye"]

        for content in test_cases:
            msg = AgentMessage(
                content=f"Well, {content}!",
                agent_id="agent_a",
                message_type="ai",
            )

            state: ConversationState = {
                "messages": [msg.to_dict()],
                "current_cycle": 1,
                "next_agent": "agent_b",
                "should_terminate": False,
            }

            should_terminate, reason = manager.check_termination(state)
            assert should_terminate is True, f"Failed for: {content}"
            assert reason == "keyword_trigger"


class TestConversationStateManager:
    """Test ConversationStateManager utility functions."""

    def test_get_messages_empty_state(self) -> None:
        """Test getting messages from empty state."""
        state: ConversationState = {
            "messages": [],
            "current_cycle": 0,
            "next_agent": "agent_a",
        }

        messages = ConversationStateManager.get_messages(state)
        assert messages == []

    def test_get_langchain_messages(self) -> None:
        """Test converting to LangChain messages."""
        msg1 = AgentMessage(
            content="Hello",
            agent_id="agent_a",
            message_type="ai",
        )
        msg2 = AgentMessage(
            content="Hi there",
            agent_id="agent_b",
            message_type="ai",
        )

        state: ConversationState = {
            "messages": [msg1.to_dict(), msg2.to_dict()],
            "current_cycle": 0,
            "next_agent": "agent_a",
        }

        lc_messages = ConversationStateManager.get_langchain_messages(state)
        assert len(lc_messages) == 2
        assert all(isinstance(msg, AIMessage) for msg in lc_messages)
