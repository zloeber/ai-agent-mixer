"""Agent node factory for creating LangGraph-compatible agent execution nodes."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from ..core.callbacks import ThoughtSuppressingCallback, ConversationLoggingCallback
from ..core.state import AgentMessage, ConversationState, ConversationStateManager
from ..schemas.config import AgentConfig
from ..services.ollama_client import OllamaClient, OllamaConnectionError

logger = logging.getLogger(__name__)


class AgentTimeoutError(Exception):
    """Exception raised when agent execution times out."""
    pass


def create_agent_node(
    agent_id: str,
    agent_config: AgentConfig,
    turn_timeout: int = 300,
    websocket_manager: Optional[Any] = None,
    thought_callback: Optional[Callable[[str, str], None]] = None,
    tools: Optional[List[BaseTool]] = None
) -> Callable[[ConversationState], ConversationState]:
    """
    Create a LangGraph-compatible node for an agent.
    
    This factory function generates a node that:
    1. Injects persona and system prompts
    2. Calls the agent's LLM
    3. Handles thought suppression if enabled
    4. Returns properly attributed messages
    5. Enforces turn timeout
    6. Supports tool calling if tools are provided
    
    Args:
        agent_id: Unique identifier for the agent
        agent_config: Configuration for the agent
        turn_timeout: Maximum seconds for agent to respond
        websocket_manager: Optional WebSocket manager for real-time updates
        thought_callback: Optional callback for thought messages
        tools: Optional list of tools available to the agent
        
    Returns:
        Callable node function compatible with LangGraph
    """
    # Create Ollama client for this agent
    ollama_client = OllamaClient(agent_config.model)
    
    # Bind tools to the client if provided
    if tools:
        logger.info(f"Binding {len(tools)} tools to agent {agent_id}")
        ollama_client.bind_tools(tools)
    
    async def agent_node(state: ConversationState) -> ConversationState:
        """
        Execute agent turn.
        
        Args:
            state: Current conversation state
            
        Returns:
            Updated conversation state with agent's response
        """
        logger.info(f"Agent {agent_id} ({agent_config.name}) starting turn")
        
        try:
            # Get conversation history as LangChain messages
            messages = ConversationStateManager.get_langchain_messages(state)
            
            # Prepend system message with persona if not already present
            if not messages or not isinstance(messages[0], SystemMessage):
                system_content = agent_config.persona
                system_msg = SystemMessage(content=system_content)
                messages.insert(0, system_msg)
            
            # Setup callbacks
            callbacks = []
            
            # Add thought suppression callback if thinking is enabled
            if agent_config.model.thinking:
                thought_callback_handler = ThoughtSuppressingCallback(
                    agent_id=agent_id,
                    thinking_enabled=True,
                    thought_callback=thought_callback,
                    websocket_manager=websocket_manager
                )
                callbacks.append(thought_callback_handler)
            
            # Add logging callback
            logging_callback = ConversationLoggingCallback(agent_id=agent_id)
            callbacks.append(logging_callback)
            
            # Generate response with timeout
            try:
                response = await asyncio.wait_for(
                    ollama_client.generate_response(
                        messages=messages,
                        stream=False,
                        callbacks=callbacks if callbacks else None
                    ),
                    timeout=turn_timeout
                )
            except asyncio.TimeoutError:
                error_msg = f"Agent {agent_id} exceeded turn timeout of {turn_timeout}s"
                logger.error(error_msg)
                raise AgentTimeoutError(error_msg)
            
            # Extract response content
            if agent_config.model.thinking and callbacks:
                # Get cleaned response from thought callback
                thought_callback_handler = callbacks[0]
                response_content = thought_callback_handler.get_response_text()
                if not response_content:
                    # Fallback to full response if no filtering occurred
                    response_content = response.content
            else:
                response_content = response.content
            
            # Additional cleanup for ellipsis patterns
            import re
            response_content = re.sub(r'…{3,}', '', response_content)  # Remove 3+ ellipsis chars
            response_content = re.sub(r'\.{4,}', '...', response_content)  # Normalize periods
            response_content = re.sub(r'Scrolling[…\.]+', '', response_content, flags=re.IGNORECASE)
            response_content = re.sub(r'\n{3,}', '\n\n', response_content)  # Reduce blank lines
            response_content = response_content.strip()
            
            # Skip if response is just punctuation or whitespace
            if not response_content or len(response_content.strip('…. \n\t')) < 3:
                logger.warning(f"Agent {agent_id} produced empty/invalid response, skipping")
                # Return state without adding message
                return state
            
            # Create agent message
            agent_message = AgentMessage(
                content=response_content,
                agent_id=agent_id,
                timestamp=datetime.utcnow(),
                is_thought=False,
                message_type="ai",
                metadata={
                    "agent_name": agent_config.name,
                    "model": agent_config.model.model_name
                }
            )
            
            # Add message to state
            state = ConversationStateManager.add_message(state, agent_message)
            
            # Send response to WebSocket if available
            if websocket_manager:
                try:
                    await websocket_manager.broadcast({
                        "type": "conversation_message",
                        "agent_id": agent_id,
                        "agent_name": agent_config.name,
                        "content": response_content,
                        "timestamp": agent_message.timestamp.isoformat(),
                        "cycle": state["current_cycle"]
                    })
                except Exception as e:
                    logger.error(f"Error broadcasting message: {e}")
            
            logger.info(f"Agent {agent_id} completed turn successfully")
            return state
            
        except AgentTimeoutError:
            # Create timeout error message
            error_message = AgentMessage(
                content=f"[Agent {agent_config.name} timed out after {turn_timeout}s]",
                agent_id="system",
                timestamp=datetime.utcnow(),
                is_thought=False,
                message_type="system",
                metadata={"error": "timeout", "agent_id": agent_id}
            )
            state = ConversationStateManager.add_message(state, error_message)
            state = ConversationStateManager.set_termination(state, "agent_timeout")
            
            # Broadcast error to WebSocket
            if websocket_manager:
                try:
                    await websocket_manager.broadcast({
                        "type": "conversation_error",
                        "error": f"Agent {agent_config.name} timed out after {turn_timeout}s",
                        "agent_id": agent_id,
                        "error_type": "timeout"
                    })
                except Exception as broadcast_error:
                    logger.error(f"Error broadcasting timeout error: {broadcast_error}")
            
            return state
            
        except OllamaConnectionError as e:
            logger.error(f"Ollama connection error for agent {agent_id}: {e}")
            error_message = AgentMessage(
                content=f"[Error: {str(e)}]",
                agent_id="system",
                timestamp=datetime.utcnow(),
                is_thought=False,
                message_type="system",
                metadata={"error": "ollama_connection", "agent_id": agent_id}
            )
            state = ConversationStateManager.add_message(state, error_message)
            state = ConversationStateManager.set_termination(state, "ollama_error")
            
            # Broadcast error to WebSocket
            if websocket_manager:
                try:
                    await websocket_manager.broadcast({
                        "type": "conversation_error",
                        "error": str(e),
                        "agent_id": agent_id,
                        "error_type": "ollama_connection"
                    })
                except Exception as broadcast_error:
                    logger.error(f"Error broadcasting connection error: {broadcast_error}")
            
            return state
            
        except Exception as e:
            logger.error(f"Unexpected error in agent {agent_id}: {e}", exc_info=True)
            error_message = AgentMessage(
                content=f"[Unexpected error: {str(e)}]",
                agent_id="system",
                timestamp=datetime.utcnow(),
                is_thought=False,
                message_type="system",
                metadata={"error": "unexpected", "agent_id": agent_id}
            )
            state = ConversationStateManager.add_message(state, error_message)
            state = ConversationStateManager.set_termination(state, "unexpected_error")
            
            # Broadcast error to WebSocket
            if websocket_manager:
                try:
                    await websocket_manager.broadcast({
                        "type": "conversation_error",
                        "error": str(e),
                        "agent_id": agent_id,
                        "error_type": "unexpected"
                    })
                except Exception as broadcast_error:
                    logger.error(f"Error broadcasting unexpected error: {broadcast_error}")
            
            return state
    
    # Return the node function
    return agent_node


def create_streaming_agent_node(
    agent_id: str,
    agent_config: AgentConfig,
    turn_timeout: int = 300,
    websocket_manager: Optional[Any] = None,
    thought_callback: Optional[Callable[[str, str], None]] = None
) -> Callable[[ConversationState], ConversationState]:
    """
    Create a streaming agent node that sends tokens in real-time.
    
    Similar to create_agent_node but streams response tokens as they're generated.
    
    Args:
        agent_id: Unique identifier for the agent
        agent_config: Configuration for the agent
        turn_timeout: Maximum seconds for agent to respond
        websocket_manager: Optional WebSocket manager for real-time updates
        thought_callback: Optional callback for thought messages
        
    Returns:
        Callable node function compatible with LangGraph
    """
    ollama_client = OllamaClient(agent_config.model)
    
    async def streaming_agent_node(state: ConversationState) -> ConversationState:
        """Execute agent turn with streaming."""
        logger.info(f"Agent {agent_id} ({agent_config.name}) starting streaming turn")
        
        try:
            # Get conversation history
            messages = ConversationStateManager.get_langchain_messages(state)
            
            # Add system message with persona
            if not messages or not isinstance(messages[0], SystemMessage):
                system_msg = SystemMessage(content=agent_config.persona)
                messages.insert(0, system_msg)
            
            # Setup callbacks
            callbacks = []
            if agent_config.model.thinking:
                thought_callback_handler = ThoughtSuppressingCallback(
                    agent_id=agent_id,
                    thinking_enabled=True,
                    thought_callback=thought_callback,
                    websocket_manager=websocket_manager
                )
                callbacks.append(thought_callback_handler)
            
            logging_callback = ConversationLoggingCallback(agent_id=agent_id)
            callbacks.append(logging_callback)
            
            # Stream response
            full_response = ""
            async for token in ollama_client.stream_response(messages, callbacks):
                full_response += token
                
                # Send token via WebSocket
                if websocket_manager:
                    try:
                        await websocket_manager.broadcast({
                            "type": "token",
                            "agent_id": agent_id,
                            "content": token
                        })
                    except Exception as e:
                        logger.error(f"Error streaming token: {e}")
            
            # Create and add message
            agent_message = AgentMessage(
                content=full_response,
                agent_id=agent_id,
                timestamp=datetime.utcnow(),
                is_thought=False,
                message_type="ai",
                metadata={
                    "agent_name": agent_config.name,
                    "model": agent_config.model.model_name
                }
            )
            
            state = ConversationStateManager.add_message(state, agent_message)
            logger.info(f"Agent {agent_id} completed streaming turn")
            return state
            
        except Exception as e:
            logger.error(f"Error in streaming agent {agent_id}: {e}", exc_info=True)
            error_message = AgentMessage(
                content=f"[Error: {str(e)}]",
                agent_id="system",
                timestamp=datetime.utcnow(),
                is_thought=False,
                message_type="system"
            )
            state = ConversationStateManager.add_message(state, error_message)
            state = ConversationStateManager.set_termination(state, "streaming_error")
            return state
    
    return streaming_agent_node
