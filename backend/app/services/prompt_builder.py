"""System prompt building and template rendering."""

import logging
from typing import Any, Dict, List, Optional

from jinja2 import Environment, Template, TemplateSyntaxError

from ..schemas.config import AgentConfig, InitializationConfig

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Builder for constructing system prompts from templates."""
    
    def __init__(self):
        """Initialize prompt builder with Jinja2 environment."""
        self.env = Environment(autoescape=False)
    
    def build_system_prompt(
        self,
        agent_config: AgentConfig,
        template: Optional[str] = None,
        global_context: Optional[Dict[str, Any]] = None,
        available_tools: Optional[List[str]] = None
    ) -> str:
        """
        Build system prompt for an agent.
        
        Args:
            agent_config: Agent configuration
            template: Optional Jinja2 template string
            global_context: Optional global context variables
            available_tools: Optional list of available tool names
            
        Returns:
            Rendered system prompt
        """
        # Use template if provided, otherwise use agent persona directly
        if not template:
            # Default template that just uses persona
            template = "{{ agent.persona }}"
        
        try:
            # Prepare template context
            context = {
                "agent": {
                    "name": agent_config.name,
                    "persona": agent_config.persona,
                    "model": agent_config.model.model_name
                }
            }
            
            # Add tools if available
            if available_tools:
                context["tools"] = available_tools
                context["has_tools"] = True
            else:
                context["has_tools"] = False
            
            # Add global context
            if global_context:
                context.update(global_context)
            
            # Render template
            tmpl = self.env.from_string(template)
            rendered = tmpl.render(**context)
            
            logger.debug(
                f"Built system prompt for {agent_config.name}: "
                f"{len(rendered)} characters"
            )
            
            return rendered.strip()
            
        except TemplateSyntaxError as e:
            logger.error(f"Template syntax error: {e}")
            # Fallback to plain persona
            return agent_config.persona
            
        except Exception as e:
            logger.error(f"Error building system prompt: {e}", exc_info=True)
            return agent_config.persona
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        This is a simple approximation: ~4 characters per token.
        For production, use tiktoken or similar.
        
        Args:
            text: Text to count
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
