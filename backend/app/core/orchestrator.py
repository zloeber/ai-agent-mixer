"""Conversation orchestrator using LangGraph for multi-agent conversations."""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Literal, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .cycle_manager import CycleManager, should_continue_conversation
from .state import ConversationState, ConversationStateManager
from ..agents.agent_node import create_agent_node
from ..schemas.config import RootConfig
from ..services.initializer import ConversationInitializer
from ..services.mcp_manager import get_mcp_manager
from ..services.tool_adapter import get_tools_for_agent_as_langchain

logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    """
    Orchestrator for managing multi-agent conversations using LangGraph.
    
    This class builds and manages the LangGraph workflow that coordinates
    turn-taking between agents, tracks cycles, and handles termination.
    """
    
    def __init__(
        self,
        config: RootConfig,
        websocket_manager: Optional[Any] = None,
        thought_callback: Optional[Callable[[str, str], None]] = None
    ):
        """
        Initialize conversation orchestrator.
        
        Args:
            config: Root configuration for the conversation
            websocket_manager: Optional WebSocket manager for real-time updates
            thought_callback: Optional callback for thought messages
        """
        self.config = config
        self.websocket_manager = websocket_manager
        self.thought_callback = thought_callback
        
        # Initialize components
        self.initializer = ConversationInitializer(config)
        self.cycle_manager = CycleManager(
            agent_ids=list(config.agents.keys()),
            max_cycles=config.conversation.max_cycles,
            termination_conditions=config.conversation.termination_conditions
        )
        
        # Build the graph
        self.graph = None
        self.checkpointer = MemorySaver()  # For state persistence
        self.agent_tools: Dict[str, List[Any]] = {}  # Tools for each agent
        self._build_graph()
        
        logger.info(f"ConversationOrchestrator initialized with {len(config.agents)} agents")
    
    async def _initialize_agent_mcp_servers(self) -> None:
        """Initialize MCP servers for each agent."""
        mcp_manager = get_mcp_manager()
        
        for agent_id, agent_config in self.config.agents.items():
            if agent_config.mcp_servers:
                logger.info(f"Starting {len(agent_config.mcp_servers)} MCP servers for agent {agent_id}")
                for server_name in agent_config.mcp_servers:
                    # Find the server config - check if it's a global server first
                    server_config = None
                    for global_server in self.config.mcp_servers.global_servers:
                        if global_server.name == server_name:
                            # This is a reference to a global server, skip
                            logger.debug(f"Agent {agent_id} references global server {server_name}")
                            continue
                    
                    # If not found in global, it might be defined elsewhere or should be agent-scoped
                    # For now, we'll log a warning if not found
                    if not server_config:
                        logger.warning(f"MCP server {server_name} referenced by agent {agent_id} but not found in configuration")
    
    async def _load_agent_tools(self) -> None:
        """Load tools for each agent from MCP servers."""
        mcp_manager = get_mcp_manager()
        
        for agent_id, agent_config in self.config.agents.items():
            # Get global server names
            global_server_names = [s.name for s in self.config.mcp_servers.global_servers]
            
            # Get agent-specific server names
            agent_server_names = agent_config.mcp_servers
            
            # Get tools as LangChain BaseTool instances
            tools = await get_tools_for_agent_as_langchain(
                agent_id=agent_id,
                global_server_names=global_server_names,
                agent_server_names=agent_server_names
            )
            
            self.agent_tools[agent_id] = tools
            logger.info(f"Loaded {len(tools)} tools for agent {agent_id}")
    
    def _build_graph(self) -> None:
        """Build the LangGraph workflow."""
        logger.info("Building conversation graph")
        
        # Create state graph
        workflow = StateGraph(ConversationState)
        
        # Add agent nodes
        for agent_id, agent_config in self.config.agents.items():
            # Get tools for this agent (may be empty initially)
            tools = self.agent_tools.get(agent_id, [])
            
            node_func = create_agent_node(
                agent_id=agent_id,
                agent_config=agent_config,
                turn_timeout=self.config.conversation.turn_timeout,
                websocket_manager=self.websocket_manager,
                thought_callback=self.thought_callback,
                tools=tools
            )
            workflow.add_node(agent_id, node_func)
            logger.debug(f"Added agent node: {agent_id} with {len(tools)} tools")
        
        # Add cycle check node
        workflow.add_node("cycle_check", self._cycle_check_node)
        
        # Set entry point based on starting agent
        workflow.set_entry_point(self.config.conversation.starting_agent)
        logger.debug(f"Entry point: {self.config.conversation.starting_agent}")
        
        # Add edges from agents to cycle check
        for agent_id in self.config.agents.keys():
            workflow.add_edge(agent_id, "cycle_check")
        
        # Add conditional edge from cycle check
        workflow.add_conditional_edges(
            "cycle_check",
            self._route_next_agent,
            {
                "terminate": END,
                **{agent_id: agent_id for agent_id in self.config.agents.keys()}
            }
        )
        
        # Compile graph with checkpointer
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        logger.info("Conversation graph compiled successfully")
    
    def _cycle_check_node(self, state: ConversationState) -> ConversationState:
        """
        Node that checks cycle completion and termination conditions.
        
        Args:
            state: Current conversation state
            
        Returns:
            Updated state
        """
        # Get the last message to determine which agent just spoke
        messages = ConversationStateManager.get_messages(state)
        if messages:
            last_message = messages[-1]
            if last_message.agent_id in self.config.agents:
                # Register agent turn
                self.cycle_manager.register_agent_turn(last_message.agent_id)
        
        # Check if cycle is complete
        if self.cycle_manager.is_cycle_complete():
            cycle_num = self.cycle_manager.complete_cycle()
            
            # Mark cycle as complete in state
            state = ConversationStateManager.mark_cycle_complete(
                state,
                list(self.config.agents.keys())
            )
            
            # Update cycle count in state
            state["current_cycle"] = cycle_num
            
            logger.info(f"Cycle {cycle_num} marked complete")
        
        # Check termination conditions
        should_terminate, reason = self.cycle_manager.check_termination(state)
        if should_terminate:
            state = ConversationStateManager.set_termination(state, reason)
            logger.info(f"Conversation marked for termination: {reason}")
        
        return state
    
    def _route_next_agent(self, state: ConversationState) -> str:
        """
        Route to next agent or terminate.
        
        Args:
            state: Current conversation state
            
        Returns:
            Agent ID to route to, or "terminate"
        """
        # Check if should terminate
        if state.get("should_terminate", False):
            logger.info(f"Routing to termination: {state.get('termination_reason')}")
            return "terminate"
        
        # Get current agent from last message
        messages = ConversationStateManager.get_messages(state)
        if not messages:
            # No messages yet, use starting agent
            next_agent = self.config.conversation.starting_agent
        else:
            # Find last non-system message to determine current agent
            current_agent = None
            for msg in reversed(messages):
                if msg.agent_id in self.config.agents:
                    current_agent = msg.agent_id
                    break
            
            if current_agent is None:
                # Fallback to starting agent
                next_agent = self.config.conversation.starting_agent
            else:
                # Alternate to next agent (simple round-robin for 2 agents)
                agent_ids = list(self.config.agents.keys())
                current_idx = agent_ids.index(current_agent)
                next_idx = (current_idx + 1) % len(agent_ids)
                next_agent = agent_ids[next_idx]
        
        # Update state with next agent
        state["next_agent"] = next_agent
        
        logger.debug(f"Routing to agent: {next_agent}")
        return next_agent
    
    async def start_conversation(self) -> Dict[str, Any]:
        """
        Start a new conversation.
        
        Returns:
            Dictionary with conversation metadata
        """
        logger.info("Starting new conversation")
        
        # Validate configuration
        self.initializer.validate_configuration()
        
        # Initialize agent MCP servers if needed
        await self._initialize_agent_mcp_servers()
        
        # Load tools for agents
        await self._load_agent_tools()
        
        # Rebuild graph with tools (only if tools were loaded)
        if any(len(tools) > 0 for tools in self.agent_tools.values()):
            logger.info("Rebuilding graph with loaded tools")
            self._build_graph()
        
        # Create initial state
        initial_state = self.initializer.create_initial_state()
        
        # Reset cycle manager
        self.cycle_manager.reset()
        
        # Store initial state
        self.current_state = initial_state
        
        # Broadcast conversation started event
        if self.websocket_manager:
            try:
                await self.websocket_manager.broadcast({
                    "type": "conversation_started",
                    "conversation_id": initial_state["metadata"]["conversation_id"],
                    "max_cycles": self.config.conversation.max_cycles,
                    "starting_agent": self.config.conversation.starting_agent,
                    "agents": list(self.config.agents.keys())
                })
            except Exception as e:
                logger.error(f"Error broadcasting conversation start: {e}")
        
        return {
            "conversation_id": initial_state["metadata"]["conversation_id"],
            "started_at": initial_state["metadata"]["started_at"],
            "agents": list(self.config.agents.keys()),
            "max_cycles": self.config.conversation.max_cycles
        }
    
    async def run_conversation(self, thread_id: str = "default") -> ConversationState:
        """
        Run the complete conversation.
        
        Args:
            thread_id: Thread identifier for checkpointing
            
        Returns:
            Final conversation state
        """
        logger.info(f"Running conversation (thread: {thread_id})")
        
        # Get initial state
        state = self.current_state
        
        # Configure for async execution
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        try:
            # Run the graph
            final_state = await self.graph.ainvoke(state, config)
            
            # Broadcast conversation ended event
            if self.websocket_manager:
                try:
                    await self.websocket_manager.broadcast({
                        "type": "conversation_ended",
                        "reason": final_state.get("termination_reason"),
                        "cycles_completed": final_state["current_cycle"],
                        "message_count": len(final_state["messages"])
                    })
                except Exception as e:
                    logger.error(f"Error broadcasting conversation end: {e}")
            
            logger.info(
                f"Conversation completed: {final_state.get('termination_reason')} "
                f"after {final_state['current_cycle']} cycles"
            )
            
            return final_state
            
        except Exception as e:
            logger.error(f"Error running conversation: {e}", exc_info=True)
            
            # Broadcast error
            if self.websocket_manager:
                try:
                    await self.websocket_manager.broadcast({
                        "type": "conversation_error",
                        "error": str(e)
                    })
                except Exception as e2:
                    logger.error(f"Error broadcasting error: {e2}")
            
            raise
    
    async def step_conversation(self) -> Optional[ConversationState]:
        """
        Execute one step of the conversation.
        
        Returns:
            Updated state or None if conversation ended
        """
        # This would be used for step-by-step execution
        # Implementation depends on LangGraph's streaming capabilities
        pass
    
    def get_current_state(self) -> ConversationState:
        """Get current conversation state."""
        return self.current_state
    
    def reset(self) -> None:
        """Reset orchestrator for a new conversation."""
        self.cycle_manager.reset()
        self.current_state = None
        logger.info("Orchestrator reset")
