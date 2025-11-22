"""Callback handlers for LangChain/LangGraph operations."""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


class ThoughtSuppressingCallback(AsyncCallbackHandler):
    """
    Callback handler that captures model thinking and routes it separately.
    
    This callback monitors LLM token generation and can:
    1. Detect when the model is "thinking" vs. responding
    2. Route thought tokens to agent-specific console
    3. Filter thought patterns from final responses
    """
    
    # Common thought patterns to detect
    THOUGHT_PATTERNS = [
        r"<thinking>.*?</thinking>",  # XML-style thinking tags
        r"```thinking\n.*?\n```",  # Markdown code block
        r"\[THINKING:.*?\]",  # Bracketed thinking
        r"Let me think about this\.\.\.",
        r"I think\.\.\.",
        r"Let me consider\.\.\.",
        r"Hmm\.\.\.",
        r"…{3,}",  # Three or more ellipsis characters
        r"\.{3,}",  # Three or more periods
        r"[…\.]{10,}",  # Long sequences of ellipsis/periods
        r"Scrolling[…\.]+",  # Scrolling with ellipsis
    ]
    
    def __init__(
        self,
        agent_id: str,
        thinking_enabled: bool = False,
        thought_callback: Optional[Callable[[str, str], None]] = None,
        websocket_manager: Optional[Any] = None
    ):
        """
        Initialize thought suppression callback.
        
        Args:
            agent_id: Identifier for the agent using this callback
            thinking_enabled: Whether to capture and suppress thoughts
            thought_callback: Optional callback function for thought tokens
            websocket_manager: Optional WebSocket manager for real-time streaming
        """
        super().__init__()
        self.agent_id = agent_id
        self.thinking_enabled = thinking_enabled
        self.thought_callback = thought_callback
        self.websocket_manager = websocket_manager
        
        # State tracking
        self.is_thinking = False
        self.thought_buffer: List[str] = []
        self.response_buffer: List[str] = []
        self.current_token = ""
        
        # Compile regex patterns for efficiency
        self._thought_patterns = [re.compile(p, re.DOTALL | re.IGNORECASE) 
                                   for p in self.THOUGHT_PATTERNS]
    
    async def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """Called when LLM starts generating."""
        # Reset state for new generation
        self.is_thinking = False
        self.thought_buffer = []
        self.response_buffer = []
        self.current_token = ""
        logger.debug(f"Agent {self.agent_id} starting LLM generation")
    
    async def on_llm_new_token(
        self,
        token: str,
        **kwargs: Any
    ) -> None:
        """
        Called when a new token is generated.
        
        Args:
            token: The newly generated token
        """
        if not self.thinking_enabled:
            # If thinking is disabled, just pass through
            self.response_buffer.append(token)
            return
        
        self.current_token = token
        
        # Check for excessive ellipsis patterns (treat as thinking)
        if len(token.strip()) > 5 and all(c in '….' for c in token.strip()):
            self.is_thinking = True
            logger.debug(f"Agent {self.agent_id} detected ellipsis pattern, treating as thinking")
        
        # Check for thinking delimiters
        if "<thinking>" in token or "```thinking" in token or "[THINKING:" in token:
            self.is_thinking = True
            logger.debug(f"Agent {self.agent_id} entered thinking mode")
        
        if self.is_thinking:
            # Capture thought token
            self.thought_buffer.append(token)
            
            # Send to console via callback if available
            if self.thought_callback:
                try:
                    await self._send_thought_async(token)
                except Exception as e:
                    logger.error(f"Error in thought callback: {e}")
            
            # Check for end of thinking
            if "</thinking>" in token or "```" in token or "]" in token:
                self.is_thinking = False
                logger.debug(f"Agent {self.agent_id} exited thinking mode")
        else:
            # Regular response token
            self.response_buffer.append(token)
    
    async def _send_thought_async(self, token: str) -> None:
        """Send thought token asynchronously."""
        if self.thought_callback:
            if asyncio.iscoroutinefunction(self.thought_callback):
                await self.thought_callback(self.agent_id, token)
            else:
                self.thought_callback(self.agent_id, token)
        
        # Also send via WebSocket if manager is available
        if self.websocket_manager:
            try:
                await self.websocket_manager.send_to_agent_console(
                    self.agent_id,
                    {
                        "type": "thought",
                        "content": token,
                        "agent_id": self.agent_id
                    }
                )
            except Exception as e:
                logger.error(f"Error sending thought via WebSocket: {e}")
    
    async def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any
    ) -> None:
        """Called when LLM finishes generating."""
        logger.debug(
            f"Agent {self.agent_id} finished generation. "
            f"Thought tokens: {len(self.thought_buffer)}, "
            f"Response tokens: {len(self.response_buffer)}"
        )
    
    async def on_llm_error(
        self,
        error: Exception,
        **kwargs: Any
    ) -> None:
        """Called when LLM encounters an error."""
        logger.error(f"Agent {self.agent_id} LLM error: {error}")
    
    def get_response_text(self) -> str:
        """
        Get the final response text with thoughts filtered out.
        
        Returns:
            Cleaned response text
        """
        response = "".join(self.response_buffer)
        
        if self.thinking_enabled:
            # Apply regex filters to remove any remaining thought patterns
            for pattern in self._thought_patterns:
                response = pattern.sub("", response)
            
            # Additional cleanup for excessive punctuation
            response = re.sub(r'…{3,}', '', response)  # Remove 3+ ellipsis
            response = re.sub(r'\.{4,}', '...', response)  # Reduce 4+ periods to 3
            response = re.sub(r'\n{3,}', '\n\n', response)  # Reduce excessive newlines
            response = re.sub(r'[ \t]{3,}', ' ', response)  # Reduce excessive spaces
        
        return response.strip()
    
    def get_thought_text(self) -> str:
        """
        Get the captured thought text.
        
        Returns:
            Thought text
        """
        return "".join(self.thought_buffer)
    
    def reset(self) -> None:
        """Reset callback state."""
        self.is_thinking = False
        self.thought_buffer = []
        self.response_buffer = []
        self.current_token = ""


class ConversationLoggingCallback(AsyncCallbackHandler):
    """Callback for logging conversation events and telemetry."""
    
    def __init__(self, agent_id: str):
        """
        Initialize conversation logging callback.
        
        Args:
            agent_id: Identifier for the agent
        """
        super().__init__()
        self.agent_id = agent_id
        self.token_count = 0
        self.start_time: Optional[float] = None
    
    async def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """Log LLM start."""
        import time
        self.start_time = time.time()
        self.token_count = 0
        logger.info(f"Agent {self.agent_id} starting LLM generation")
    
    async def on_llm_new_token(
        self,
        token: str,
        **kwargs: Any
    ) -> None:
        """Count tokens."""
        self.token_count += 1
    
    async def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any
    ) -> None:
        """Log completion with telemetry."""
        import time
        if self.start_time:
            duration = time.time() - self.start_time
            logger.info(
                f"Agent {self.agent_id} completed generation: "
                f"{self.token_count} tokens in {duration:.2f}s "
                f"({self.token_count/duration:.1f} tokens/s)"
            )
    
    async def on_llm_error(
        self,
        error: Exception,
        **kwargs: Any
    ) -> None:
        """Log errors."""
        logger.error(f"Agent {self.agent_id} LLM error: {error}", exc_info=True)
