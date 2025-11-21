"""MCP Server Manager for launching, monitoring, and managing MCP server processes."""

import asyncio
import logging
from typing import Dict, Optional, List
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from ..schemas.config import MCPServerConfig


logger = logging.getLogger(__name__)


@dataclass
class MCPServerStatus:
    """Status information for an MCP server."""
    name: str
    running: bool
    healthy: bool
    started_at: Optional[datetime]
    error_message: Optional[str]
    tools_available: List[str]


class MCPServerInstance:
    """Represents a running MCP server instance."""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.session: Optional[ClientSession] = None
        self.started_at: Optional[datetime] = None
        self.healthy: bool = False
        self.error_message: Optional[str] = None
        self.tools_available: List[str] = []
        self._stdio_context = None
        self._read_stream = None
        self._write_stream = None
        
    async def start(self) -> bool:
        """Start the MCP server process and initialize connection."""
        try:
            logger.info(f"Starting MCP server: {self.config.name}")
            
            # Create server parameters
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env if self.config.env else None
            )
            
            # Start stdio client
            self._stdio_context = stdio_client(server_params)
            streams = await self._stdio_context.__aenter__()
            self._read_stream, self._write_stream = streams
            
            # Create and initialize session
            self.session = ClientSession(self._read_stream, self._write_stream)
            await self.session.__aenter__()
            
            # Initialize the connection
            await self.session.initialize()
            
            self.started_at = datetime.utcnow()
            
            # Perform health check
            await self._health_check()
            
            logger.info(f"MCP server {self.config.name} started successfully")
            return True
            
        except Exception as e:
            self.error_message = str(e)
            self.healthy = False
            logger.error(f"Failed to start MCP server {self.config.name}: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the MCP server process gracefully."""
        try:
            logger.info(f"Stopping MCP server: {self.config.name}")
            
            if self.session:
                await self.session.__aexit__(None, None, None)
                self.session = None
            
            if self._stdio_context:
                await self._stdio_context.__aexit__(None, None, None)
                self._stdio_context = None
            
            self.healthy = False
            self.started_at = None
            logger.info(f"MCP server {self.config.name} stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping MCP server {self.config.name}: {e}")
    
    async def _health_check(self) -> bool:
        """Perform health check on the MCP server."""
        try:
            if not self.session:
                self.healthy = False
                return False
            
            # Try to list available tools
            tools_result = await self.session.list_tools()
            self.tools_available = [tool.name for tool in tools_result.tools]
            
            self.healthy = True
            self.error_message = None
            logger.debug(f"MCP server {self.config.name} health check passed, {len(self.tools_available)} tools available")
            return True
            
        except Exception as e:
            self.healthy = False
            self.error_message = f"Health check failed: {str(e)}"
            logger.warning(f"MCP server {self.config.name} health check failed: {e}")
            return False
    
    async def check_health(self) -> bool:
        """Public method to check server health."""
        return await self._health_check()
    
    async def restart(self) -> bool:
        """Restart the MCP server."""
        logger.info(f"Restarting MCP server: {self.config.name}")
        await self.stop()
        await asyncio.sleep(1)  # Brief pause before restart
        return await self.start()
    
    def get_status(self) -> MCPServerStatus:
        """Get current status of the MCP server."""
        return MCPServerStatus(
            name=self.config.name,
            running=self.session is not None,
            healthy=self.healthy,
            started_at=self.started_at,
            error_message=self.error_message,
            tools_available=self.tools_available
        )


class MCPManager:
    """Singleton manager for all MCP servers."""
    
    _instance: Optional['MCPManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.active_servers: Dict[str, MCPServerInstance] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval: int = 30  # seconds
        self._initialized = True
        logger.info("MCPManager initialized")
    
    async def start_server(self, config: MCPServerConfig) -> bool:
        """Start a new MCP server."""
        if config.name in self.active_servers:
            logger.warning(f"MCP server {config.name} is already running")
            return False
        
        instance = MCPServerInstance(config)
        success = await instance.start()
        
        if success:
            self.active_servers[config.name] = instance
        
        return success
    
    async def stop_server(self, name: str) -> bool:
        """Stop an MCP server by name."""
        if name not in self.active_servers:
            logger.warning(f"MCP server {name} not found")
            return False
        
        instance = self.active_servers[name]
        await instance.stop()
        del self.active_servers[name]
        return True
    
    async def restart_server(self, name: str) -> bool:
        """Restart an MCP server by name."""
        if name not in self.active_servers:
            logger.warning(f"MCP server {name} not found")
            return False
        
        instance = self.active_servers[name]
        return await instance.restart()
    
    async def get_server(self, name: str) -> Optional[MCPServerInstance]:
        """Get an MCP server instance by name."""
        return self.active_servers.get(name)
    
    def get_all_servers(self) -> Dict[str, MCPServerInstance]:
        """Get all active MCP server instances."""
        return self.active_servers.copy()
    
    async def get_server_status(self, name: str) -> Optional[MCPServerStatus]:
        """Get status of a specific MCP server."""
        instance = self.active_servers.get(name)
        if instance:
            return instance.get_status()
        return None
    
    async def get_all_statuses(self) -> Dict[str, MCPServerStatus]:
        """Get status of all MCP servers."""
        return {
            name: instance.get_status()
            for name, instance in self.active_servers.items()
        }
    
    async def start_health_monitoring(self) -> None:
        """Start periodic health monitoring of all servers."""
        if self._health_check_task is not None:
            logger.warning("Health monitoring is already running")
            return
        
        self._health_check_task = asyncio.create_task(self._health_monitor_loop())
        logger.info("Health monitoring started")
    
    async def stop_health_monitoring(self) -> None:
        """Stop health monitoring."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
        logger.info("Health monitoring stopped")
    
    async def _health_monitor_loop(self) -> None:
        """Background task that monitors server health."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                for name, instance in self.active_servers.items():
                    healthy = await instance.check_health()
                    if not healthy:
                        logger.warning(f"MCP server {name} is unhealthy: {instance.error_message}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
    
    async def stop_all_servers(self) -> None:
        """Stop all MCP servers gracefully."""
        logger.info("Stopping all MCP servers")
        
        for name in list(self.active_servers.keys()):
            await self.stop_server(name)
        
        await self.stop_health_monitoring()
        logger.info("All MCP servers stopped")
    
    async def get_tools_for_agent(self, agent_id: str, global_server_names: List[str], agent_server_names: List[str]) -> List[dict]:
        """
        Get all tools available to a specific agent.
        Aggregates tools from global servers and agent-specific servers.
        """
        tools = []
        
        # Get tools from global servers
        for server_name in global_server_names:
            instance = self.active_servers.get(server_name)
            if instance and instance.healthy:
                try:
                    if instance.session:
                        tools_result = await instance.session.list_tools()
                        for tool in tools_result.tools:
                            tools.append({
                                "name": tool.name,
                                "description": tool.description or "",
                                "server": server_name,
                                "scope": "global",
                                "input_schema": tool.inputSchema
                            })
                except Exception as e:
                    logger.error(f"Error getting tools from global server {server_name}: {e}")
        
        # Get tools from agent-specific servers
        for server_name in agent_server_names:
            # Agent-scoped servers are prefixed with agent_id_
            scoped_name = f"{agent_id}_{server_name}"
            instance = self.active_servers.get(scoped_name)
            if instance and instance.healthy:
                try:
                    if instance.session:
                        tools_result = await instance.session.list_tools()
                        for tool in tools_result.tools:
                            tools.append({
                                "name": tool.name,
                                "description": tool.description or "",
                                "server": scoped_name,
                                "scope": "agent",
                                "agent_id": agent_id,
                                "input_schema": tool.inputSchema
                            })
                except Exception as e:
                    logger.error(f"Error getting tools from agent server {scoped_name}: {e}")
        
        logger.info(f"Agent {agent_id} has access to {len(tools)} tools")
        return tools
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> dict:
        """
        Call a tool on a specific MCP server.
        """
        instance = self.active_servers.get(server_name)
        if not instance:
            raise ValueError(f"MCP server {server_name} not found")
        
        if not instance.healthy:
            raise ValueError(f"MCP server {server_name} is not healthy")
        
        if not instance.session:
            raise ValueError(f"MCP server {server_name} has no active session")
        
        try:
            result = await instance.session.call_tool(tool_name, arguments)
            return {
                "success": True,
                "content": result.content,
                "isError": result.isError if hasattr(result, 'isError') else False
            }
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on server {server_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "isError": True
            }


# Global singleton instance
_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get or create the global MCP manager instance."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
