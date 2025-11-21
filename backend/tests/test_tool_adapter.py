"""Tests for MCP tool adapter functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.tool_adapter import (
    MCPAdapterTool,
    create_langchain_tool_from_mcp,
    get_tools_for_agent_as_langchain,
    ToolExecutionLogger
)


class TestMCPAdapterTool:
    """Test MCP adapter tool functionality."""
    
    def test_tool_creation(self):
        """Test creating an MCP adapter tool."""
        tool = MCPAdapterTool(
            server_name="test_server",
            tool_name="test_tool",
            tool_description="A test tool",
            input_schema_dict={"type": "object", "properties": {}}
        )
        
        assert tool.server_name == "test_server"
        assert tool.tool_name == "test_tool"
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
    
    def test_tool_sync_not_supported(self):
        """Test that synchronous execution raises error."""
        tool = MCPAdapterTool(
            server_name="test_server",
            tool_name="test_tool",
            tool_description="Test",
            input_schema_dict={}
        )
        
        with pytest.raises(NotImplementedError):
            tool._run()
    
    @pytest.mark.asyncio
    async def test_tool_async_execution_success(self):
        """Test successful async tool execution."""
        tool = MCPAdapterTool(
            server_name="test_server",
            tool_name="test_tool",
            tool_description="Test",
            input_schema_dict={}
        )
        
        # Mock the MCP manager
        with patch('app.services.tool_adapter.get_mcp_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.call_tool = AsyncMock(return_value={
                "success": True,
                "content": [{"type": "text", "text": "Tool result"}]
            })
            mock_get_manager.return_value = mock_manager
            
            result = await tool._arun(arg1="value1")
            
            assert result == "Tool result"
            mock_manager.call_tool.assert_called_once_with(
                server_name="test_server",
                tool_name="test_tool",
                arguments={"arg1": "value1"}
            )
    
    @pytest.mark.asyncio
    async def test_tool_async_execution_error(self):
        """Test tool execution with error."""
        tool = MCPAdapterTool(
            server_name="test_server",
            tool_name="test_tool",
            tool_description="Test",
            input_schema_dict={}
        )
        
        # Mock the MCP manager to return error
        with patch('app.services.tool_adapter.get_mcp_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.call_tool = AsyncMock(return_value={
                "success": False,
                "error": "Tool execution failed"
            })
            mock_get_manager.return_value = mock_manager
            
            result = await tool._arun()
            
            assert "Error: Tool execution failed" in result


class TestToolCreation:
    """Test LangChain tool creation from MCP."""
    
    def test_create_langchain_tool_from_mcp(self):
        """Test creating LangChain tool from MCP metadata."""
        tool = create_langchain_tool_from_mcp(
            server_name="test_server",
            tool_name="my_tool",
            tool_description="Does something useful",
            input_schema={"type": "object", "properties": {"param": {"type": "string"}}}
        )
        
        assert isinstance(tool, MCPAdapterTool)
        assert tool.name == "my_tool"
        assert tool.description == "Does something useful"
        assert tool.server_name == "test_server"
    
    @pytest.mark.asyncio
    async def test_get_tools_for_agent_empty(self):
        """Test getting tools when no servers are available."""
        with patch('app.services.tool_adapter.get_mcp_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_tools_for_agent = AsyncMock(return_value=[])
            mock_get_manager.return_value = mock_manager
            
            tools = await get_tools_for_agent_as_langchain(
                agent_id="test_agent",
                global_server_names=[],
                agent_server_names=[]
            )
            
            assert tools == []
    
    @pytest.mark.asyncio
    async def test_get_tools_for_agent_with_tools(self):
        """Test getting tools from MCP servers."""
        with patch('app.services.tool_adapter.get_mcp_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_tools_for_agent = AsyncMock(return_value=[
                {
                    "name": "tool1",
                    "description": "First tool",
                    "server": "server1",
                    "scope": "global",
                    "input_schema": {}
                },
                {
                    "name": "tool2",
                    "description": "Second tool",
                    "server": "server2",
                    "scope": "agent",
                    "agent_id": "test_agent",
                    "input_schema": {}
                }
            ])
            mock_get_manager.return_value = mock_manager
            
            tools = await get_tools_for_agent_as_langchain(
                agent_id="test_agent",
                global_server_names=["server1"],
                agent_server_names=["server2"]
            )
            
            assert len(tools) == 2
            assert all(isinstance(tool, MCPAdapterTool) for tool in tools)
            assert tools[0].name == "tool1"
            assert tools[1].name == "tool2"


class TestToolExecutionLogger:
    """Test tool execution logging."""
    
    def test_log_successful_tool_call(self):
        """Test logging a successful tool call."""
        # Should not raise any exceptions
        ToolExecutionLogger.log_tool_call(
            agent_id="test_agent",
            tool_name="test_tool",
            server_name="test_server",
            arguments={"arg": "value"},
            result={"content": "result"},
            duration=0.5,
            success=True
        )
    
    def test_log_failed_tool_call(self):
        """Test logging a failed tool call."""
        # Should not raise any exceptions
        ToolExecutionLogger.log_tool_call(
            agent_id="test_agent",
            tool_name="test_tool",
            server_name="test_server",
            arguments={"arg": "value"},
            result={"error": "Tool failed"},
            duration=0.3,
            success=False
        )


class TestToolContent:
    """Test handling of different tool content types."""
    
    @pytest.mark.asyncio
    async def test_tool_with_list_content(self):
        """Test tool execution with list content."""
        tool = MCPAdapterTool(
            server_name="test_server",
            tool_name="test_tool",
            tool_description="Test",
            input_schema_dict={}
        )
        
        with patch('app.services.tool_adapter.get_mcp_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.call_tool = AsyncMock(return_value={
                "success": True,
                "content": [
                    {"type": "text", "text": "First part"},
                    {"type": "text", "text": "Second part"}
                ]
            })
            mock_get_manager.return_value = mock_manager
            
            result = await tool._arun()
            
            assert "First part" in result
            assert "Second part" in result
    
    @pytest.mark.asyncio
    async def test_tool_with_string_content(self):
        """Test tool execution with string content."""
        tool = MCPAdapterTool(
            server_name="test_server",
            tool_name="test_tool",
            tool_description="Test",
            input_schema_dict={}
        )
        
        with patch('app.services.tool_adapter.get_mcp_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.call_tool = AsyncMock(return_value={
                "success": True,
                "content": "Simple string result"
            })
            mock_get_manager.return_value = mock_manager
            
            result = await tool._arun()
            
            assert result == "Simple string result"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
