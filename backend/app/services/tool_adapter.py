"""Tool adapter for converting MCP tools to LangChain BaseTool format."""

import logging
from typing import Any, Dict, Optional, Type
from datetime import datetime, timezone

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, create_model

from .mcp_manager import get_mcp_manager


logger = logging.getLogger(__name__)


class MCPAdapterTool(BaseTool):
    """
    Adapter tool that forwards tool calls to MCP servers.
    Converts LangChain tool interface to MCP protocol.
    """
    
    server_name: str = Field(..., description="Name of the MCP server")
    tool_name: str = Field(..., description="Name of the tool on the MCP server")
    tool_description: str = Field(default="", description="Description of the tool")
    input_schema_dict: Dict[str, Any] = Field(..., description="JSON schema for tool input")
    
    # BaseTool required fields
    name: str = ""
    description: str = ""
    
    def __init__(self, **data):
        # Set name and description from tool metadata
        if 'name' not in data and 'tool_name' in data:
            data['name'] = data['tool_name']
        if 'description' not in data and 'tool_description' in data:
            data['description'] = data['tool_description']
        super().__init__(**data)
    
    def _run(self, *args, **kwargs) -> str:
        """Synchronous execution - not supported for async MCP calls."""
        raise NotImplementedError("MCPAdapterTool only supports async execution. Use _arun instead.")
    
    async def _arun(self, **kwargs) -> str:
        """
        Execute the tool by calling the MCP server.
        """
        try:
            logger.info(f"Calling MCP tool {self.tool_name} on server {self.server_name}")
            logger.debug(f"Tool arguments: {kwargs}")
            
            # Get MCP manager
            mcp_manager = get_mcp_manager()
            
            # Call the tool on the MCP server
            start_time = datetime.now(timezone.utc)
            result = await mcp_manager.call_tool(
                server_name=self.server_name,
                tool_name=self.tool_name,
                arguments=kwargs
            )
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(f"Tool {self.tool_name} completed in {duration:.2f}s")
            
            # Handle result
            if result.get("success"):
                # Extract content from MCP response
                content = result.get("content", [])
                if isinstance(content, list):
                    # Combine multiple content items
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                            else:
                                # For other types, convert to string
                                text_parts.append(str(item))
                        else:
                            text_parts.append(str(item))
                    return "\n".join(text_parts)
                else:
                    return str(content)
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Tool {self.tool_name} failed: {error_msg}")
                return f"Error: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error executing MCP tool {self.tool_name}: {e}")
            return f"Error executing tool: {str(e)}"


def create_langchain_tool_from_mcp(
    server_name: str,
    tool_name: str,
    tool_description: str,
    input_schema: Dict[str, Any]
) -> MCPAdapterTool:
    """
    Create a LangChain-compatible tool from MCP tool metadata.
    
    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool
        tool_description: Description of what the tool does
        input_schema: JSON schema defining the tool's input parameters
    
    Returns:
        MCPAdapterTool instance that can be used with LangChain agents
    """
    return MCPAdapterTool(
        server_name=server_name,
        tool_name=tool_name,
        tool_description=tool_description,
        input_schema_dict=input_schema,
        name=tool_name,
        description=tool_description
    )


async def get_tools_for_agent_as_langchain(
    agent_id: str,
    global_server_names: list[str],
    agent_server_names: list[str]
) -> list[BaseTool]:
    """
    Get all tools for an agent as LangChain BaseTool instances.
    
    Args:
        agent_id: ID of the agent
        global_server_names: List of global MCP server names
        agent_server_names: List of agent-specific MCP server names
    
    Returns:
        List of LangChain BaseTool instances
    """
    mcp_manager = get_mcp_manager()
    
    # Get tool metadata from MCP manager
    tools_metadata = await mcp_manager.get_tools_for_agent(
        agent_id=agent_id,
        global_server_names=global_server_names,
        agent_server_names=agent_server_names
    )
    
    # Convert to LangChain tools
    langchain_tools = []
    for tool_meta in tools_metadata:
        try:
            tool = create_langchain_tool_from_mcp(
                server_name=tool_meta["server"],
                tool_name=tool_meta["name"],
                tool_description=tool_meta["description"],
                input_schema=tool_meta["input_schema"]
            )
            langchain_tools.append(tool)
        except Exception as e:
            logger.error(f"Error creating LangChain tool for {tool_meta['name']}: {e}")
    
    logger.info(f"Created {len(langchain_tools)} LangChain tools for agent {agent_id}")
    return langchain_tools


class ToolExecutionLogger:
    """Logger for tool execution metrics and telemetry."""
    
    @staticmethod
    def log_tool_call(
        agent_id: str,
        tool_name: str,
        server_name: str,
        arguments: dict,
        result: dict,
        duration: float,
        success: bool
    ) -> None:
        """
        Log a tool execution with full context.
        
        Args:
            agent_id: ID of the agent that called the tool
            tool_name: Name of the tool
            server_name: Name of the MCP server
            arguments: Arguments passed to the tool
            result: Result from the tool
            duration: Execution duration in seconds
            success: Whether the tool call succeeded
        """
        log_data = {
            "event": "tool_call",
            "agent_id": agent_id,
            "tool_name": tool_name,
            "server_name": server_name,
            "duration_seconds": duration,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if success:
            logger.info(f"Tool call succeeded", extra=log_data)
        else:
            log_data["error"] = result.get("error", "Unknown error")
            logger.warning(f"Tool call failed", extra=log_data)
