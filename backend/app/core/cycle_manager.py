"""Cycle detection and termination logic for conversation management."""

import logging
import re
from typing import List, Optional, Tuple

from .state import ConversationState, ConversationStateManager, AgentMessage
from ..schemas.config import TerminationConditions

logger = logging.getLogger(__name__)


class CycleManager:
    """
    Manager for tracking conversation cycles and determining termination.
    
    A cycle is completed when all agents have had at least one turn.
    """
    
    def __init__(
        self,
        agent_ids: List[str],
        max_cycles: int,
        termination_conditions: Optional[TerminationConditions] = None
    ):
        """
        Initialize cycle manager.
        
        Args:
            agent_ids: List of all agent IDs in the conversation
            max_cycles: Maximum number of cycles before termination
            termination_conditions: Optional conditions for early termination
        """
        self.agent_ids = set(agent_ids)
        self.max_cycles = max_cycles
        self.termination_conditions = termination_conditions or TerminationConditions()
        
        # Track which agents have spoken in current cycle
        self.agents_spoken_this_cycle: set[str] = set()
        self.cycles_completed = 0
        
        # For silence detection
        self.last_substantive_cycle = 0
        
        logger.debug(
            f"CycleManager initialized with {len(agent_ids)} agents, "
            f"max {max_cycles} cycles"
        )
    
    def register_agent_turn(self, agent_id: str) -> None:
        """
        Register that an agent has taken a turn.
        
        Args:
            agent_id: ID of agent that just spoke
        """
        if agent_id in self.agent_ids:
            self.agents_spoken_this_cycle.add(agent_id)
            logger.debug(
                f"Agent {agent_id} registered. "
                f"{len(self.agents_spoken_this_cycle)}/{len(self.agent_ids)} agents spoken"
            )
    
    def is_cycle_complete(self) -> bool:
        """
        Check if current cycle is complete (all agents have spoken).
        
        Returns:
            True if all agents have spoken at least once
        """
        return self.agents_spoken_this_cycle == self.agent_ids
    
    def complete_cycle(self) -> int:
        """
        Mark current cycle as complete and prepare for next cycle.
        
        Returns:
            The cycle number that just completed
        """
        if self.is_cycle_complete():
            self.cycles_completed += 1
            self.agents_spoken_this_cycle.clear()
            logger.info(f"Cycle {self.cycles_completed} completed")
            return self.cycles_completed
        else:
            logger.warning("complete_cycle called but cycle not complete")
            return self.cycles_completed
    
    def check_termination(self, state: ConversationState) -> Tuple[bool, Optional[str]]:
        """
        Check if conversation should terminate.
        
        Args:
            state: Current conversation state
            
        Returns:
            Tuple of (should_terminate, reason)
        """
        # Check if already marked for termination
        if state.get("should_terminate", False):
            return True, state.get("termination_reason", "manual_termination")
        
        # Check max cycles
        if self.cycles_completed >= self.max_cycles:
            logger.info(f"Max cycles ({self.max_cycles}) reached")
            return True, "max_cycles_reached"
        
        # Get recent messages
        messages = ConversationStateManager.get_messages(state, exclude_thoughts=True)
        
        # Check keyword triggers
        if self.termination_conditions.keyword_triggers:
            if self._check_keyword_triggers(messages):
                logger.info("Keyword trigger detected")
                return True, "keyword_trigger"
        
        # Check silence detection
        if self.termination_conditions.silence_detection:
            if self._check_silence_detection(messages):
                logger.info("Silence detected")
                return True, "silence_detected"
        
        return False, None
    
    def _check_keyword_triggers(self, messages: List[AgentMessage]) -> bool:
        """
        Check if any termination keywords are present in recent messages.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            True if termination keyword found
        """
        if not self.termination_conditions.keyword_triggers:
            return False
        
        # Check last 5 messages for keywords
        recent_messages = messages[-5:] if len(messages) >= 5 else messages
        
        for msg in recent_messages:
            if msg.message_type in ["ai", "human"]:
                content_lower = msg.content.lower()
                for keyword in self.termination_conditions.keyword_triggers:
                    if keyword.lower() in content_lower:
                        logger.debug(f"Found keyword trigger: '{keyword}' in message from {msg.agent_id}")
                        return True
        
        return False
    
    def _check_silence_detection(self, messages: List[AgentMessage]) -> bool:
        """
        Check if conversation has been silent (no substantive content).
        
        Args:
            messages: List of conversation messages
            
        Returns:
            True if silence threshold exceeded
        """
        if not self.termination_conditions.silence_detection:
            return False
        
        threshold = self.termination_conditions.silence_detection
        
        # Check if we've had enough cycles for silence detection
        if self.cycles_completed < threshold:
            return False
        
        # Check last N cycles for substantive content
        # A message is substantive if it's longer than 20 characters and not just punctuation
        recent_cycles = self.cycles_completed - threshold
        
        substantive_found = False
        for msg in reversed(messages):
            if msg.message_type == "ai" and not msg.is_thought:
                # Check if message is substantive
                content = msg.content.strip()
                # Remove common filler patterns
                content_cleaned = re.sub(r'[^\w\s]', '', content)
                
                if len(content_cleaned) > 20:
                    substantive_found = True
                    break
        
        if not substantive_found:
            logger.debug(f"No substantive content in last {threshold} cycles")
            return True
        
        return False
    
    def get_current_cycle(self) -> int:
        """Get current cycle number."""
        return self.cycles_completed
    
    def reset(self) -> None:
        """Reset cycle tracking."""
        self.agents_spoken_this_cycle.clear()
        self.cycles_completed = 0
        self.last_substantive_cycle = 0
        logger.debug("CycleManager reset")


def should_continue_conversation(state: ConversationState, cycle_manager: CycleManager) -> str:
    """
    Determine if conversation should continue or terminate.
    
    This function is used as a conditional edge in LangGraph.
    
    Args:
        state: Current conversation state
        cycle_manager: Cycle manager tracking conversation progress
        
    Returns:
        "continue" or "terminate"
    """
    should_terminate, reason = cycle_manager.check_termination(state)
    
    if should_terminate:
        logger.info(f"Conversation terminating: {reason}")
        state = ConversationStateManager.set_termination(state, reason)
        return "terminate"
    
    return "continue"
