"""Tests for MCP Manager functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.services.mcp_manager import MCPManager, MCPServerInstance, MCPServerStatus, get_mcp_manager
from app.schemas.config import MCPServerConfig


@pytest.fixture
def mcp_server_config():
    """Create a test MCP server configuration."""
    return MCPServerConfig(
        name="test_server",
        command="echo",
        args=["test"],
        env={"TEST_VAR": "test_value"}
    )


@pytest.fixture
def mcp_manager():
    """Create a fresh MCP manager instance."""
    # Reset singleton
    MCPManager._instance = None
    return MCPManager()


class TestMCPServerConfig:
    """Test MCP server configuration validation."""
    
    def test_valid_config(self):
        """Test valid MCP server configuration."""
        config = MCPServerConfig(
            name="test_server",
            command="test_command",
            args=["arg1", "arg2"],
            env={"KEY": "VALUE"}
        )
        assert config.name == "test_server"
        assert config.command == "test_command"
        assert len(config.args) == 2
        assert config.env["KEY"] == "VALUE"
    
    def test_config_with_defaults(self):
        """Test MCP server config with default values."""
        config = MCPServerConfig(
            name="minimal_server",
            command="command"
        )
        assert config.name == "minimal_server"
        assert config.command == "command"
        assert config.args == []
        assert config.env == {}
    
    def test_invalid_name(self):
        """Test invalid server name raises validation error."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            MCPServerConfig(
                name="invalid name!",  # Contains invalid characters
                command="command"
            )


class TestMCPManager:
    """Test MCP Manager singleton and basic operations."""
    
    def test_singleton_pattern(self):
        """Test that MCPManager is a singleton."""
        manager1 = get_mcp_manager()
        manager2 = get_mcp_manager()
        assert manager1 is manager2
    
    def test_manager_initialization(self, mcp_manager):
        """Test manager initializes correctly."""
        assert mcp_manager.active_servers == {}
        assert mcp_manager._health_check_task is None
    
    @pytest.mark.asyncio
    async def test_get_all_statuses_empty(self, mcp_manager):
        """Test getting statuses when no servers are running."""
        statuses = await mcp_manager.get_all_statuses()
        assert statuses == {}
    
    @pytest.mark.asyncio
    async def test_get_server_status_not_found(self, mcp_manager):
        """Test getting status of non-existent server."""
        status = await mcp_manager.get_server_status("nonexistent")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_stop_server_not_found(self, mcp_manager):
        """Test stopping non-existent server."""
        result = await mcp_manager.stop_server("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_restart_server_not_found(self, mcp_manager):
        """Test restarting non-existent server."""
        result = await mcp_manager.restart_server("nonexistent")
        assert result is False


class TestMCPServerInstance:
    """Test MCP server instance lifecycle."""
    
    def test_instance_creation(self, mcp_server_config):
        """Test creating a server instance."""
        instance = MCPServerInstance(mcp_server_config)
        assert instance.config == mcp_server_config
        assert instance.session is None
        assert instance.healthy is False
        assert instance.started_at is None
    
    def test_get_status_not_started(self, mcp_server_config):
        """Test getting status of unstarted server."""
        instance = MCPServerInstance(mcp_server_config)
        status = instance.get_status()
        
        assert isinstance(status, MCPServerStatus)
        assert status.name == "test_server"
        assert status.running is False
        assert status.healthy is False
        assert status.started_at is None
        assert len(status.tools_available) == 0


class TestToolAggregation:
    """Test tool aggregation for agents."""
    
    @pytest.mark.asyncio
    async def test_get_tools_for_agent_no_servers(self, mcp_manager):
        """Test getting tools when no servers are running."""
        tools = await mcp_manager.get_tools_for_agent(
            agent_id="test_agent",
            global_server_names=[],
            agent_server_names=[]
        )
        assert tools == []
    
    @pytest.mark.asyncio
    async def test_get_all_servers_empty(self, mcp_manager):
        """Test getting all servers when none exist."""
        servers = mcp_manager.get_all_servers()
        assert servers == {}


class TestMCPServerStatus:
    """Test MCP server status data class."""
    
    def test_status_creation(self):
        """Test creating a server status."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        status = MCPServerStatus(
            name="test",
            running=True,
            healthy=True,
            started_at=now,
            error_message=None,
            tools_available=["tool1", "tool2"]
        )
        
        assert status.name == "test"
        assert status.running is True
        assert status.healthy is True
        assert status.started_at == now
        assert status.error_message is None
        assert len(status.tools_available) == 2


# Integration-style tests (these would normally use mocks or test MCP servers)
class TestMCPIntegration:
    """Integration tests for MCP functionality."""
    
    @pytest.mark.asyncio
    async def test_manager_lifecycle(self, mcp_manager):
        """Test basic manager lifecycle."""
        # Manager should start clean
        assert len(mcp_manager.active_servers) == 0
        
        # Can stop all servers even when none exist
        await mcp_manager.stop_all_servers()
        assert len(mcp_manager.active_servers) == 0
    
    @pytest.mark.asyncio
    async def test_health_monitoring_start_stop(self, mcp_manager):
        """Test starting and stopping health monitoring."""
        # Should be able to start monitoring
        await mcp_manager.start_health_monitoring()
        assert mcp_manager._health_check_task is not None
        
        # Should be able to stop monitoring
        await mcp_manager.stop_health_monitoring()
        assert mcp_manager._health_check_task is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
